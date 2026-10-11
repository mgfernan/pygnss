import datetime
import math
from dataclasses import dataclass, field
from typing import Dict, IO, Iterable, List, Optional, Sequence, Tuple

from ..gnss.types import Satellite
from .header import (LEO_EXTENSION_NAME, RINEX_LINE_APPROX_POSITION, RINEX_LINE_END_OF_HEADER,
                     RINEX_LINE_LEO_EXTENSION, RINEX_LINE_MARKER_NAME, RINEX_LINE_VERSION_TYPE,
                     SUPPORTED_LEO_EXTENSION_MAJOR, SUPPORTED_LEO_EXTENSION_MINOR)
from .defs import RINEX_LINE_SYS_OBS_TYPES

RINEX_VERSION = 4.01
RINEX_LINE_PGM_RUN_BY_DATE = "PGM / RUN BY / DATE"
RINEX_LINE_COMMENT = "COMMENT"
RINEX_LINE_TIME_OF_FIRST_OBS = "TIME OF FIRST OBS"
RINEX_LINE_TIME_OF_LAST_OBS = "TIME OF LAST OBS"

_MAX_OBS_TYPES_PER_LINE = 13
_BLANK_OBSERVATION = ' ' * 16


@dataclass
class ObsHeader:
    """
    Information required to write the header of a RINEX-LEO observation file
    """

    obs_types: Dict[str, List[str]]
    marker_name: str = 'UNKN'
    approx_position_xyz: Optional[Tuple[float, float, float]] = None
    time_system: str = 'GPS'
    program: str = 'pygnss'
    run_by: str = ''
    date: Optional[datetime.datetime] = None
    first_obs: Optional[datetime.datetime] = None
    last_obs: Optional[datetime.datetime] = None
    comments: List[str] = field(default_factory=list)


def _record(content: str, label: str) -> str:
    return f'{content:<60.60}{label}\n'


def format_time_of_obs(epoch: datetime.datetime, time_system: str, label: str) -> str:
    """
    Format a TIME OF FIRST/LAST OBS header record

    >>> format_time_of_obs(datetime.datetime(2026, 10, 1, 0, 0, 1, 616990), 'GPS', 'TIME OF FIRST OBS').rstrip()
    '  2026    10     1     0     0    1.6169900     GPS         TIME OF FIRST OBS'
    """

    seconds = epoch.second + epoch.microsecond * 1e-6
    content = (f'{epoch.year:6d}{epoch.month:6d}{epoch.day:6d}{epoch.hour:6d}{epoch.minute:6d}'
               f'{seconds:13.7f}     {time_system:<3s}')
    return _record(content, label)


def format_header(header: ObsHeader) -> str:
    """
    Format the header of a RINEX-LEO observation file

    >>> h = ObsHeader({'X': ['D1C', 'S1C']}, marker_name='LEO1', date=datetime.datetime(2026, 1, 2, 3, 4, 5))
    >>> print(format_header(h), end='')
         4.01           OBSERVATION DATA    M                   RINEX VERSION / TYPE
    RINEX-LEO 2.00                                              RINEX-LEO EXTENSION
    pygnss                                  20260102 030405 UTC PGM / RUN BY / DATE
    LEO1                                                        MARKER NAME
    X    2 D1C S1C                                              SYS / # / OBS TYPES
                                                                END OF HEADER
    """

    date = header.date or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    out = _record(f'{RINEX_VERSION:9.2f}{"":11s}{"OBSERVATION DATA":<20s}{"M":<20s}', RINEX_LINE_VERSION_TYPE)
    out += _record(f'{LEO_EXTENSION_NAME} {SUPPORTED_LEO_EXTENSION_MAJOR}.{SUPPORTED_LEO_EXTENSION_MINOR:02d}',
                   RINEX_LINE_LEO_EXTENSION)
    out += _record(f'{header.program:<20s}{header.run_by:<20s}{date:%Y%m%d %H%M%S} UTC', RINEX_LINE_PGM_RUN_BY_DATE)

    for comment in header.comments:
        out += _record(comment, RINEX_LINE_COMMENT)

    out += _record(header.marker_name, RINEX_LINE_MARKER_NAME)

    if header.approx_position_xyz is not None:
        x, y, z = header.approx_position_xyz
        out += _record(f'{x:14.4f}{y:14.4f}{z:14.4f}', RINEX_LINE_APPROX_POSITION)

    for constellation in sorted(header.obs_types):
        obs_types = header.obs_types[constellation]
        for i_start in range(0, len(obs_types), _MAX_OBS_TYPES_PER_LINE):
            chunk = obs_types[i_start:i_start + _MAX_OBS_TYPES_PER_LINE]
            prefix = f'{constellation:1s}  {len(obs_types):3d}' if i_start == 0 else ' ' * 6
            out += _record(prefix + ''.join(f' {t:3s}' for t in chunk), RINEX_LINE_SYS_OBS_TYPES)

    if header.first_obs is not None:
        out += format_time_of_obs(header.first_obs, header.time_system, RINEX_LINE_TIME_OF_FIRST_OBS)
    if header.last_obs is not None:
        out += format_time_of_obs(header.last_obs, header.time_system, RINEX_LINE_TIME_OF_LAST_OBS)

    out += _record('', RINEX_LINE_END_OF_HEADER)
    return out


