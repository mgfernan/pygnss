import doctest


def test_doctest():
    """Rinex :: Number of failed doctests should be 0"""

    import pygnss.gnss.types as m
    fails, tests = doctest.testmod(m)
    assert tests > 0
    assert fails == 0


def test_satellite_id_roundtrip():
    """Satellite :: MEO ids use 2 digits and LEO ids 6 digits"""

    from pygnss.gnss.types import Satellite

    for text in ['G07', 'E36', 'X002434', 'V010000', 'Z043012', 'X100972']:
        assert str(Satellite.from_string(text)) == text

    assert Satellite.from_string('X002434').prn == 2434
    assert Satellite.from_string('X100972').prn == 100972
