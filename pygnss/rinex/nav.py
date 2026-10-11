from abc import ABC, abstractmethod
from dataclasses import dataclass, fields, asdict
import datetime
import math
import pandas as pd
from typing import Dict, List, Union, IO

from .. import logger
from .. import time
from ..file import process_filename_or_file_handler, skip_lines
from ..gnss.types import ConstellationId, TrackingChannel, Satellite, LEO_SATELLITE_ID_DIGITS

from ..orbit.tle import TLE
from ..orbit.kepler import Kepler
from .clock import Clock, CodeBiases, ZeroClockModel, ZeroCodeBiases
from .defs import (A_M_STR, ARG_PERIGEE_DEG_STR, ECCENTRICITY_STR, EPOCH_STR, INCLINATION_DEG_STR,
                   RIGHT_ASCENSION_DEG_STR, SAT_STR, TRUE_ANOMALY_DEG_STR)
from .ids import EphType


@dataclass
class NavBlock(ABC):
    """
    Abstract class for RINEX Navigation block
    """
    satellite: Satellite
    epoch: datetime

    @staticmethod
    def csv_fields() -> str:
        return None

    def to_csv(self) -> str:
        # Get all field names from the __dataclass_fields__ attribute
        field_names = [field.name for field in fields(self)]

        # Get the value of each field from the instance dictionary
        field_values = [getattr(self, field_name) for field_name in field_names]

        # Convert field values to strings and join them with commas
        body = ",".join(map(str, field_values))

        return f'{self.get_type().value},{body}'

    # Custom function to convert each NavBlock to a dict with string satellite
    def to_dict(self):
        block_dict = asdict(self)
        block_dict['satellite'] = str(self.satellite)  # Convert satellite to string
        return block_dict

    @abstractmethod
    def get_type(self) -> EphType:
        return None


@dataclass
class GpsLnavNavBlock(NavBlock):
    clock_bias_s: float
    clock_drift_sps: float
    clock_drift_rate_sps2: float

    iode: int
    crs: float
    deltan: float
    M0: float

    cuc: float
    e: float
    cus: float
    sqrtA: float

    toe_sow: float
    cic: float
    OMEGA0: float
    cis: float

    i0: float
    crc: float
    omega: float
    OMEGA_DOT: float

    idot: float
    codesL2: int
    toe_week: int
    l2p_flag: int

    accuracy: float
    health: int
    tgd: float
    iodc: int

    tx_time_tow: float
    fit_interval: int

    def csv_fields(self) -> str:
        return f"{self.get_type().value},{_SAT_STR},{_EPOCH_STR},\
{_CLK_BIAS_STR},{_CLK_DRIFT_STR},{_CLK_DRIFT_RATE_STR},\
{_IODE_STR},{_CRS_STR},{_DELTAN_STR},{_M0_STR},\
{_CUC_STR},{_E_STR},{_CUS_STR},{_SQRTA_STR},\
{_TOE_SOW_STR},{_CIC_STR},{_OMEGA0_STR},{_CIS_STR},\
{_I0_STR},{_CRC_STR},{_OMEGA_STR},{_OMEGA_DOT_STR},\
{_IDOT_STR},{_CODESL2_STR},{_TOE_WEEK_STR},{_L2PFLAG_STR},\
{_ACCURACY_STR},{_HEALTH_STR},{_TGD_STR},{_IODC_STR},\
{_TX_TIME_TOW_STR},{_FIT_INTERVAL_STR}"

    def get_type(self) -> EphType:
        return EphType.GPS_LNAV


@dataclass
class GpsCnavNavBlock(NavBlock):
    clock_bias_s: float
    clock_drift_sps: float
    clock_drift_rate_sps2: float

    adot: float
    crs: float
    deltan: float
    M0: float

    cuc: float
    e: float
    cus: float
    sqrtA: float

    top: float
    cic: float
    OMEGA0: float
    cis: float

    i0: float
    crc: float
    omega: float
    OMEGA_DOT: float

    idot: float
    deltan_dot: float
    urai_ned0: float
    urai_ned1: float

    urai_ed: float
    health: int
    tgd: float
    urai_ned2: float

    isc_l1ca: float
    isc_l2c: float
    isc_l5i5: float
    isc_l5q5: float

    tx_time_tow: float
    wn_op: int

    def csv_fields(self) -> str:
        return f"{self.get_type().value},{_SAT_STR},{_EPOCH_STR},\
{_CLK_BIAS_STR},{_CLK_DRIFT_STR},{_CLK_DRIFT_RATE_STR},\
{_ADOT_STR},{_CRS_STR},{_DELTAN_STR},{_M0_STR},\
{_CUC_STR},{_E_STR},{_CUS_STR},{_SQRTA_STR},\
{_T_OP_STR},{_CIC_STR},{_OMEGA0_STR},{_CIS_STR},\
{_I0_STR},{_CRC_STR},{_OMEGA_STR},{_OMEGA_DOT_STR},\
{_IDOT_STR},{_DELTAN_DOT_STR},{_URAI_NED0_STR},{_URAI_NED1_STR},\
{_URAI_ED_STR},{_HEALTH_STR},{_TGD_STR},{_URAI_NED2_STR},\
{_ISC_L1CA_STR},{_ISC_L2C_STR},{_ISC_L5I5_STR},{_ISC_L5Q5_STR},\
{_TX_TIME_TOW_STR},{_WN_OP_STR}"

    def get_type(self) -> EphType:
        return EphType.GPS_CNAV


@dataclass
class GpsCnv2NavBlock(NavBlock):
    clock_bias_s: float
    clock_drift_sps: float
    clock_drift_rate_sps2: float

    adot: float
    crs: float
    deltan: float
    M0: float

    cuc: float
    e: float
    cus: float
    sqrtA: float

    top: float
    cic: float
    OMEGA0: float
    cis: float

    i0: float
    crc: float
    omega: float
    OMEGA_DOT: float

    idot: float
    deltan_dot: float
    urai_ned0: float
    urai_ned1: float

    urai_ed: float
    health: int
    tgd: float
    urai_ned2: float

    isc_l1ca: float
    isc_l2c: float
    isc_l5i5: float
    isc_l5q5: float

    isc_l1cd: float
    isc_l1cp: float

    tx_time_tow: float
    wn_op: int

    def csv_fields(self) -> str:
        return f"{self.get_type().value},{_SAT_STR},{_EPOCH_STR},\
{_CLK_BIAS_STR},{_CLK_DRIFT_STR},{_CLK_DRIFT_RATE_STR},\
{_ADOT_STR},{_CRS_STR},{_DELTAN_STR},{_M0_STR},\
{_CUC_STR},{_E_STR},{_CUS_STR},{_SQRTA_STR},\
{_T_OP_STR},{_CIC_STR},{_OMEGA0_STR},{_CIS_STR},\
{_I0_STR},{_CRC_STR},{_OMEGA_STR},{_OMEGA_DOT_STR},\
{_IDOT_STR},{_DELTAN_DOT_STR},{_URAI_NED0_STR},{_URAI_NED1_STR},\
{_URAI_ED_STR},{_HEALTH_STR},{_TGD_STR},{_URAI_NED2_STR},\
{_ISC_L1CA_STR},{_ISC_L2C_STR},{_ISC_L5I5_STR},{_ISC_L5Q5_STR},\
{_ISC_L1CD_STR},{_ISC_L1CP_STR},\
{_TX_TIME_TOW_STR},{_WN_OP_STR}"

    def get_type(self) -> EphType:
        return EphType.GPS_CNV2


