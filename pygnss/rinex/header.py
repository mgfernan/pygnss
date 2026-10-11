from dataclasses import dataclass, field
import re
from typing import Dict, Iterator, List, Optional, Tuple

from .defs import RINEX_LINE_SYS_OBS_TYPES
from .observables import ObservableType

RINEX_LINE_VERSION_TYPE = "RINEX VERSION / TYPE"
RINEX_LINE_LEO_EXTENSION = "RINEX-LEO EXTENSION"
RINEX_LINE_END_OF_HEADER = "END OF HEADER"
RINEX_LINE_MARKER_NAME = "MARKER NAME"
RINEX_LINE_APPROX_POSITION = "APPROX POSITION XYZ"

LEO_EXTENSION_NAME = "RINEX-LEO"

# Highest RINEX-LEO extension version understood by this reader
SUPPORTED_LEO_EXTENSION_MAJOR = 2
SUPPORTED_LEO_EXTENSION_MINOR = 0

_MAX_OBS_TYPES_PER_LINE = 13
_LABEL_START = 60

_TYPE_PATTERN = re.compile(r'\s*(\w)[^\n]*?DATA\s*(\w)?')
_LEO_EXTENSION_PATTERN = re.compile(rf'^{LEO_EXTENSION_NAME}\s+(\d+)\.(\d+)\s*$')


class InvalidRinexHeader(ValueError):
    """The RINEX header is malformed"""


class InvalidLeoExtension(InvalidRinexHeader):
    """The RINEX-LEO extension header record is missing, misplaced or malformed"""


class UnsupportedLeoExtensionVersion(InvalidLeoExtension):
    """The RINEX-LEO extension version cannot be interpreted by this reader"""


@dataclass
class RinexHeader:
    """
    Subset of the RINEX header records needed by the readers
    """

    version: float
    file_type: str
    satellite_system: str
    leo_extension_version: Optional[Tuple[int, int]] = None
    marker_name: Optional[str] = None
    approx_position_xyz: Optional[Tuple[float, float, float]] = None
    obs_types: Dict[str, List[ObservableType]] = field(default_factory=dict)

    @property
    def is_leo(self) -> bool:
        """Whether the file declares the RINEX-LEO extension"""
        return self.leo_extension_version is not None


def _get_label(line: str) -> str:
    return line[_LABEL_START:].strip()


def _parse_type_and_system(line: str) -> Tuple[str, str]:
    """
    Extract file type and satellite system from RINEX VERSION / TYPE, tolerating
    small column misalignments

    >>> _parse_type_and_system("     4.01           OBSERVATION DATA    M                   RINEX VERSION / TYPE")
    ('O', 'M')
    >>> _parse_type_and_system("     4.01          OBSERVATION DATA    M                    RINEX VERSION / TYPE")
    ('O', 'M')
    >>> _parse_type_and_system("     4.00           N: GNSS NAV DATA    G: GPS              RINEX VERSION / TYPE")
    ('N', 'G')
    """

    match = _TYPE_PATTERN.match(line[9:_LABEL_START])
    return (match.group(1), match.group(2) or '') if match else ('', '')


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


def parse_leo_extension_line(line: str) -> Tuple[int, int]:
    """
    Parse the RINEX-LEO EXTENSION header record and validate the version

    >>> parse_leo_extension_line("RINEX-LEO 2.00                                              RINEX-LEO EXTENSION")
    (2, 0)
    >>> parse_leo_extension_line("RINEX-LEO 1.00                                              RINEX-LEO EXTENSION")
    Traceback (most recent call last):
    ...
    pygnss.rinex.header.UnsupportedLeoExtensionVersion: Unsupported RINEX-LEO extension version 1.0 (supported: 2.x)
    >>> parse_leo_extension_line("LEO 1.00                                                    RINEX-LEO EXTENSION")
    Traceback (most recent call last):
    ...
    pygnss.rinex.header.InvalidLeoExtension: Invalid RINEX-LEO EXTENSION record [ LEO 1.00 ]
    """

    match = _LEO_EXTENSION_PATTERN.match(line[:_LABEL_START].strip())
    if match is None:
        raise InvalidLeoExtension(f"Invalid {RINEX_LINE_LEO_EXTENSION} record [ {line[:_LABEL_START].strip()} ]")

    major, minor = int(match.group(1)), int(match.group(2))

    # Minor versions are backward compatible, major ones are not
    if major != SUPPORTED_LEO_EXTENSION_MAJOR:
        raise UnsupportedLeoExtensionVersion(
            f"Unsupported RINEX-LEO extension version {major}.{minor} (supported: {SUPPORTED_LEO_EXTENSION_MAJOR}.x)")

    return major, minor


