import datetime
import math
import os
import pandas as pd
from typing import List, Tuple

from .. import time
from ..constants import SPEED_OF_LIGHT
from ..gnss.types import ConstellationId, TrackingChannel, Satellite

from .defs import RINEX_BAND_MAP, RINEX_LINE_SYS_OBS_TYPES
from .observables import EpochFlag, ObservableType, ObservableValue, Record


def get_channels(observables: List[ObservableType]) -> List[TrackingChannel]:
    """
    Get the channel list from a list of observables

    >>> C1C = ObservableType.from_string("C1C")
    >>> L1C = ObservableType.from_string("L1C")
    >>> C1W = ObservableType.from_string("C1W")
    >>> C2W = ObservableType.from_string("C2W")
    >>> L2W = ObservableType.from_string("L2W")
    >>> C2L = ObservableType.from_string("C2L")
    >>> L2L = ObservableType.from_string("L2L")
    >>> C5Q = ObservableType.from_string("C5Q")
    >>> L5Q = ObservableType.from_string("L5Q")
    >>> get_channels([C1C, L1C, C1W, C2W, L2W, C2L, L2L, C5Q, L5Q])
    [1C, 1W, 2W, 2L, 5Q]
    """

    res = []
    for observable in observables:
        channel = observable.channel

        if channel not in res:
            res.append(channel)

    return res


def get_obs_mapping(lines: List[str]) -> dict:
    """
    Get the observable mappings for a constellation

    >>> line = "G    9 C1C L1C C1W C2W L2W C2L L2L C5Q L5Q                  SYS / # / OBS TYPES"
    >>> get_obs_mapping([line])
    {'G': [C1C, L1C, C1W, C2W, L2W, C2L, L2L, C5Q, L5Q]}

    >>> lines = ["G   20 C1C L1C D1C S1C C1W L1W D1W S1W C2W L2W D2W S2W C2L  SYS / # / OBS TYPES", \
                 "       L2L D2L S2L C5Q L5Q D5Q S5Q                          SYS / # / OBS TYPES"]
    >>> get_obs_mapping(lines)
    {'G': [C1C, L1C, D1C, S1C, C1W, L1W, D1W, S1W, C2W, L2W, D2W, S2W, C2L, L2L, D2L, S2L, C5Q, L5Q, D5Q, S5Q]}
    """

    constellation = None
    values = None

    for line in lines:

        constellation_letter = line[0] if line[0] != ' ' else None
        values_partial = [ObservableType.from_string(s) for s in line[6:60].split()]

        if constellation_letter:
            constellation = constellation_letter
            values = values_partial

        else:
            values.extend(values_partial)

    return {constellation: values}


def to_dataframe(rinex_file: str, station_name=None) -> pd.DataFrame:
    """
    Convert a RINEX file to a pandas DataFrame structure
    """

    station_name_inferred = os.path.basename(rinex_file)[0:4]

    with open(rinex_file, 'r', encoding='utf-8') as file:

        constellation_observables = {}
        records = []

        # Header parsing
        for line in file:

            if "END OF HEADER" in line:
                break

            if RINEX_LINE_SYS_OBS_TYPES in line:
                lines = [line]

                n_observables = int(line[1:6])
                n_extra_lines = (n_observables - 1) // 13 if n_observables > 13 else 0
                for _ in range(n_extra_lines):
                    lines.append(next(file))

                constellation_observables.update(get_obs_mapping(lines))

            if "MARKER NAME" in line:
                station_name_inferred = line[0:4]

        # Body parsing
        for line in file:

            epoch_flag = EpochFlag.get_from_line(line)

            if epoch_flag == EpochFlag.OK:

                epoch, _, n_lines = _parse_rnx3_epoch(line)

                for _ in range(n_lines):

                    line = next(file)

                    constellation = line[0]

                    observable_types = constellation_observables.get(constellation, None)
                    if observable_types is None:
                        continue

                    n_obs = len(observable_types)
                    channels = get_channels(observable_types)
                    satellite, observable_values = _parse_obs_line(line, n_obs)

                    epoch_records = [
                        Record(epoch, satellite, channel, math.nan, math.nan, math.nan, math.nan, 0)
                        for channel in channels]

                    # Create a dictionary with channels as keys and records as values
                    epoch_records_dict = {record.channel: record for record in epoch_records}

                    for observable_type, observable_value in zip(observable_types, observable_values):

                        record = epoch_records_dict.get(observable_type.channel, None)
                        if record is not None:
                            record.set_value(observable_type, observable_value)

                    records.extend(epoch_records)

            else:
                n_lines_to_skip = int(line[33:])
                for _ in range(n_lines_to_skip):
                    line = next(file)

        dataframe = pd.DataFrame([record.aslist() for record in records], columns=Record.get_list_fieldnames())
        station_name_lowercase = str.lower(station_name if station_name is not None else station_name_inferred)
        dataframe['station'] = station_name_lowercase

        return dataframe