@dataclass
class GalNavBlock(NavBlock):
    clock_bias_s: float
    clock_drift_sps: float
    clock_drift_rate_sps2: float

    iodnav: float
    crs: float
    deltan: float
    M0: float

    cuc: float
    e: float
    cus: float
    sqrtA: float

    toe_gal_tow: int
    cic: float
    OMEGA0: float
    cis: float

    i0: float
    crc: float
    omega: float
    OMEGA_DOT: float

    idot: float
    data_source: int
    toe_gal_week: int

    sisa: float
    health: int
    bgd_e5a_e1: float
    bgd_e5b_e1: float

    tx_time_tow: float

    def csv_fields(self) -> str:
        return f"{self.get_type().value},{_SAT_STR},{_EPOCH_STR},\
{_CLK_BIAS_STR},{_CLK_DRIFT_STR},{_CLK_DRIFT_RATE_STR},\
{_IODNAV_STR},{_CRS_STR},{_DELTAN_STR},{_M0_STR},\
{_CUC_STR},{_E_STR},{_CUS_STR},{_SQRTA_STR},\
{_TOE_GAL_TOW_STR},{_CIC_STR},{_OMEGA0_STR},{_CIS_STR},\
{_I0_STR},{_CRC_STR},{_OMEGA_STR},{_OMEGA_DOT_STR},\
{_IDOT_STR},{_DATA_SOURCES_STR},{_TOE_GAL_WEEK_STR},,\
{_SISA_STR},{_HEALTH_STR},{_BGD_E5A_STR},{_BGD_E5B_STR},\
{_TX_TIME_TOW_STR}"

    def get_type(self) -> EphType:
        INAV_MASK = 0b101
        FNAV_MASK = 0b10

        if self.data_source & INAV_MASK:
            return EphType.GAL_INAV
        elif self.data_source & FNAV_MASK:
            return EphType.GAL_FNAV

        raise ValueError(f'Cannot extract the Galileo Eph type from the data sources [ {self.data_source} ]')


@dataclass
class BdsDNavBlock(NavBlock):
    clock_bias_s: float
    clock_drift_sps: float
    clock_drift_rate_sps2: float

    aode: int
    crs: float
    deltan: float
    M0: float

    cuc: float
    e: float
    cus: float
    sqrtA: float

    toe_bdt_tow: int
    cic: float
    OMEGA0: float
    cis: float

    i0: float
    crc: float
    omega: float
    OMEGA_DOT: float

    idot: float
    toe_bdt_week: int

    accuracy: float
    satH1: int
    tgd1: float
    tgd2: float

    tx_time_tow: float
    aodc: int

    eph_type: str

    def csv_fields(self) -> str:
        return f"{self.get_type().value},{_SAT_STR},{_EPOCH_STR},\
{_CLK_BIAS_STR},{_CLK_DRIFT_STR},{_CLK_DRIFT_RATE_STR},\
{_AODE_STR},{_CRS_STR},{_DELTAN_STR},{_M0_STR},\
{_CUC_STR},{_E_STR},{_CUS_STR},{_SQRTA_STR},\
{_TOE_BDT_TOW_STR},{_CIC_STR},{_OMEGA0_STR},{_CIS_STR},\
{_I0_STR},{_CRC_STR},{_OMEGA_STR},{_OMEGA_DOT_STR},\
{_IDOT_STR},{_TOE_BDT_WEEK_STR},\
{_ACCURACY_STR},{_SATH1_STR},{_TGD1_STR},{_TGD2_STR},\
{_TX_TIME_TOW_STR},{_AODC_STR}"

    def get_type(self) -> EphType:
        return EphType.from_string(self.eph_type)


@dataclass
class BdsCnv1NavBlock(NavBlock):
    """
    BEIDOU Navigation message on Beidou-3 B1C signal
    """
    clock_bias_s: float
    clock_drift_sps: float
    clock_drift_rate_sps2: float

    adot: float
    crs: float
    deltan: float
    M0: float

    cuc: float
    e: float
    cus: float
    sqrtA: float

    toe_bdt_tow: int
    cic: float
    OMEGA0: float
    cis: float

    i0: float
    crc: float
    omega: float
    OMEGA_DOT: float

    idot: float
    deltan_dot: float
    sattype: int
    t_op: float

    sisai_oe: float
    sisai_ocb: float
    sisai_oc1: float
    sisai_oc2: float

    isc_b1cd: float
    tgd_b1cp: float
    tgd_b2ap: float

    sismai: float
    health: int
    b1c_integrity_flags: int
    iodc: int

    tx_time_tow: float
    iode: int

    def csv_fields(self) -> str:
        return f"{self.get_type().value},{_SAT_STR},{_EPOCH_STR},\
{_CLK_BIAS_STR},{_CLK_DRIFT_STR},{_CLK_DRIFT_RATE_STR},\
{_ADOT_STR},{_CRS_STR},{_DELTAN_STR},{_M0_STR},\
{_CUC_STR},{_E_STR},{_CUS_STR},{_SQRTA_STR},\
{_TOE_BDT_TOW_STR},{_CIC_STR},{_OMEGA0_STR},{_CIS_STR},\
{_I0_STR},{_CRC_STR},{_OMEGA_STR},{_OMEGA_DOT_STR},\
{_IDOT_STR},{_DELTAN_DOT_STR},{_SAT_TYPE_STR},{_T_OP_STR},\
{_SISAI_OE_STR},{_SISAI_OCB_STR},{_SISAI_OC1_STR},{_SISAI_OC2_STR},\
{_ISC_B1CD_STR},{_TGD_B1CP},{_TGD_B2AP},\
{_SISMAI_STR},{_HEALTH_STR},{_B1C_INTEGRITY_FLAGS_STR},{_IODC_STR},\
{_TX_TIME_TOW_STR},{_IODE_STR}"

    def get_type(self) -> EphType:
        return EphType.BDS_CNV1


