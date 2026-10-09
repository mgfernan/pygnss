from dataclasses import dataclass
from typing import Dict, List

from ..gnss.types import ConstellationId

# Attribute of the observation code used for all the LEO signals of opportunity
SIGNAL_ATTRIBUTE = 'C'

# Observable type used to store the carrier frequency of FDMA signals: offset (kHz)
# with respect to the nominal frequency of the band
CARRIER_OFFSET_OBS_TYPE = 'X'


@dataclass(frozen=True)
class LeoSignal:
    """
    Signal definition of a LEO constellation in RINEX-LEO

    Attributes:
        band: RINEX band digit
        nominal_frequency_hz: Nominal (center) frequency of the band
        fdma: Whether the carrier frequency changes among transmissions (FDMA), in
              which case the offset with respect to the nominal frequency is stored
              in an extra observable
    """
    band: int
    nominal_frequency_hz: float
    fdma: bool = False

    @property
    def obs_types(self) -> List[str]:
        """
        Observation types, in the order they are written to the RINEX file

        >>> LEO_SIGNALS[ConstellationId.GLOBALSTAR].obs_types
        ['D9C', 'S9C']
        >>> LEO_SIGNALS[ConstellationId.ORBCOMM].obs_types
        ['D3C', 'S3C', 'X3C']
        """

        suffix = f'{self.band}{SIGNAL_ATTRIBUTE}'
        types = [f'D{suffix}', f'S{suffix}']
        if self.fdma:
            types.append(f'{CARRIER_OFFSET_OBS_TYPE}{suffix}')
        return types

    def carrier_offset_khz(self, frequency_hz: float) -> float:
        """
        >>> LEO_SIGNALS[ConstellationId.ORBCOMM].carrier_offset_khz(137287500)
        -212.5
        """

        return (frequency_hz - self.nominal_frequency_hz) / 1e3


# Band digits: 9 is the S-band of the RINEX-LEO proposal. 6 (Iridium L-band, ~1626 MHz)
# and 3 (Orbcomm VHF, 137-138 MHz) are only meaningful within their own constellation
LEO_SIGNALS: Dict[ConstellationId, LeoSignal] = {
    ConstellationId.GLOBALSTAR: LeoSignal(9, 2486100000.0),
    ConstellationId.IRIDIUM: LeoSignal(6, 1626270833.0),
    ConstellationId.ORBCOMM: LeoSignal(3, 137500000.0, fdma=True),
}