class Obs:

    def __init__(self, filename: str):
        self.filename = filename
        self.data = to_dataframe(self.filename)
        timetags = sorted(set([ts.to_pydatetime() for ts in self.data['epoch']]))
        if len(timetags) > 1:
            self.interval = time.get_interval(timetags)

    def compute_detrended_code_minus_carrier(self) -> pd.DataFrame:
        self.count_cycle_slips()

        grouped_data = self.data.groupby(['channel', 'sat', 'slipc'], group_keys=False)
        self.data = grouped_data.apply(lambda df: self.__compute_grouped_detrended_cmc(df))

    def count_cycle_slips(self):
        grouped_data = self.data.groupby(['channel', 'sat'])
        self.data['slipc'] = grouped_data['slip'].transform(lambda slip: slip.cumsum())

    def __compute_grouped_detrended_cmc(self, grouped_df):
        # grouped_df is rinex_obs.data grouped by 'channel', 'sat' and 'slipc'
        const = grouped_df['constellation'].iloc[0]
        constellation_id = ConstellationId.from_string(const)

        chan = grouped_df['channel'].iloc[0]
        band_frequency = RINEX_BAND_MAP[constellation_id][chan[0]]
        wavelength = SPEED_OF_LIGHT / band_frequency

        cmc = grouped_df['range'] - grouped_df['phase'] * wavelength

        CMC_ROLL_WINDOW_SAMPLES = 600 / self.interval
        if len(cmc) >= CMC_ROLL_WINDOW_SAMPLES:
            trend = cmc.rolling(20).median()
        else:
            trend = cmc.mean()

        grouped_df['cmc_detrended'] = cmc - trend

        return grouped_df


def _parse_obs_line(line: str, n_obs: int) -> Tuple[Satellite, List[ObservableValue]]:
    """

    >>> line = "C05  40058862.469 6 208597044.05206  40058858.572 7 161300483.44407  40058861.947 7 169502210.29507"
    >>> _parse_obs_line(line, 6)
    (C05, [ObservableValue(value=40058862.469, lli=0, snr=6), \
ObservableValue(value=208597044.052, lli=0, snr=6), \
ObservableValue(value=40058858.572, lli=0, snr=7), \
ObservableValue(value=161300483.444, lli=0, snr=7), \
ObservableValue(value=40058861.947, lli=0, snr=7), \
ObservableValue(value=169502210.295, lli=0, snr=7)])
    """

    satellite = Satellite.from_string(line[0:3])

    observable_values = []

    offset = 3
    for i_obs in range(n_obs):
        start = offset + i_obs * 16
        obs_str = line[start:start + 14]
        lli_str = line[start + 14:start + 14 + 1]
        snr_str = line[start + 15:start + 15 + 1]

        obs = float(obs_str) if obs_str and obs_str != '              ' and obs_str != '\n' else math.nan
        lli = int(lli_str) if lli_str and lli_str != ' ' and lli_str != '\n' else 0
        snr = int(snr_str) if snr_str and snr_str != ' ' and snr_str != '\n' else 0

        observable_values.append(ObservableValue(obs, lli, snr))

    return satellite, observable_values


def _parse_rnx3_epoch(line):
    """
    Parse a measurement epoch from a Rinex3 and return a tuple
    with the epochm event type and number of lines

    >>> _parse_rnx3_epoch("> 2017 08 03 11 22 30.1234000  0 29")
    (datetime.datetime(2017, 8, 3, 11, 22, 30, 123400), 0, 29)

    >>> _parse_rnx3_epoch("> 2021  2  5 15 51 30.2000000 0 22")
    (datetime.datetime(2021, 2, 5, 15, 51, 30, 200000), 0, 22)

    >>> _parse_rnx3_epoch("> 2020 11 18 21 43 30.0000000  0 28       0.000000000000")
    (datetime.datetime(2020, 11, 18, 21, 43, 30), 0, 28)

    >>> _parse_rnx3_epoch("> 2019 07 02 13 25  5.9999995  0 31")
    (datetime.datetime(2019, 7, 2, 13, 25, 5, 999999), 0, 31)
    """

    try:
        _, year, month, day, hour, minute, seconds, epoch_flag, n_lines, *b = line.split()
    except ValueError as e:
        raise ValueError(f"Invalid Rinex 3 epoch line [ {line} ]: {e}")

    seconds, microseconds, *b = seconds.split('.')

    t = datetime.datetime(int(year), int(month), int(day),
                          hour=int(hour), minute=int(minute), second=int(seconds),
                          microsecond=int(microseconds[0:6]))

    return t, int(epoch_flag), int(n_lines)