@dataclass
class BdsCnv2NavBlock(NavBlock):
    """
    BEIDOU Navigation message on Beidou-3 B2a signal
    """
    clock_bias_s: float
    clock_drift_sps: float
    clock_drift_rate_sps2: float

    adot: float
    crs: float
    deltan: float
    M0: float

    cuc: float
    e: float
    cus: float
    sqrtA: float

    toe_bdt_tow: int
    cic: float
    OMEGA0: float
    cis: float

    i0: float
    crc: float
    omega: float
    OMEGA_DOT: float

    idot: float
    deltan_dot: float
    sattype: int
    t_op: float

    sisai_oe: float
    sisai_ocb: float
    sisai_oc1: float
    sisai_oc2: float

    isc_b2ad: float
    tgd_b1cp: float
    tgd_b2ap: float

    sismai: float
    health: int
    b2a_integrity_flags: int
    iodc: int

    tx_time_tow: float
    iode: int

    def csv_fields(self) -> str:
        return f"{self.get_type().value},{_SAT_STR},{_EPOCH_STR},\
{_CLK_BIAS_STR},{_CLK_DRIFT_STR},{_CLK_DRIFT_RATE_STR},\
{_ADOT_STR},{_CRS_STR},{_DELTAN_STR},{_M0_STR},\
{_CUC_STR},{_E_STR},{_CUS_STR},{_SQRTA_STR},\
{_TOE_BDT_TOW_STR},{_CIC_STR},{_OMEGA0_STR},{_CIS_STR},\
{_I0_STR},{_CRC_STR},{_OMEGA_STR},{_OMEGA_DOT_STR},\
{_IDOT_STR},{_DELTAN_DOT_STR},{_SAT_TYPE_STR},{_T_OP_STR},\
{_SISAI_OE_STR},{_SISAI_OCB_STR},{_SISAI_OC1_STR},{_SISAI_OC2_STR},\
{_ISC_B2AD_STR},{_TGD_B1CP},{_TGD_B2AP},\
{_SISMAI_STR},{_HEALTH_STR},{_B2A_INTEGRITY_FLAGS_STR},{_IODC_STR},\
{_TX_TIME_TOW_STR},{_IODE_STR}"

    def get_type(self) -> EphType:
        return EphType.BDS_CNV2


@dataclass
class BdsCnv3NavBlock(NavBlock):
    """
    BEIDOU Navigation message on Beidou-3 B2b signal
    """
    clock_bias_s: float
    clock_drift_sps: float
    clock_drift_rate_sps2: float

    adot: float
    crs: float
    deltan: float
    M0: float

    cuc: float
    e: float
    cus: float
    sqrtA: float

    toe_bdt_tow: int
    cic: float
    OMEGA0: float
    cis: float

    i0: float
    crc: float
    omega: float
    OMEGA_DOT: float

    idot: float
    deltan_dot: float
    sattype: int
    t_op: float

    sisai_oe: float
    sisai_ocb: float
    sisai_oc1: float
    sisai_oc2: float

    sismai: float
    health: int
    b2b_integrity_flags: int
    tgd_b2bi: int

    tx_time_tow: float

    def csv_fields(self) -> str:
        return f"{self.get_type().value},{_SAT_STR},{_EPOCH_STR},\
{_CLK_BIAS_STR},{_CLK_DRIFT_STR},{_CLK_DRIFT_RATE_STR},\
{_ADOT_STR},{_CRS_STR},{_DELTAN_STR},{_M0_STR},\
{_CUC_STR},{_E_STR},{_CUS_STR},{_SQRTA_STR},\
{_TOE_BDT_TOW_STR},{_CIC_STR},{_OMEGA0_STR},{_CIS_STR},\
{_I0_STR},{_CRC_STR},{_OMEGA_STR},{_OMEGA_DOT_STR},\
{_IDOT_STR},{_DELTAN_DOT_STR},{_SAT_TYPE_STR},{_T_OP_STR},\
{_SISAI_OE_STR},{_SISAI_OCB_STR},{_SISAI_OC1_STR},{_SISAI_OC2_STR},\
{_SISMAI_STR},{_HEALTH_STR},{_B2B_INTEGRITY_FLAGS_STR},{_TGD_B2BI},\
{_TX_TIME_TOW_STR},{_IODE_STR}"

    def get_type(self) -> EphType:
        return EphType.BDS_CNV2


