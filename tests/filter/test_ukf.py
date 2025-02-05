import doctest

from pygnss.filter import ukf


def test_doctest():
    """Number of failed doctests should be 0"""

    fails, tests = doctest.testmod(ukf)
    assert tests > 0
    assert fails == 0
