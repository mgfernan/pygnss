import doctest

from pygnss.filter import models


def test_doctest():
    """Number of failed doctests should be 0"""

    fails, tests = doctest.testmod(models)
    assert tests > 0
    assert fails == 0