@dataclass
class RawNavBlock(object):
    satellite: Satellite
    epoch: datetime.datetime
    lines: List[str]

    def __repr__(self):
        return '\n'.join(self.lines)

    def __lt__(self, other):

        if self.epoch != other.epoch:
            return self.epoch < other.epoch

        elif self.satellite.constellation != other.satellite.constellation:
            return self.satellite.constellation < other.satellite.constellation

        return self.satellite.prn < other.satellite.prn

    def to_rinex2(self) -> str:

        out = ""

        id = self.satellite.prn
        if id > 99:
            raise ValueError('Cannot write a Rinex 2 nav block for satellite with id > 99')

        epoch_line = f'{id:2d}'
        clock_str = self.lines[1][23:]
        out = out + f'{epoch_line} {self.epoch.strftime("%y %m %d %H %M %S.0")}{clock_str}\n'
        for brdc_line in self.lines[2:]:
            out = out + f'{brdc_line[1:]}\n'
        # print extra lines
        out = out + '    0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00\n'
        out = out + f'{self.lines[4][1:23]} 0.000000000000e+00'

        return out

    def to_csv(self) -> str:
        pass

    def to_nav_block(self) -> NavBlock:
        """
        Convert to Navigation Block
        """

        # Get the type of EPH block
        eph_type = _get_eph_type_from_rinex4_nav_block_header(self.lines[0])
        if eph_type == EphType.GPS_LNAV:
            return self._to_GPS_LNAV()
        elif eph_type == EphType.GPS_CNAV:
            return self._to_GPS_CNAV()
        elif eph_type == EphType.GPS_CNV2:
            return self._to_GPS_CNV2()
        elif eph_type == EphType.GAL_FNAV or eph_type == EphType.GAL_INAV:
            return self._to_GAL()
        elif eph_type == EphType.BDS_D1 or eph_type == EphType.BDS_D2:
            return self._to_BDS_D(eph_type)
        elif eph_type == EphType.BDS_CNV1:
            return self._to_BDS_CNV1()
        elif eph_type == EphType.BDS_CNV2:
            return self._to_BDS_CNV2()
        elif eph_type == EphType.BDS_CNV3:
            return self._to_BDS_CNV3()

        raise ValueError(f'There is no NavBlock generator for [ {eph_type} ]')

    def _to_GPS_LNAV(self) -> GpsLnavNavBlock:

        sat_str, year, month, day, hour,  min, sec, clk_bias, clk_drift, clk_drift_rate = _parse_nav_epoch_line(self.lines[1])
        iode, crs, deltan, M0 = _parse_nav_orb_line(self.lines[2])
        cuc, e, cus, sqrtA = _parse_nav_orb_line(self.lines[3])
        toe_sow, cic, OMEGA0, cis = _parse_nav_orb_line(self.lines[4])
        i0, crc, omega, OMEGA_DOT = _parse_nav_orb_line(self.lines[5])
        idot, codesL2, toe_week, l2p_flag = _parse_nav_orb_line(self.lines[6])
        accuracy, health, tgd, iodc = _parse_nav_orb_line(self.lines[7])
        tx_time_tow, fit_interval, _, _ = _parse_nav_orb_line(self.lines[8])

        if fit_interval is None:
            fit_interval = 0

        return GpsLnavNavBlock(Satellite.from_string(sat_str),
                               datetime.datetime(year, month, day, hour, min, sec),
                               clk_bias, clk_drift, clk_drift_rate,
                               iode, crs, deltan, M0,
                               cuc, e, cus, sqrtA,
                               toe_sow, cic, OMEGA0, cis,
                               i0, crc, omega, OMEGA_DOT,
                               idot, int(codesL2), int(toe_week), int(l2p_flag),
                               accuracy, int(health), tgd, int(iodc),
                               tx_time_tow, int(fit_interval))

    def _to_GPS_CNAV(self) -> GpsCnavNavBlock:

        sat_str, year, month, day, hour,  min, sec, clk_bias, clk_drift, clk_drift_rate = _parse_nav_epoch_line(self.lines[1])
        adot, crs, deltan, M0 = _parse_nav_orb_line(self.lines[2])
        cuc, e, cus, sqrtA = _parse_nav_orb_line(self.lines[3])
        top, cic, OMEGA0, cis = _parse_nav_orb_line(self.lines[4])
        i0, crc, omega, OMEGA_DOT = _parse_nav_orb_line(self.lines[5])
        idot, deltan_dot, urai_ned0, urai_ned1 = _parse_nav_orb_line(self.lines[6])
        urai_ed, health, tgd, urai_ned = _parse_nav_orb_line(self.lines[7])
        isc_l1ca, isc_l2c, isc_l5i5, isc_l5q5 = _parse_nav_orb_line(self.lines[8])
        tx_time_tow, wn_op, _, _ = _parse_nav_orb_line(self.lines[9])

        return GpsCnavNavBlock(Satellite.from_string(sat_str),
                               datetime.datetime(year, month, day, hour, min, sec),
                               clk_bias, clk_drift, clk_drift_rate,
                               adot, crs, deltan, M0,
                               cuc, e, cus, sqrtA,
                               top, cic, OMEGA0, cis,
                               i0, crc, omega, OMEGA_DOT,
                               idot, deltan_dot, urai_ned0, urai_ned1,
                               urai_ed, health, tgd, urai_ned,
                               isc_l1ca, isc_l2c, isc_l5i5, isc_l5q5,
                               tx_time_tow, int(wn_op))

    def _to_GPS_CNV2(self) -> GpsCnv2NavBlock:

        sat_str, year, month, day, hour,  min, sec, clk_bias, clk_drift, clk_drift_rate = _parse_nav_epoch_line(self.lines[1])
        adot, crs, deltan, M0 = _parse_nav_orb_line(self.lines[2])
        cuc, e, cus, sqrtA = _parse_nav_orb_line(self.lines[3])
        top, cic, OMEGA0, cis = _parse_nav_orb_line(self.lines[4])
        i0, crc, omega, OMEGA_DOT = _parse_nav_orb_line(self.lines[5])
        idot, deltan_dot, urai_ned0, urai_ned1 = _parse_nav_orb_line(self.lines[6])
        urai_ed, health, tgd, urai_ned = _parse_nav_orb_line(self.lines[7])
        isc_l1ca, isc_l2c, isc_l5i5, isc_l5q5 = _parse_nav_orb_line(self.lines[8])
        isc_l1cd, isc_l1cp, _, _ = _parse_nav_orb_line(self.lines[9])
        tx_time_tow, wn_op, _, _ = _parse_nav_orb_line(self.lines[10])

        return GpsCnv2NavBlock(Satellite.from_string(sat_str),
                               datetime.datetime(year, month, day, hour, min, sec),
                               clk_bias, clk_drift, clk_drift_rate,
                               adot, crs, deltan, M0,
                               cuc, e, cus, sqrtA,
                               top, cic, OMEGA0, cis,
                               i0, crc, omega, OMEGA_DOT,
                               idot, deltan_dot, urai_ned0, urai_ned1,
                               urai_ed, health, tgd, urai_ned,
                               isc_l1ca, isc_l2c, isc_l5i5, isc_l5q5,
                               isc_l1cd, isc_l1cp,
                               tx_time_tow, int(wn_op))

    def _to_GAL(self) -> GalNavBlock:

        sat_str, year, month, day, hour,  min, sec, clk_bias, clk_drift, clk_drift_rate = _parse_nav_epoch_line(self.lines[1])
        iodnav, crs, deltan, M0 = _parse_nav_orb_line(self.lines[2])
        cuc, e, cus, sqrtA = _parse_nav_orb_line(self.lines[3])
        toe_tow, cic, OMEGA0, cis = _parse_nav_orb_line(self.lines[4])
        i0, crc, omega, OMEGA_DOT = _parse_nav_orb_line(self.lines[5])
        idot, datasources, toe_week, _ = _parse_nav_orb_line(self.lines[6])
        sisa, health, bgd_e5a, bgd_e5b = _parse_nav_orb_line(self.lines[7])
        tx_tm, _, _, _ = _parse_nav_orb_line(self.lines[8])

        return GalNavBlock(Satellite.from_string(sat_str),
                           datetime.datetime(year, month, day, hour, min, sec),
                           clk_bias, clk_drift, clk_drift_rate,
                           int(iodnav), crs, deltan, M0,
                           cuc, e, cus, sqrtA,
                           toe_tow, cic, OMEGA0, cis,
                           i0, crc, omega, OMEGA_DOT,
                           idot, int(datasources), int(toe_week),
                           sisa, health, bgd_e5a, bgd_e5b,
                           tx_tm)

    def _to_BDS_D(self, eph_type: EphType) -> BdsDNavBlock:

        sat_str, year, month, day, hour,  min, sec, clk_bias, clk_drift, clk_drift_rate = _parse_nav_epoch_line(self.lines[1])
        aode, crs, deltan, M0 = _parse_nav_orb_line(self.lines[2])
        cuc, e, cus, sqrtA = _parse_nav_orb_line(self.lines[3])
        toe_tow, cic, OMEGA0, cis = _parse_nav_orb_line(self.lines[4])
        i0, crc, omega, OMEGA_DOT = _parse_nav_orb_line(self.lines[5])
        idot, _, toe_week, _ = _parse_nav_orb_line(self.lines[6])
        accuracy, satH1, tgd1, tgd2 = _parse_nav_orb_line(self.lines[7])
        tx_tm, aodc, _, _ = _parse_nav_orb_line(self.lines[8])

        return BdsDNavBlock(Satellite.from_string(sat_str),
                            datetime.datetime(year, month, day, hour, min, sec),
                            clk_bias, clk_drift, clk_drift_rate,
                            int(aode), crs, deltan, M0,
                            cuc, e, cus, sqrtA,
                            toe_tow, cic, OMEGA0, cis,
                            i0, crc, omega, OMEGA_DOT,
                            idot, int(toe_week),
                            accuracy, int(satH1), tgd1, tgd2,
                            tx_tm, aodc, eph_type.value)

    def _to_BDS_CNV1(self) -> BdsCnv1NavBlock:

        sat_str, year, month, day, hour,  min, sec, clk_bias, clk_drift, clk_drift_rate = _parse_nav_epoch_line(self.lines[1])
        adot, crs, deltan, M0 = _parse_nav_orb_line(self.lines[2])
        cuc, e, cus, sqrtA = _parse_nav_orb_line(self.lines[3])
        toe_tow, cic, OMEGA0, cis = _parse_nav_orb_line(self.lines[4])
        i0, crc, omega, OMEGA_DOT = _parse_nav_orb_line(self.lines[5])
        idot, deltan_dot, sattype, t_op = _parse_nav_orb_line(self.lines[6])
        sisai_oe, sisai_ocb, sisai_oc1, sisai_oc2 = _parse_nav_orb_line(self.lines[7])
        isc_b1cd, _, tgd_b1cp, tgd_b2ap = _parse_nav_orb_line(self.lines[8])
        sismai, health, b1c_integrity_flags, iodc = _parse_nav_orb_line(self.lines[9])
        tx_time_tow, _, _, iode = _parse_nav_orb_line(self.lines[10])

        return BdsCnv1NavBlock(Satellite.from_string(sat_str),
                               datetime.datetime(year, month, day, hour, min, sec),
                               clk_bias, clk_drift, clk_drift_rate,
                               adot, crs, deltan, M0,
                               cuc, e, cus, sqrtA,
                               toe_tow, cic, OMEGA0, cis,
                               i0, crc, omega, OMEGA_DOT,
                               idot, deltan_dot, int(sattype), t_op,
                               sisai_oe, sisai_ocb, sisai_oc1, sisai_oc2,
                               isc_b1cd, tgd_b1cp, tgd_b2ap,
                               sismai, int(health), int(b1c_integrity_flags), int(iodc),
                               tx_time_tow, int(iode))

    def _to_BDS_CNV2(self) -> BdsCnv2NavBlock:

        sat_str, year, month, day, hour,  min, sec, clk_bias, clk_drift, clk_drift_rate = _parse_nav_epoch_line(self.lines[1])
        adot, crs, deltan, M0 = _parse_nav_orb_line(self.lines[2])
        cuc, e, cus, sqrtA = _parse_nav_orb_line(self.lines[3])
        toe_tow, cic, OMEGA0, cis = _parse_nav_orb_line(self.lines[4])
        i0, crc, omega, OMEGA_DOT = _parse_nav_orb_line(self.lines[5])
        idot, deltan_dot, sattype, t_op = _parse_nav_orb_line(self.lines[6])
        sisai_oe, sisai_ocb, sisai_oc1, sisai_oc2 = _parse_nav_orb_line(self.lines[7])
        isc_b2ad, _, tgd_b1cp, tgd_b2ap = _parse_nav_orb_line(self.lines[8])
        sismai, health, b2a_integrity_flags, iodc = _parse_nav_orb_line(self.lines[9])
        tx_time_tow, _, _, iode = _parse_nav_orb_line(self.lines[10])

        return BdsCnv2NavBlock(Satellite.from_string(sat_str),
                               datetime.datetime(year, month, day, hour, min, sec),
                               clk_bias, clk_drift, clk_drift_rate,
                               adot, crs, deltan, M0,
                               cuc, e, cus, sqrtA,
                               toe_tow, cic, OMEGA0, cis,
                               i0, crc, omega, OMEGA_DOT,
                               idot, deltan_dot, int(sattype), t_op,
                               sisai_oe, sisai_ocb, sisai_oc1, sisai_oc2,
                               isc_b2ad, tgd_b1cp, tgd_b2ap,
                               sismai, int(health), int(b2a_integrity_flags), int(iodc),
                               tx_time_tow, int(iode))

    def _to_BDS_CNV3(self) -> BdsCnv3NavBlock:

        sat_str, year, month, day, hour,  min, sec, clk_bias, clk_drift, clk_drift_rate = _parse_nav_epoch_line(self.lines[1])
        adot, crs, deltan, M0 = _parse_nav_orb_line(self.lines[2])
        cuc, e, cus, sqrtA = _parse_nav_orb_line(self.lines[3])
        toe_tow, cic, OMEGA0, cis = _parse_nav_orb_line(self.lines[4])
        i0, crc, omega, OMEGA_DOT = _parse_nav_orb_line(self.lines[5])
        idot, deltan_dot, sattype, t_op = _parse_nav_orb_line(self.lines[6])
        sisai_oe, sisai_ocb, sisai_oc1, sisai_oc2 = _parse_nav_orb_line(self.lines[7])
        sismai, health, b2b_integrity_flags, tgd_b2ap = _parse_nav_orb_line(self.lines[8])
        tx_time_tow, _, _, iode = _parse_nav_orb_line(self.lines[9])

        return BdsCnv3NavBlock(Satellite.from_string(sat_str),
                               datetime.datetime(year, month, day, hour, min, sec),
                               clk_bias, clk_drift, clk_drift_rate,
                               adot, crs, deltan, M0,
                               cuc, e, cus, sqrtA,
                               toe_tow, cic, OMEGA0, cis,
                               i0, crc, omega, OMEGA_DOT,
                               idot, deltan_dot, int(sattype), t_op,
                               sisai_oe, sisai_ocb, sisai_oc1, sisai_oc2,
                               sismai, int(health), int(b2b_integrity_flags), tgd_b2ap,
                               tx_time_tow)


