from abc import ABC, abstractmethod
import math
from typing import List, Tuple

from ..gnss.types import ConstellationId, Satellite, MEO_SATELLITE_ID_DIGITS, LEO_SATELLITE_ID_DIGITS
from .observables import ObservableValue

# Each observation is F14.3 followed by the LLI and signal strength indicators
OBSERVATION_FIELD_WIDTH = 16
OBSERVATION_VALUE_WIDTH = 14


class ObsLineParser(ABC):
    """
    Parser of the satellite lines of a RINEX observation data record. Implementations
    differ in the width of the satellite identifier at the beginning of the line.
    """

    @property
    @abstractmethod
    def sat_id_width(self) -> int:
        """Number of characters of the satellite identifier (constellation letter included)"""

    def parse(self, line: str, n_obs: int) -> Tuple[Satellite, List[ObservableValue]]:

        satellite = Satellite.from_string(line[0:self.sat_id_width])

        observable_values = []

        for i_obs in range(n_obs):
            start = self.sat_id_width + i_obs * OBSERVATION_FIELD_WIDTH
            obs_str = line[start:start + OBSERVATION_VALUE_WIDTH].strip()
            lli_str = line[start + 14:start + 15].strip()
            snr_str = line[start + 15:start + 16].strip()

            obs = float(obs_str) if obs_str else math.nan
            lli = int(lli_str) if lli_str else 0
            snr = int(snr_str) if snr_str else 0

            observable_values.append(ObservableValue(obs, lli, snr))

        return satellite, observable_values


class MeoObsLineParser(ObsLineParser):
    """Parser for MEO GNSS lines (A1,I2 satellite identifier)"""

    @property
    def sat_id_width(self) -> int:
        return 1 + MEO_SATELLITE_ID_DIGITS


class LeoObsLineParser(ObsLineParser):
    """Parser for LEO lines (A1,I6 satellite identifier), as defined by RINEX-LEO"""

    @property
    def sat_id_width(self) -> int:
        return 1 + LEO_SATELLITE_ID_DIGITS


_MEO_PARSER = MeoObsLineParser()
_LEO_PARSER = LeoObsLineParser()


def get_obs_line_parser(constellation_char: str) -> ObsLineParser:
    """
    Get the observation line parser suitable for a constellation

    >>> type(get_obs_line_parser('G')).__name__
    'MeoObsLineParser'
    >>> type(get_obs_line_parser('X')).__name__
    'LeoObsLineParser'
    """

    constellation = ConstellationId.from_string(constellation_char)
    return _LEO_PARSER if constellation.is_leo() else _MEO_PARSER


def parse_obs_line(line: str, n_obs: int) -> Tuple[Satellite, List[ObservableValue]]:
    """
    Parse a satellite line of an observation record, selecting the MEO or LEO
    format from the constellation letter

    >>> line = "C05  40058862.469 6 208597044.05206  40058858.572 7 161300483.44407  40058861.947 7 169502210.29507"
    >>> parse_obs_line(line, 6)
    (C05, [ObservableValue(value=40058862.469, lli=0, snr=6), \
ObservableValue(value=208597044.052, lli=0, snr=6), \
ObservableValue(value=40058858.572, lli=0, snr=7), \
ObservableValue(value=161300483.444, lli=0, snr=7), \
ObservableValue(value=40058861.947, lli=0, snr=7), \
ObservableValue(value=169502210.295, lli=0, snr=7)])

    >>> parse_obs_line("Z043012    732793.036      732794.384", 2)
    (Z043012, [ObservableValue(value=732793.036, lli=0, snr=0), ObservableValue(value=732794.384, lli=0, snr=0)])
    """

    return get_obs_line_parser(line[0]).parse(line, n_obs)
