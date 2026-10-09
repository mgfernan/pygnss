import io
import os

import numpy as np
import pytest

from pygnss.leo.csv_to_rinex import convert, parse_rx_location, read_leo_csv
from pygnss.leo.norad import SatNameResolver
from pygnss.rinex import to_dataframe

CSV = os.path.join(os.path.dirname(__file__), 'data',
                   'globalstar_orbcomm_iridium_01-10-2026_00:00:00_01-10-2026_00:07:59_UTC.csv')


@pytest.fixture(scope='module')
def rinex_file(tmp_path_factory):
    path = str(tmp_path_factory.mktemp('leo') / 'out.rnx')
    with open(path, 'w') as fh:
        n_epochs = convert(CSV, fh, marker_name='TEST')
    return path, n_epochs


def test_header(rinex_file):
    path, _ = rinex_file
    text = open(path).read()
    assert 'A    2 D9C S9C' in text
    assert 'B    3 D3C S3C X3C' in text
    assert 'D    2 D6C S6C' in text
    assert 'GPS' in text


def test_parse_rx_location():
    assert len(parse_rx_location(open(CSV).readline())) == 3


def test_unknown_satellite():
    with pytest.raises(KeyError):
        convert(io.StringIO('id,constellation,satellite_name,frequency,doppler,snr,timestamp_utc\n'
                            '1,iridium,IRIDIUM 999,1626270833,1.0,10.0,01-10-2026 00:00:01.000000000\n'),
                io.StringIO(), resolver=SatNameResolver())


def test_round_trip(rinex_file):
    path, n_epochs = rinex_file
    csv, _ = read_leo_csv(CSV)
    df = to_dataframe(path)

    assert len(df) == len(csv) == 873
    assert df['epoch'].nunique() == n_epochs

    # GPS time = UTC + 18 s
    csv = csv.sort_values('timestamp').reset_index(drop=True)
    df = df.sort_values('epoch').reset_index(drop=True)
    dt = (df['epoch'] - csv['timestamp'] - np.timedelta64(18, 's')).abs()
    assert dt.max() < np.timedelta64(2, 'us')

    assert sorted(df['constellation'].unique()) == ['A', 'B', 'D']
    assert np.allclose(np.sort(df['doppler'].to_numpy()), np.sort(csv['doppler'].to_numpy()), atol=1e-3)
    assert np.allclose(np.sort(df['snr'].to_numpy()), np.sort(csv['snr'].to_numpy()), atol=1e-3)


def test_utc_time_system():
    out = io.StringIO()
    convert(CSV, out, time_system='utc')
    assert 'UTC         TIME OF FIRST OBS' in out.getvalue()
    assert '  2026    10     1     0     0    1.6169900     UTC' in out.getvalue()