class Nav(object):
    """
    Class that holds Rinex Navigation data
    """

    RINEX4_EPH_BLOCK_LINES_LEO = 8

    RINEX4_EPH_BLOCK_LINES = {
        EphType.GPS_LNAV: 8,
        EphType.GPS_CNAV: 9,
        EphType.GPS_CNV2: 10,
        EphType.GAL_INAV: 8,
        EphType.GAL_FNAV: 8,
        EphType.GLO_FDMA: 5,
        EphType.QZS_LNAV: 8,
        EphType.QZS_CNAV: 9,
        EphType.QZS_CNV2: 10,
        EphType.BDS_D1: 8,
        EphType.BDS_D2: 8,
        EphType.BDS_CNV1: 10,
        EphType.BDS_CNV2: 10,
        EphType.BDS_CNV3: 9,
        EphType.SBS: 4,
        EphType.IRN_LNAV: 8,
        EphType.LEO: RINEX4_EPH_BLOCK_LINES_LEO,
        EphType.SPIRE: RINEX4_EPH_BLOCK_LINES_LEO,
        EphType.STARLINK: RINEX4_EPH_BLOCK_LINES_LEO,
        EphType.ONEWEB: RINEX4_EPH_BLOCK_LINES_LEO,
    }

    def __init__(self, file: Union[str, IO]):
        self.blocks = Nav._load(file)

    @staticmethod
    def _get_eph_block_lines(eph_type: EphType, satellite: Satellite) -> int:
        """
        Number of lines (excluding the header) of the ephemeris block. Any LEO
        constellation of the RINEX-LEO extension uses the LEO block layout

        >>> Nav._get_eph_block_lines(EphType.GPS_LNAV, Satellite.from_string('G01'))
        8
        >>> Nav._get_eph_block_lines(EphType.GLOBALSTAR, Satellite.from_string('A037741'))
        8
        """

        n_lines = Nav.RINEX4_EPH_BLOCK_LINES.get(eph_type)
        if n_lines is None and satellite.constellation.is_leo():
            n_lines = Nav.RINEX4_EPH_BLOCK_LINES_LEO
        if n_lines is None:
            raise ValueError(f'Unsupported ephemeris type [ {eph_type} ]')

        return n_lines

    @staticmethod
    @process_filename_or_file_handler('r')
    def _load(fh: IO) -> List['Nav']:
        """
        Load from a stream of data
        """

        blocks = []

        # header
        line = fh.readline()

        if not line.startswith('     4'):
            raise ValueError(f'Unsupported RINEX Nav version [ {line[5:6]} ] ')

        # body
        while True:
            line = fh.readline().rstrip()
            if line is None or len(line) == 0:
                break

            if line.startswith('> EOP'):
                skip_lines(fh, 3)
                continue

            elif line.startswith('> STO'):
                skip_lines(fh, 2)
                continue

            elif line.startswith('> ION') and line.endswith('> LNAV'):
                skip_lines(fh, 3)
                continue

            elif line.startswith('> ION') and line.endswith('> D1D2'):
                skip_lines(fh, 3)
                continue

            elif line.startswith('> ION') and line.endswith('> CNVX'):
                skip_lines(fh, 3)
                continue

            elif line.startswith('> ION') and line.endswith('> IFNV'):
                skip_lines(fh, 2)
                continue

            if not line.startswith('> EPH'):
                continue

            fields = line.split()
            sat = fields[2]
            satellite = Satellite.from_string(sat)  # satellite from eph

            eph_type = _get_eph_type_from_rinex4_nav_block_header(line)
            n_lines = Nav._get_eph_block_lines(eph_type, satellite)

            lines = [fh.readline().rstrip() for _ in range(n_lines)]

            epoch_line = lines[0]
            epoch = datetime.datetime.strptime(epoch_line[4:23], "%Y %m %d %H %M %S")

            block_lines = [line] + lines
            block = RawNavBlock(satellite, epoch, block_lines)

            blocks.append(block)

        return blocks

    def get(satellite: Satellite):
        pass

    def to_blocks(self) -> Dict[EphType, List[NavBlock]]:

        out = {}

        for block in self.blocks:

            try:
                nav_block = block.to_nav_block()
            except ValueError:
                pass

            eph_type = nav_block.get_type()

            if eph_type not in out:
                out[eph_type] = []

            out[eph_type].append(nav_block)

        return out

    def to_dataframes(self) -> Dict[EphType, pd.DataFrame]:

        blocks = self.to_blocks()

        dfs = {}

        for eph_type, nav_blocks in blocks.items():
            data = [block.to_dict() for block in nav_blocks]
            dfs[eph_type] = pd.DataFrame(data)

        return dfs

    def __len__(self):
        """
        Number of blocks of the Rinex Nav file
        """
        return len(self.blocks)

    def __iter__(self):
        """
        Iterator for the Rinex blocks, to be used in for loops
        """
        return iter(self.blocks)

    def __lt__(self, other):
        return self.blocks < other.blocks

    @staticmethod
    def create_header(pgm: str = "pygnss") -> str:
        """
        Create a basic RINEX 4.99 header

        Subversion 99 stands for Rokubun implementation of Rinex 4 standard
        that supports LEO navigation blocks
        """

        epoch_str = datetime.datetime.now(datetime.UTC).strftime('%Y%m%d %H%M%S UTC ')

        out = "     4.99           NAVIGATION DATA     M                   RINEX VERSION / TYPE\n"
        out = out + f"{pgm.ljust(20)}rokubun             {epoch_str}PGM / RUN BY / DATE\n"
        out = out + "    18                                                      LEAP SECONDS\n"
        out = out + "                                                            END OF HEADER\n"
        return out

    @staticmethod
    def create_navblock(satellite: Satellite, orbit: Kepler, sat_clock: Clock, code_biases: CodeBiases) -> RawNavBlock:

        if satellite.constellation.is_leo():
            return Nav.create_leo_navblock(satellite, orbit, sat_clock, code_biases)

    @staticmethod
    def create_leo_navblock(satellite: Satellite, orbit: Kepler, sat_clock: Clock, biases: CodeBiases) -> RawNavBlock:
        """
        Output a RINEX4 navigation block from a set of orbit and clock parameters
        """

        lines = []

        # Header line
        lines.append(
            f'> EPH {satellite.constellation.to_char()}{satellite.prn:0{LEO_SATELLITE_ID_DIGITS}d}')

        # EPOCH - CLK epoch
        lines.append(orbit.toe.strftime('    %Y %m %d %H %M %S') +
                     f'{sat_clock.bias_s:19.12e}{sat_clock.drift_s_per_s:19.12e}{sat_clock.drift_rate_s_per_s2:19.12e}')

        # ORBIT 1
        adot = 0.0
        crs = 0.0
        delta_n0 = 0.0
        M0 = orbit.true_anomaly_rad
        lines.append(Nav._write_orbit_line(adot, crs, delta_n0, M0))

        # ORBIT 2
        cuc = 0.0
        e = orbit.eccentricity
        cus = 0.0
        sqrta = math.sqrt(orbit.a_m)
        lines.append(Nav._write_orbit_line(cuc, e, cus, sqrta))

        # ORBIT - 3
        weektow = time.to_week_tow(orbit.toe)
        void = 0
        cic = 0.0
        # The RAAN parameter of GPS orbits are referred to the start of the GPS week, not the epoch
        # epoch of the ephemeris. Therfore, we need to compensate it
        t_start_of_week = time.from_week_tow(weektow.week, 0.0)
        greenwich_raan_rad = compute_greenwich_ascending_node_rad(t_start_of_week)
        OMEGA0 = orbit.raan_rad - greenwich_raan_rad
        OMEGA0 = math.fmod(OMEGA0 + math.tau, math.tau)

        cis = 0.0
        lines.append(Nav._write_orbit_line(weektow.tow, cic, OMEGA0, cis))

        # ORBIT - 4
        i0 = orbit.inclination_rad
        crc = 0.0
        omega = orbit.arg_perigee_rad
        OMEGA_DOT = 0.0
        lines.append(Nav._write_orbit_line(i0, crc, omega, OMEGA_DOT))

        # ORBIT - 5
        void = 0.0
        idot = 0.0
        delta_n_dot = orbit.delta_n_dot_rad_per_s
        lines.append(Nav._write_orbit_line(idot, delta_n_dot, weektow.week, void))

        # ORBIT - 6
        lines.append(Nav._write_orbit_line(void, void, biases.get_base_tgd(), void))

        # ORBIT - 7
        channel = TrackingChannel.from_string('9C')  # May depend on the LEO constellation
        lines.append(Nav._write_orbit_line(biases.get_code_bias(channel), void, void, void))

        return RawNavBlock(satellite, orbit.toe, lines)

    @staticmethod
    @process_filename_or_file_handler('w')
    def write_from_tle(output, tle_list: List[TLE], rinex2=False, sat_clock_model=ZeroClockModel(), code_biases=ZeroCodeBiases()) -> None:

        output.write(Nav.create_header(pgm='rinex_from_file'))

        for tle in tle_list:

            try:
                satellite = tle.get_satellite()
                orbit = tle.to_kepler()
                sat_clock = sat_clock_model.get_clock(satellite, tle.toe)
                nav_block = Nav.create_navblock(satellite, orbit, sat_clock, code_biases)

                output.write(nav_block.to_rinex2() if rinex2 else str(nav_block))
                output.write('\n')
            except ValueError as e:
                logger.warning(e)
                continue

    @staticmethod
    @process_filename_or_file_handler('w')
    def write_from_dataframe(output, df: pd.DataFrame, rinex2=False, sat_clock_model=ZeroClockModel(), clock_biases=ZeroCodeBiases()) -> None:
        f"""
        Write a RINEX file from the orbital parameters contained in a DataFrame,
        which should have the following fields
        - {EPOCH_STR}, with the reference epoch (will be parsed to a datetime)
        - {SAT_STR}, with the satellite identifier
        - {A_M_STR}, with the semimajor axis
        - {ECCENTRICITY_STR} Eccentricity of the orbit (adimensional)
        - {INCLINATION_DEG_STR} Inclination of the orbit (degrees)
        - {RIGHT_ASCENSION_DEG_STR} Right ascension of the ascending node (degrees)
        - {ARG_PERIGEE_DEG_STR} Argument of the perigee (degrees)
        - {TRUE_ANOMALY_DEG_STR} True anomaly (degrees)

        """

        output.write(Nav.create_header(pgm='rinex_from_file'))

        df = df.sort_values(by=['epoch', 'sat'], ascending=[True, True])

        for _, row in df.iterrows():

            try:
                constellation = ConstellationId.from_string(row.sat[0])
                prn = int(row.sat[1:])
                satellite = Satellite(constellation=constellation, prn=prn)
                sat_clock = sat_clock_model.get_clock(satellite, row.epoch)
                orbit = Kepler(
                    row.epoch, row.a_m, row.eccentricity,
                    math.radians(row.inclination_deg), math.radians(row.raan_deg),
                    math.radians(row.arg_perigee_deg), math.radians(row.true_anomaly_deg))
                nav_block = Nav.create_navblock(satellite, orbit, sat_clock, clock_biases)

                output.write(nav_block.to_rinex2() if rinex2 else str(nav_block))
                output.write('\n')
            except Exception as e:
                logger.warning(e)
                continue

    def write(self, output_filename, rinex2=False) -> None:

        with open(output_filename, 'w') as fh:

            fh.write(Nav.create_header(pgm='rinex_from_file'))

            for block in self.blocks:
                try:
                    fh.write(block.to_rinex2() if rinex2 else str(block))
                    fh.write('\n')
                except Exception as e:
                    logger.warning(e)
                    continue

