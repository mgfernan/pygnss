import doctest


def test_doctest():
    """sinex :: Number of failed doctests should be 0"""

    import pygnss.sinex as m
    fails, tests = doctest.testmod(m)
    assert tests > 0
    assert fails == 0
