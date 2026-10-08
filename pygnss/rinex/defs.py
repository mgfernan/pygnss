
from ..gnss.types import ConstellationId, Band

RINEX_LINE_SYS_OBS_TYPES = "SYS / # / OBS TYPES"

RANDOM_STR = 'random'
ZERO_STR = 'zero'

SAT_STR = 'sat'
EPOCH_STR = 'epoch'
A_M_STR = 'a_m'
ECCENTRICITY_STR = 'eccentricity'
INCLINATION_DEG_STR = 'inclination_deg'
RIGHT_ASCENSION_DEG_STR = 'raan_deg'
ARG_PERIGEE_DEG_STR = 'arg_perigee_deg'
TRUE_ANOMALY_DEG_STR = 'true_anomaly_deg'

RINEX_BAND_MAP = {
    ConstellationId.GPS: {
        '1': Band.L1,
        '2': Band.L2,
        '5': Band.L5
    },
    ConstellationId.GLONASS: {
        '1': Band.G1,
        '4': Band.G1a,
        '2': Band.G2,
        '6': Band.G2a,
        '3': Band.G3
    },
    ConstellationId.GALILEO: {
        '1': Band.E1,
        '5': Band.E5a,
        '7': Band.E5b,
        '8': Band.E5,
        '6': Band.E6
    },
    ConstellationId.BEIDOU: {
        '2': Band.B1_2,
        '1': Band.B1,
        '5': Band.B2a,
        '7': Band.B2b,
        '8': Band.B2,
        '6': Band.B3
    },
    ConstellationId.QZSS: {
        '1': Band.L1,
        '2': Band.L2,
        '5': Band.L5,
        '6': Band.L6
    },
    ConstellationId.IRNSS: {
        '5': Band.L5,
        '9': Band.S
    },
    ConstellationId.SBAS: {
        '1': Band.L1,
        '5': Band.L5
    }
}
