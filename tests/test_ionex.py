import os
import subprocess
import tempfile
from typing import List

import numpy as np
import pytest

from pygnss import ionex
from pygnss.iono import gim

DATA_FOLDER = os.path.join(os.path.dirname(__file__), "./data")
SAMPLE_IONEX =  os.path.join(DATA_FOLDER, "sample.ionex")

@pytest.mark.parametrize('ionex_file, n_vtec_maps, n_rms_maps', [
    pytest.param('COD0OPSRAP_20250790000_01D_01H_GIM.INX.gz', 25, 25),
    pytest.param('uprg0790.25i.Z', 13, 13),
])
def test__load_ionex_file(ionex_file: str, n_vtec_maps: int, n_rms_maps: int):

    gim_handler = gim.GimHandlerArray()

    ionex.load(os.path.join(DATA_FOLDER, ionex_file),
               gim_handler=gim_handler)

    assert len(gim_handler.vtec_gims) == n_vtec_maps
    assert len(gim_handler.rms_gims) == n_rms_maps


def test__compare():

    ionex_a = os.path.join(DATA_FOLDER, 'COD0OPSRAP_20250790000_01D_01H_GIM.INX.gz')
    ionex_b = os.path.join(DATA_FOLDER, 'uprg0790.25i.Z')

    with tempfile.NamedTemporaryFile(mode='wt') as fh:

        ionex.diff(ionex_a, ionex_b, fh.name)

        fh.flush()
        fh.seek(0)

        # Read the resulting file and make some checks
        with open(fh.name, mode='rt') as finp:

            gim_handler = gim.GimHandlerArray()
            ionex.load(fh.name, gim_handler=gim_handler)

            gims = gim_handler.vtec_gims

            assert len(gims) == 13

            assert gims[0].vtec_values[0][0] == pytest.approx(10.8)
            assert gims[-1].vtec_values[-1][-1] == pytest.approx(-10.2)

            finp.seek(0)

            doc = finp.read()

            assert '    87.5-180.0 180.0   5.0 450.0                            LAT/LON1/LON2/DLON/H\n'
            '  108  107  108  106  106  101  100  100   99   98   93   89   83   82   75   72' in doc
            assert '  -66  -70  -73  -77  -79  -89  -95  -99 -102\n'
            '    12                                                      END OF TEC MAP' in doc


def test__compare_all_zeroes():

    with tempfile.NamedTemporaryFile(mode='wt') as fh:

        ionex.diff(SAMPLE_IONEX, SAMPLE_IONEX, fh.name)

        fh.flush()
        fh.seek(0)

        # Read the resulting file and make some checks
        with open(fh.name, mode='rt') as finp:

            gim_handler = gim.GimHandlerArray()
            ionex.load(fh.name, gim_handler=gim_handler)

            gims = gim_handler.vtec_gims

            assert len(gims) == 1

            zeros = np.zeros_like(gims[0].vtec_values)
            assert np.array_equal(gims[0].vtec_values, zeros)


@pytest.mark.parametrize("cmd_args, return_code", [
    pytest.param(
        ["ionex_diff", "--rhs", SAMPLE_IONEX, SAMPLE_IONEX], 0,
        id="two_ionex_files"
    ),
    pytest.param(
        ["ionex_diff", "--nequick", "110", "0.1", "0.0002", SAMPLE_IONEX], 0,
        id="nequick_and_ionex"
    ),
    pytest.param(
        ["ionex_diff", "--nequick", "110", "0.1", SAMPLE_IONEX], 2,
        id="error_insufficient_nequick_coeffs"
    ),
    pytest.param(
        ["ionex_diff", "--nequick", "110", "0.1", "3", "53", SAMPLE_IONEX], 2,
        id="error_wrong_number_of_nequick_coeffs"
    ),
    pytest.param(
        ["ionex_diff", "--nequick", "110", "0.1", "0.0002", "--rhs", SAMPLE_IONEX, SAMPLE_IONEX], 2,
        id="error_nequick_and_rhs"
    ),
    pytest.param(
        ["ionex_diff", "--nequick-ionex", "nequick.ionex", "--rhs", SAMPLE_IONEX, SAMPLE_IONEX], 2,
        id="error_nequick_output_and_rhs"
    ),
])
def test_ionex_diff_inputs(cmd_args: List[str], return_code: int):
    """
    Test the ionex_diff CLI with different input scenarios.
    """
    with tempfile.NamedTemporaryFile(mode="wt") as fh:
        cmd = cmd_args + [fh.name]  # Append the output file to the command
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert p.returncode == return_code


def test_ionex_write():
    """
    Test the ionex write function.
    """
    with tempfile.NamedTemporaryFile(mode="wt") as fh:

        gim_handler = gim.GimHandlerArray()
        ionex.load(SAMPLE_IONEX, gim_handler=gim_handler)
        gims = gim_handler.vtec_gims

        ionex.write(fh.name, gims, gim.GimType.TEC)

        assert os.path.getsize(fh.name) > 0, "File is empty"
