from abc import ABC, abstractmethod
import enum

from ..gnss.types import ConstellationId



class EphType(enum.Enum):

    GPS_LNAV = f'{ConstellationId.GPS.value}_LNAV'
    GPS_CNAV = f'{ConstellationId.GPS.value}_CNAV'
    GPS_CNV2 = f'{ConstellationId.GPS.value}_CNV2'
    GAL_INAV = f'{ConstellationId.GALILEO.value}_INAV'
    GAL_FNAV = f'{ConstellationId.GALILEO.value}_FNAV'
    GLO_FDMA = f'{ConstellationId.GLONASS.value}_FDMA'
    QZS_LNAV = f'{ConstellationId.QZSS.value}_LNAV'
    QZS_CNAV = f'{ConstellationId.QZSS.value}_CNAV'
    QZS_CNV2 = f'{ConstellationId.QZSS.value}_CNV2'
    BDS_D1 = f'{ConstellationId.BEIDOU.value}_D1'
    BDS_D2 = f'{ConstellationId.BEIDOU.value}_D2'
    BDS_CNV1 = f'{ConstellationId.BEIDOU.value}_CNV1'
    BDS_CNV2 = f'{ConstellationId.BEIDOU.value}_CNV2'
    BDS_CNV3 = f'{ConstellationId.BEIDOU.value}_CNV3'
    SBS = f'{ConstellationId.SBAS.value}_SBAS'
    IRN_LNAV = f'{ConstellationId.IRNSS.value}_LNAV'
    LEO = f'{ConstellationId.LEO.value}'
    SPIRE = f'{ConstellationId.SPIRE.value}'
    STARLINK = f'{ConstellationId.STARLINK.value}'
    ONEWEB = f'{ConstellationId.ONEWEB.value}'

    @staticmethod
    def from_string(value: str) -> 'EphType':
        """
        Get the Ephemerides type from an input string (or raise an exception if not found)

        >>> EphType.from_string('G_LNAV')
        <EphType.GPS_LNAV: 'G_LNAV'>
        """

        for member in EphType:
            if member.value == value:
                return member

        raise ValueError(f"Value [ {value} ] could not be mapped into a Rinex 4 ephemeris type")


class RinexSatIdProvider(ABC):
    """
    This abstract class provides an interface to provide the RINEX Satellite ID and constellation
    """
    @abstractmethod
    def get_constellation_letter(self) -> str:
        pass

    def get_sat_number(self, norad_id) -> int:
        return norad_id


class RinexSatIdFactory:
    @staticmethod
    def create(constellation: ConstellationId) -> RinexSatIdProvider:
        if constellation == ConstellationId.STARLINK:
            return StarlinkRNXId()
        elif constellation == ConstellationId.SPIRE:
            return SpireRNXId()
        elif constellation == ConstellationId.ONEWEB:
            return OneWebRNXId()
        else:
            raise ValueError("Invalid constellation")


class StarlinkRNXId(RinexSatIdProvider):
    def get_constellation_letter(self) -> str:
        return ConstellationId.STARLINK.value


class SpireRNXId(RinexSatIdProvider):
    def get_constellation_letter(self) -> str:
        return ConstellationId.SPIRE.value


class OneWebRNXId(RinexSatIdProvider):
    def get_constellation_letter(self) -> str:
        return ConstellationId.ONEWEB.value
