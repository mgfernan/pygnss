import argparse
import datetime
import io
import re
import sys
from typing import Dict, IO, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..gnss.types import ConstellationId, Satellite
from ..logger import logger
from ..rinex.obs_writer import ObsHeader, write_obs
from ..time import get_gps_leapseconds
from .norad import SatNameResolver, load_norad_map
from .signals import LEO_SIGNALS

CSV_CONSTELLATIONS: Dict[str, ConstellationId] = {
    'globalstar': ConstellationId.GLOBALSTAR,
    'iridium': ConstellationId.IRIDIUM,
    'orbcomm': ConstellationId.ORBCOMM,
}

CSV_TIMESTAMP_FORMAT = '%d-%m-%Y %H:%M:%S.%f'
FREQUENCY_TOLERANCE_HZ = 1e3
EPOCH_RESOLUTION_NS = 100

_RX_LOCATION_PATTERN = re.compile(r'(\w+):lla\([^)]*\);ecef\(([^)]*)\)')


def parse_rx_location(line: str) -> Dict[str, Tuple[float, float, float]]:
    """
    Parse the receiver location comment of the CSV files

    >>> parse_rx_location('# rx_location globalstar:lla(41.5,2.1,198.4);ecef(1.0,2.0,3.0) | iridium:lla(1,2,3);ecef(4,5,6)')
    {'globalstar': (1.0, 2.0, 3.0), 'iridium': (4.0, 5.0, 6.0)}
    """

    locations = {}
    for name, ecef in _RX_LOCATION_PATTERN.findall(line):
        x, y, z = (float(v) for v in ecef.split(','))
        locations[name.lower()] = (x, y, z)
    return locations


def read_leo_csv(source) -> Tuple[pd.DataFrame, Dict[str, Tuple[float, float, float]]]:
    """
    Read a LEO CSV file (path or file-like object).

    Returns the observations (with 'timestamp' as datetime64[ns]) and the receiver
    ECEF position per constellation, if available
    """

    opened = isinstance(source, str)
    fh = open(source, 'r', encoding='utf-8') if opened else source
    try:
        content = fh.read()
    finally:
        if opened:
            fh.close()

    locations: Dict[str, Tuple[float, float, float]] = {}
    first_line = content.split('\n', 1)[0]
    if first_line.startswith('#'):
        locations = parse_rx_location(first_line)

    df = pd.read_csv(io.StringIO(content), comment='#')
    df['constellation'] = df['constellation'].str.strip().str.lower()
    df['timestamp'] = pd.to_datetime(df['timestamp_utc'], format=CSV_TIMESTAMP_FORMAT)

    return df, locations


