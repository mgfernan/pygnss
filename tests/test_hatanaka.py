import gzip
from pathlib import Path
import tempfile

from pygnss import hatanaka

# Get the absolute path to the hatanakalib directory
hatanakalib_path = Path(__file__).parent.parent / 'submodules' / 'hatanakalib'

# Construct the path to the data file
crz_file = hatanakalib_path / 'tests' / 'data' / 'ACSO00XXX_R_20241310000_05S_01S_MO.crx.gz'

def test__hatanaka_to_dataframe_crx():
    """Hatanaka :: To DataFrame (CRX) """

    # Uncompress the file
    with gzip.open(str(crz_file), 'rb') as f_in:
        with tempfile.NamedTemporaryFile(delete=False) as f_out:
            f_out.write(f_in.read())
            f_out.seek(0)

            df = hatanaka.to_dataframe(f_out.name)

    assert len(df) == 600

def test__hatanaka_to_dataframe_crz():
    """Hatanaka :: To DataFrame (CRZ) """

    df = hatanaka.to_dataframe(str(crz_file))

    assert len(df) == 600
