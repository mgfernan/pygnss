import doctest
import pytest

import pygnss.geodetic as geodetic


def test_doctest():
    """Number of failed doctests should be 0"""

    import pygnss.geodetic as m
    fails, tests = doctest.testmod(m)
    assert tests > 0
    assert fails == 0


def test_geodetic_get_absolute_position():

    ref_position = geodetic.Coordinates.from_lla(2.0, 41.0, 0.0)

    enu = [0.1, 0.1, 0.0]

    displacement = geodetic.CoordinatesDisplacement(enu=enu, ref_position=ref_position)

    abs_pos = displacement.get_absolute_position()

    lla = abs_pos.lla()

    assert abs(lla.altitude) < 0.0001


def test_coordinates_are_equals():

    coordinates1 = geodetic.Coordinates(4097216.671, 4429119.006, -2065771.359)
    coordinates2 = geodetic.Coordinates(4097216.671, 4429119.006, -2065771.359)

    assert coordinates1 == coordinates2


def test_coordinates_are_not_equals():

    coordinates1 = geodetic.Coordinates(4097216.671, 4429119.006, -2065771.359)
    coordinates2 = geodetic.Coordinates(4097216.671, 4429119.006, -2065771.351)

    assert coordinates1 != coordinates2


def test_coordinates_are_not_same_instance():

    coordinates1 = geodetic.Coordinates(4097216.671, 4429119.006, -2065771.359)
    coordinates2 = [1, 2, 3]

    assert coordinates1 != coordinates2


def test_xyz_dunders():

    XYZ_REF = geodetic.XYZ(1.0, 2.0, 3.0)
    scale = 2.0

    # __mul__
    xyz_scaled = XYZ_REF * scale

    assert isinstance(xyz_scaled, geodetic.XYZ)
    assert xyz_scaled.x == pytest.approx(2.0)
    assert xyz_scaled.y == pytest.approx(4.0)
    assert xyz_scaled.z == pytest.approx(6.0)

    # __truediv__
    xyz = xyz_scaled / scale
    assert isinstance(xyz, geodetic.XYZ)
    assert xyz == pytest.approx(XYZ_REF)