#    def to_csv(self, csv_filename:str) -> None:
#
#        with open(csv_filename, "w") as fh:
#
#            for block in self.blocks:
#                pass

    @staticmethod
    def _write_orbit_line(a: float, b: float, c: float, d: float) -> str:
        return f'    {a:19.12e}{b:19.12e}{c:19.12e}{d:19.12e}'


def compute_greenwich_ascending_node_rad(epoch_utc: datetime.datetime) -> float:
    """
    Compute the Ascending Node of the Greenwich meridian at the given UTC epoch

    >>> round(compute_greenwich_ascending_node_rad(datetime.datetime(2024, 2, 11)), 9)
    2.453307616
    """

    gmst_h = time.gmst(epoch_utc)

    gmst_rad = gmst_h * math.tau / 24.0
    gmst_rad = gmst_rad % math.tau

    return gmst_rad


def merge_nav(files: List[Union[str, IO]]) -> str:
    """
    Merge RINEX navigation files

    :param files: list of RINEX Nav files to merge

    :return: the merged RINEX NAV file as a string
    """

    # Read navigation blocks and place them into memory
    rinex_navs = [Nav(file) for file in files]

    sorted_blocks = sorted([block for rinex_nav in rinex_navs for block in rinex_nav])

    # Proceed to output all of them
    out = Nav.create_header(pgm="merge_rinex_nav")

    out += '\n'.join([str(block) for block in sorted_blocks])

    return out


