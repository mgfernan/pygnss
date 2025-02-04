import datetime
import math
import tempfile

import pytest

from pygnss.orbit.tle import TLE, read_celestrak


def test_write_tle_rinex():

    tle = TLE(
        "1 53722U 22107Y   23305.87948756  .00001394  00000+0  10567-3 0  9996",
        "2 53722  53.2145 149.3795 0001289  81.3713 278.7425 15.08842580 64750")

    assert tle.toe == pytest.approx(datetime.datetime(2023, 11, 1, 21, 6, 27, microsecond=725184))
    assert tle.inclination_rad == pytest.approx(math.radians(53.2145))
    assert tle.RAAN_rad == pytest.approx(math.radians(149.3795))
    assert tle.arg_perigee_rad == pytest.approx(math.radians(81.3713))


def test__read_celestrak():

    doc = """ONEWEB-0012
1 44057U 19010A   24048.46720274 -.00000208  00000+0 -57902-3 0  9998
2 44057  87.9056  38.1049 0002697  78.3061 281.8373 13.16593911239624
ONEWEB-0010
1 44058U 19010B   24048.56855024  .00000095  00000+0  21501-3 0  9990
2 44058  87.9061  38.0627 0001996  67.4050 292.7292 13.16593857239686
ONEWEB-0008
1 44059U 19010C   24048.51787914  .00000040  00000+0  69755-4 0  9992
2 44059  87.9061  38.0745 0001821  94.6884 265.4455 13.16596956239795"""

    with tempfile.NamedTemporaryFile() as fh:

        fh.write(doc.encode('utf-8'))

        # rewind the file-handler
        fh.seek(0)

        tles = read_celestrak(fh.name)

    assert len(tles) == 3
    assert tles[0].id == 44057
    assert tles[1].id == 44058
    assert tles[2].id == 44059
