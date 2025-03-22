import datetime
import tempfile

import nequick

import pygnss.nequick


def test__to_ionex():

    coeffs = nequick.Coefficients(a0=169.00, a1=0.45312, a2=5.5847e-03)

    dates = [datetime.datetime(2025, 3, 18, 0, 0, 0)]

    with tempfile.NamedTemporaryFile(mode='wt') as fh:

        pygnss.nequick.to_ionex(fh.name, coeffs, dates)
        fh.flush()
        fh.seek(0)

        with open(fh.name, mode='rt') as finp:
            doc = finp.read()

    assert doc is not None

    assert '     1.0            IONOSPHERE MAPS     NEQUICK             IONEX VERSION / TYPE' in doc
    assert 'a0=169.000000       a1=0.45312000       a2=0.00558470000    COMMENT' in doc

    assert '  2025    03    18    00    00    00                        EPOCH OF FIRST MAP' in doc
    assert '  2025    03    18    00    00    00                        EPOCH OF CURRENT MAP' in doc

    # Check 3rd line after:
    assert '   -85.0-180.0 180.0   5.0 450.0                            LAT/LON1/LON2/DLON/H' in doc
    assert '  124  124  124  125  125  126  126  127  128  128  129  130  131  132  133  134' in doc
