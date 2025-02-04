import doctest
from datetime import datetime, timedelta
from pygnss.time import Timespan
import pytest


def test_doctest():
    """Number of failed doctests should be 0"""

    import pygnss.time as m
    fails, tests = doctest.testmod(m)
    assert tests > 0
    assert fails == 0


@pytest.fixture()
def timespan1():
    start = datetime(2022, 1, 1, 12, 0, 0)
    end = datetime(2022, 1, 2, 12, 0, 0)
    return Timespan(start, end)


def test_is_overlaping(timespan1):
    # Test case where other timespan starts before this one ends
    start = datetime(2022, 1, 1, 0, 0, 0)
    end = datetime(2022, 1, 1, 12, 0, 0)
    timespan2 = Timespan(start, end)
    assert timespan1.is_overlaping(timespan2) is True

    # Test case where other timespan ends after this one starts
    start = datetime(2022, 1, 2, 0, 0, 0)
    end = datetime(2022, 1, 3, 0, 0, 0)
    timespan2 = Timespan(start, end)
    assert timespan1.is_overlaping(timespan2) is True

    # Test case where other timespan starts and ends inside this one
    start = datetime(2022, 1, 1, 12, 30, 0)
    end = datetime(2022, 1, 2, 11, 30, 0)
    timespan2 = Timespan(start, end)
    assert timespan1.is_overlaping(timespan2) is True

    # Test case where other timespan starts and ends outside this one
    start = datetime(2021, 12, 31, 12, 0, 0)
    end = datetime(2022, 1, 3, 12, 0, 0)
    timespan2 = Timespan(start, end)
    assert timespan1.is_overlaping(timespan2) is True

    # Test case where other timespan starts and ends before this one
    start = datetime(2021, 12, 31, 12, 0, 0)
    end = datetime(2022, 1, 1, 11, 59, 59)
    timespan2 = Timespan(start, end)
    assert timespan1.is_overlaping(timespan2) is False


def test_duration(timespan1):
    assert timespan1.duration() == timedelta(hours=24)
    assert timespan1.duration_seconds() == 24 * 60 * 60
    assert timespan1.duration_minutes() == 24 * 60
    assert timespan1.duration_hours() == 24
    assert timespan1.duration_days() == 1


def test_get_is_overlap_time_spaning():
    # Test is_overlappinging time spans
    time1 = Timespan(datetime(2022, 1, 1, 12, 0, 0), datetime(2022, 1, 1, 14, 0, 0))
    time2 = Timespan(datetime(2022, 1, 1, 13, 0, 0), datetime(2022, 1, 1, 15, 0, 0))
    is_overlaping = time1.overlap(time2)
    assert is_overlaping.start == datetime(2022, 1, 1, 13, 0, 0)
    assert is_overlaping.end == datetime(2022, 1, 1, 14, 0, 0)

    # Test non-is_overlappinging time spans
    time1 = Timespan(datetime(2022, 1, 1, 12, 0, 0), datetime(2022, 1, 1, 14, 0, 0))
    time2 = Timespan(datetime(2022, 1, 1, 14, 0, 1), datetime(2022, 1, 1, 15, 0, 0))
    with pytest.raises(ValueError) as _:
        is_overlaping = time1.overlap(time2)

    # Test time spans where one completely is_overlapsing the other
    time1 = Timespan(datetime(2022, 1, 1, 12, 0, 0), datetime(2022, 1, 1, 14, 0, 0))
    time2 = Timespan(datetime(2022, 1, 1, 11, 0, 0), datetime(2022, 1, 1, 15, 0, 0))
    is_overlaping = time1.overlap(time2)
    assert is_overlaping.start == time1.start
    assert is_overlaping.end == time1.end
