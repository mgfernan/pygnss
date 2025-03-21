import datetime

import pytest
import numpy as np

from pygnss.iono import gim


def test__gim_compare():

    gim_a = gim.Gim(
        epoch=datetime.datetime(2025, 3, 21, 12, 0),
        longitudes=[0, 1, 2],
        latitudes=[0, 1],
        vtec_values=[[10, 20, 30], [40, 50, 60]]
    )


    gim_b = gim.Gim(
        epoch=datetime.datetime(2025, 3, 21, 12, 0),
        longitudes=[0, 1, 2],
        latitudes=[0, 1],
        vtec_values=[[5, 10, 15], [20, 25, 30]]
    )

    dvtec_ref = [[5, 10, 15], [20, 25, 30]]

    dgim = gim_a - gim_b

    assert np.array_equal(dgim.vtec_values, dvtec_ref)
    assert np.array_equal(gim.subtract(gim_a, gim_b).vtec_values, dvtec_ref)


def test__gim_mismatched_epochs():
    """
    Test subtraction of GIMs with mismatched epochs.
    """
    gim_a = gim.Gim(
        epoch=datetime.datetime(2025, 3, 21, 12, 0),
        longitudes=[0, 1, 2],
        latitudes=[0, 1],
        vtec_values=[[10, 20, 30], [40, 50, 60]]
    )

    gim_b = gim.Gim(
        epoch=datetime.datetime(2025, 3, 21, 13, 0),  # Different epoch
        longitudes=[0, 1, 2],
        latitudes=[0, 1],
        vtec_values=[[5, 10, 15], [20, 25, 30]]
    )

    with pytest.raises(ValueError, match="Epochs of both GIMs differ"):
        _ = gim_a - gim_b


def test__gim_mismatched_latitudes():
    """
    Test subtraction of GIMs with mismatched latitudes.
    """
    gim_a = gim.Gim(
        epoch=datetime.datetime(2025, 3, 21, 12, 0),
        longitudes=[0, 1, 2],
        latitudes=[0, 1],
        vtec_values=[[10, 20, 30], [40, 50, 60]]
    )

    gim_b = gim.Gim(
        epoch=datetime.datetime(2025, 3, 21, 12, 0),
        longitudes=[0, 1, 2],
        latitudes=[0, 2],  # Different latitudes
        vtec_values=[[5, 10, 15], [20, 25, 30]]
    )

    with pytest.raises(ValueError, match="Latitudes do not match between the two GIMs"):
        _ = gim_a - gim_b


def test__gim_mismatched_longitudes():
    """
    Test subtraction of GIMs with mismatched longitudes.
    """
    gim_a = gim.Gim(
        epoch=datetime.datetime(2025, 3, 21, 12, 0),
        longitudes=[0, 1, 2],
        latitudes=[0, 1],
        vtec_values=[[10, 20, 30], [40, 50, 60]]
    )

    gim_b = gim.Gim(
        epoch=datetime.datetime(2025, 3, 21, 12, 0),
        longitudes=[0, 1, 3],  # Different longitudes
        latitudes=[0, 1],
        vtec_values=[[5, 10, 15], [20, 25, 30]]
    )

    with pytest.raises(ValueError, match="Longitude do not match between the two GIMs"):
        _ = gim_a - gim_b