def format_epoch_line(epoch: datetime.datetime, n_satellites: int, epoch_flag: int = 0,
                      clock_offset_s: Optional[float] = None) -> str:
    """
    Format an epoch record (RINEX 4 format, 100 ns resolution)

    >>> format_epoch_line(datetime.datetime(2022, 12, 20, 12, 1, 4, 603000), 30)
    '> 2022 12 20 12  1  4.6030000  0 30'
    >>> format_epoch_line(datetime.datetime(2022, 12, 20, 12, 1, 4, 603000), 2, clock_offset_s=1.5e-6)
    '> 2022 12 20 12  1  4.6030000  0  2       0.000001500000'
    """

    seconds = epoch.second + epoch.microsecond * 1e-6
    line = (f'> {epoch.year:4d} {epoch.month:2d} {epoch.day:2d} {epoch.hour:2d} {epoch.minute:2d}'
            f'{seconds:11.7f}  {epoch_flag:1d}{n_satellites:3d}')

    if clock_offset_s is not None:
        line += f'{"":6s}{clock_offset_s:15.12f}'

    return line


def format_obs_line(satellite: Satellite, values: Sequence[Optional[float]],
                    llis: Optional[Sequence[int]] = None, snrs: Optional[Sequence[int]] = None) -> str:
    """
    Format the observation line of a satellite. The satellite identifier is A1,I2
    for MEO satellites and A1,I6 for LEO ones (RINEX-LEO extension).
    Missing (None or NaN) observations are left blank

    >>> format_obs_line(Satellite.from_string('Z043012'), [732793.036, 732794.384])
    'Z043012    732793.036      732794.384'
    >>> format_obs_line(Satellite.from_string('G23'), [24718012.436, None, 1.0], snrs=[7, 0, 0])
    'G23  24718012.436 7                         1.000'
    """

    line = str(satellite)

    for i_obs, value in enumerate(values):
        if value is None or math.isnan(value):
            line += _BLANK_OBSERVATION
            continue

        lli = llis[i_obs] if llis else 0
        snr = snrs[i_obs] if snrs else 0
        line += f'{value:14.3f}{lli if lli else " "}{snr if snr else " "}'

    return line.rstrip()


def write_obs(output: IO, header: ObsHeader,
              epochs: Iterable[Tuple[datetime.datetime, Sequence[Tuple[Satellite, Sequence[Optional[float]]]]]]) -> None:
    """
    Write a RINEX-LEO observation file

    The epochs are tuples of the epoch and the list of (satellite, observation values),
    where the values follow the sequence of observation types of the constellation
    in the header.
    """

    output.write(format_header(header))

    for epoch, satellite_observations in epochs:
        output.write(format_epoch_line(epoch, len(satellite_observations)) + '\n')
        for satellite, values in satellite_observations:
            expected = len(header.obs_types[satellite.constellation.value])
            if len(values) != expected:
                raise ValueError(f'Satellite {satellite} has {len(values)} values, expected {expected}')
            output.write(format_obs_line(satellite, values) + '\n')
