import doctest


def test_doctest():
    """Number of failed doctests should be 0"""

    from pygnss import stats as m
    fails, tests = doctest.testmod(m)
    assert tests > 0
    assert fails == 0
