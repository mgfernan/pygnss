import os
import tempfile

import pytest

from pygnss import ionex
from pygnss.iono import gim

DATA_FOLDER = os.path.join(os.path.dirname(__file__), "./data")

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