def _to_epoch(timestamp_ns: int, time_system: str) -> datetime.datetime:
    rounded = int(round(timestamp_ns / EPOCH_RESOLUTION_NS)) * EPOCH_RESOLUTION_NS
    epoch = datetime.datetime(1970, 1, 1) + datetime.timedelta(microseconds=rounded // 1000)
    if time_system == 'GPS':
        epoch += get_gps_leapseconds(epoch)
    return epoch


def convert(source, output: IO, marker_name: str = 'LEO', constellations: Optional[List[str]] = None,
            resolver: Optional[SatNameResolver] = None, time_system: str = 'GPS') -> int:
    """
    Convert a LEO CSV (Doppler and SNR) into a RINEX-LEO observation file

    Returns the number of epochs written
    """

    time_system = time_system.upper()
    if time_system not in ('GPS', 'UTC'):
        raise ValueError(f'Unsupported time system [ {time_system} ]')

    resolver = resolver or SatNameResolver()
    df, locations = read_leo_csv(source)

    unknown = set(df['constellation'].unique()) - set(CSV_CONSTELLATIONS)
    if unknown:
        raise ValueError(f'Unsupported constellations in CSV: {sorted(unknown)}')

    if constellations:
        wanted = {c.lower() for c in constellations}
        df = df[df['constellation'].isin(wanted)]
    if df.empty:
        raise ValueError('No observations to convert')

    names = df['satellite_name'].unique()
    norad = {name: resolver.resolve(name) for name in names}

    obs_types: Dict[str, List[str]] = {}
    comments: List[str] = []
    for csv_name in sorted(df['constellation'].unique()):
        constellation = CSV_CONSTELLATIONS[csv_name]
        signal = LEO_SIGNALS[constellation]
        obs_types[constellation.value] = signal.obs_types
        comments.append(f'{constellation.value}: band {signal.band}, nominal {signal.nominal_frequency_hz / 1e6:.6f} MHz'
                        + (', X = carrier offset (kHz)' if signal.fdma else ''))

        sub = df[df['constellation'] == csv_name]
        if not signal.fdma:
            deviation = (sub['frequency'] - signal.nominal_frequency_hz).abs().max()
            if deviation > FREQUENCY_TOLERANCE_HZ:
                logger.warning(f'{csv_name}: frequency deviates up to {deviation:.0f} Hz from nominal')

    position = None
    positions = {locations[c] for c in df['constellation'].unique() if c in locations}
    if positions:
        position = sorted(positions)[0]
        if len(positions) > 1:
            logger.warning('Receiver position differs among constellations; using the first one')

    # Observation values per satellite, following the observation types
    values = np.full((len(df), 3), np.nan)
    values[:, 0] = df['doppler'].to_numpy()
    values[:, 1] = df['snr'].to_numpy()
    for csv_name, constellation in CSV_CONSTELLATIONS.items():
        signal = LEO_SIGNALS[constellation]
        if signal.fdma:
            mask = (df['constellation'] == csv_name).to_numpy()
            values[mask, 2] = (df['frequency'].to_numpy()[mask] - signal.nominal_frequency_hz) / 1e3

    df = df.assign(row_idx=np.arange(len(df)))
    # Explicit division as pandas may hold datetimes with a resolution other than ns
    df['_ns'] = (df['timestamp'] - pd.Timestamp('1970-01-01')) // pd.Timedelta(1, 'ns')
    df['_ns'] = (np.round(df['_ns'] / EPOCH_RESOLUTION_NS) * EPOCH_RESOLUTION_NS).astype('int64')

    epochs = []
    for ns, group in sorted(df.groupby('_ns'), key=lambda item: item[0]):
        satellites = []
        for row in group.itertuples():
            constellation = CSV_CONSTELLATIONS[row.constellation]
            n_values = len(LEO_SIGNALS[constellation].obs_types)
            satellites.append((Satellite(constellation, norad[row.satellite_name]),
                               [None if np.isnan(v) else float(v) for v in values[row.row_idx, :n_values]]))
        satellites.sort(key=lambda s: str(s[0]))
        epochs.append((_to_epoch(int(ns), time_system), satellites))

    header = ObsHeader(obs_types=obs_types, marker_name=marker_name, approx_position_xyz=position,
                       time_system=time_system, comments=comments,
                       first_obs=epochs[0][0], last_obs=epochs[-1][0])
    write_obs(output, header, epochs)

    return len(epochs)


def cli(args=None) -> None:

    parser = argparse.ArgumentParser(description='Convert a LEO CSV (Doppler and SNR) into a RINEX-LEO observation file')
    parser.add_argument('csv', help='Input CSV file')
    parser.add_argument('-o', '--output', help='Output RINEX-LEO file (default: stdout)')
    parser.add_argument('--marker-name', default='LEO', help='Marker name for the header (default: %(default)s)')
    parser.add_argument('--constellations', nargs='+', choices=sorted(CSV_CONSTELLATIONS),
                        help='Constellations to convert (default: all)')
    parser.add_argument('--norad-map', help='JSON file {"SATELLITE NAME": norad_id} taking precedence over the bundled ids')
    parser.add_argument('--online', action='store_true', help='Look up unknown satellite names in Celestrak')
    parser.add_argument('--time-system', choices=['gps', 'utc'], default='gps',
                        help='Time system of the epochs (default: %(default)s)')
    parsed = parser.parse_args(args)

    overrides = load_norad_map(parsed.norad_map) if parsed.norad_map else None
    resolver = SatNameResolver(overrides, online=parsed.online)

    out = open(parsed.output, 'w', encoding='utf-8') if parsed.output else sys.stdout
    try:
        convert(parsed.csv, out, parsed.marker_name, parsed.constellations, resolver, parsed.time_system)
    finally:
        if parsed.output:
            out.close()