_ACCURACY_STR = "accuracy"
_ADOT_STR = "Adot[m/s]"
_AODC_STR = "aodc"
_AODE_STR = "aode"
_B1C_INTEGRITY_FLAGS_STR = "b1c_integrity_flags"
_B2A_INTEGRITY_FLAGS_STR = "b2a_integrity_flags"
_B2B_INTEGRITY_FLAGS_STR = "b2b_integrity_flags"
_BGD_E5A_STR = "bgd_e5a_e1[s]"
_BGD_E5B_STR = "bgd_e5b_e1[s]"
_CIC_STR = "cic[rad]"
_CIS_STR = "cis[rad]"
_CLK_BIAS_STR = "clock_bias[s]"
_CLK_DRIFT_RATE_STR = "clock_drift_rate[s/s2]"
_CLK_DRIFT_STR = "clock_drift[s/s]"
_CODESL2_STR = "codesL2"
_CRC_STR = "crc[m]"
_CRS_STR = "crs[m]"
_CUC_STR = "cuc[rad]"
_CUS_STR = "cus[rad]"
_DATA_SOURCES_STR = "datasources"
_DELTAN_DOT_STR = "deltan_dot[r/s^2]"
_DELTAN_STR = "deltan[rad/s]"
_EPOCH_STR = "epoch"
_E_STR = "e"
_FIT_INTERVAL_STR = "fit_interval"
_HEALTH_STR = "health"
_I0_STR = "i0[rad]"
_IDOT_STR = "idot[rad/s]"
_IODC_STR = "iodc"
_IODE_STR = "iode"
_IODNAV_STR = "iodnav"
_ISC_B2AD_STR = "isc_b2ad[s]"
_ISC_B1CD_STR = "isc_b1cd[s]"
_ISC_L1CA_STR = "isc_L1CA[s]"
_ISC_L1CD_STR = "isc_L1CD[s]"
_ISC_L1CP_STR = "isc_L1CP[s]"
_ISC_L2C_STR = "isc_L2C[s]"
_ISC_L5I5_STR = "isc_L5I5[s]"
_ISC_L5Q5_STR = "isc_L5Q5[s]"
_L2PFLAG_STR = "l2p_flag"
_M0_STR = "M0[rad]"
_OMEGA0_STR = "OMEGA0[rad]"
_OMEGA_DOT_STR = "OMEGA_DOT[rad/s]"
_OMEGA_STR = "omega[rad]"
_SATH1_STR = "sat_H1"
_SAT_STR = "sat"
_SAT_TYPE_STR = "sat_type"
_SISAI_OC1_STR = "SISAI_oc1"
_SISAI_OC2_STR = "SISAI_oc2"
_SISAI_OCB_STR = "SISAI_ocb"
_SISAI_OE_STR = "SISAI_oe"
_SISA_STR = "sisa[m]"
_SISMAI_STR = "SISMAI"
_SQRTA_STR = "sqrtA[sqrt(m)]"
_TGD1_STR = "tgd1[s]"
_TGD2_STR = "tgd2[s]"
_TGD_B1CP = "tgd_b1cp[s]"
_TGD_B2AP = "tgd_b2ap[s]"
_TGD_B2BI = "tgd_b2bi[s]"
_TGD_STR = "tgd[s]"
_TOE_BDT_TOW_STR = "toe_bdt_tow[s]"
_TOE_BDT_WEEK_STR = "toe_bdt_week[week]"
_TOE_GAL_TOW_STR = "toe_gal_tow[s]"
_TOE_GAL_WEEK_STR = "toe_gal_week[week]"
_TOE_SOW_STR = "toe[s]"
_TOE_WEEK_STR = "toe[week]"
_TX_TIME_TOW_STR = "tx_time[s]"
_T_OP_STR = "t_op[s]"
_URAI_ED_STR = "urai_ed"
_URAI_NED0_STR = "urai_ned0"
_URAI_NED1_STR = "urai_ned1"
_URAI_NED2_STR = "urai_ned2"
_WN_OP_STR = "wn_op[week]"