def parse_header(lines: Iterator[str]) -> RinexHeader:
    """
    Parse a RINEX header, consuming the lines up to (and including) END OF HEADER

    >>> doc = [
    ... "     4.01           OBSERVATION DATA    M                   RINEX VERSION / TYPE",
    ... "RINEX-LEO 2.00                                              RINEX-LEO EXTENSION",
    ... "G    4 C1C L1C C2W L2W                                      SYS / # / OBS TYPES",
    ... "Z    2 D1C S1C                                              SYS / # / OBS TYPES",
    ... "                                                            END OF HEADER"]
    >>> header = parse_header(iter(doc))
    >>> header.version, header.file_type, header.satellite_system, header.leo_extension_version
    (4.01, 'O', 'M', (2, 0))
    >>> header.obs_types['Z']
    [D1C, S1C]
    """

    lines = iter(lines)

    version = None
    file_type = None
    satellite_system = None
    leo_extension_version = None
    n_leo_records = 0
    marker_name = None
    approx_position_xyz = None
    obs_types = {}

    for i_line, line in enumerate(lines):

        label = _get_label(line)

        if i_line == 0 and label != RINEX_LINE_VERSION_TYPE:
            raise InvalidRinexHeader(f"The first header record must be {RINEX_LINE_VERSION_TYPE}")

        if label == RINEX_LINE_VERSION_TYPE:
            try:
                version = float(line[0:9])
            except ValueError:
                raise InvalidRinexHeader(f"Invalid {RINEX_LINE_VERSION_TYPE} record [ {line.rstrip()} ]")
            file_type, satellite_system = _parse_type_and_system(line)

        elif label == RINEX_LINE_LEO_EXTENSION:
            n_leo_records += 1
            if n_leo_records > 1:
                raise InvalidLeoExtension(f"{RINEX_LINE_LEO_EXTENSION} record must appear exactly once")
            if i_line != 1:
                raise InvalidLeoExtension(f"{RINEX_LINE_LEO_EXTENSION} record must follow {RINEX_LINE_VERSION_TYPE}")
            leo_extension_version = parse_leo_extension_line(line)

        elif label == RINEX_LINE_SYS_OBS_TYPES:
            obs_lines = [line]

            n_observables = int(line[1:6])
            n_extra_lines = (n_observables - 1) // _MAX_OBS_TYPES_PER_LINE
            for _ in range(n_extra_lines):
                obs_lines.append(next(lines))

            obs_types.update(get_obs_mapping(obs_lines))

        elif label == RINEX_LINE_MARKER_NAME:
            marker_name = line[:_LABEL_START].strip()

        elif label == RINEX_LINE_APPROX_POSITION:
            x, y, z = (float(v) for v in line[:_LABEL_START].split()[:3])
            approx_position_xyz = (x, y, z)

        elif label == RINEX_LINE_END_OF_HEADER:
            break

    if version is None:
        raise InvalidRinexHeader(f"Missing {RINEX_LINE_VERSION_TYPE} record")

    return RinexHeader(version, file_type, satellite_system, leo_extension_version,
                       marker_name, approx_position_xyz, obs_types)