def _parse_nav_epoch_line(line: str) -> tuple:
    """
    Parse a Rinex 4 Navigation line

    >>> _parse_nav_epoch_line("G01 2024 02 13 11 22 33 1.693181693554e-04 1.477928890381e-12 1.000000000000e+00")
    ('G01', 2024, 2, 13, 11, 22, 33, 0.0001693181693554, 1.477928890381e-12, 1.0)
    """

    return line[0:3], \
        int(line[4:8]), int(line[9:11]), int(line[12:14]),  \
        int(line[15:17]),  int(line[17:20]),  int(line[20:23]), \
        float(line[23:42]), float(line[42:61]), float(line[61:])


def _parse_nav_orb_line(line: str) -> tuple:
    """
    Parse a Rinex 4 Navigation line (broadcast orbit line)


    >>> _parse_nav_orb_line('     1.700595021248e-06')
    (1.700595021248e-06, None, None, None)

    >>> _parse_nav_orb_line('     1.700595021248e-06 1.270996686071e-02')
    (1.700595021248e-06, 0.01270996686071, None, None)

    >>> _parse_nav_orb_line('     1.700595021248e-06 1.270996686071e-02 1.259148120880e-05')
    (1.700595021248e-06, 0.01270996686071, 1.25914812088e-05, None)

    >>> _parse_nav_orb_line('     1.700595021248e-06 1.270996686071e-02 1.259148120880e-05 5.154011671066e+03')
    (1.700595021248e-06, 0.01270996686071, 1.25914812088e-05, 5154.011671066)
    """

    try:
        v1 = float(line[4:23])
    except ValueError:
        v1 = None

    try:
        v2 = float(line[23:42])
    except ValueError:
        v2 = None

    try:
        v3 = float(line[42:61])
    except ValueError:
        v3 = None

    try:
        v4 = float(line[61:])
    except ValueError:
        v4 = None

    return v1, v2, v3, v4


def _get_eph_type_from_rinex4_nav_block_header(block_header: str) -> EphType:
    """
    Get the type of ephemeris based on the header line of the Rinex 4 navigation block

    >>> _get_eph_type_from_rinex4_nav_block_header('> EPH G01 LNAV')
    <EphType.GPS_LNAV: 'G_LNAV'>

    >>> _get_eph_type_from_rinex4_nav_block_header('> EPH X002434')
    <EphType.STARLINK: 'X'>
    """

    fields = block_header.split()

    sat = Satellite.from_string(fields[2])

    sat.constellation.value
    key = sat.constellation.value
    if len(fields) == 4:
        key = f'{key}_{fields[-1]}'

    return EphType.from_string(key)
