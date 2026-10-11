import io
import os

import numpy as np
import pytest

from pygnss.leo.csv_to_rinex import convert, parse_rx_location, read_leo_csv
from pygnss.leo.norad import SatNameResolver
import pandas as pd

from pygnss.rinex import to_dataframe
from pygnss.rinex.cli import to_parquet

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
    assert 'B    3 D3C S3C F3C' in text
    assert 'D    2 D6C S6C' in text
    assert 'GPS' in text


def test_parse_rx_location():
    assert len(parse_rx_location(open(CSV).readline())) == 3


def test_unknown_satellite():
    with pytest.raises(KeyError):
        convert(io.StringIO('id,constellation,satellite_name,frequency,doppler,snr,timestamp_utc\n'
                            '1,iridium,IRIDIUM 999,1626270833,1.0,10.0,01-10-2026 00:00:01.000000000\n'),
                io.StringIO(), resolver=SatNameResolver())


def test_six_digit_norad_round_trip(tmp_path):
    csv = io.StringIO('id,constellation,satellite_name,frequency,doppler,snr,timestamp_utc\n'
                      '1,iridium,IRIDIUM 999,1626270833,1.0,10.0,01-10-2026 00:00:01.000000000\n')
    output = tmp_path / 'six_digit.rnx'
    with output.open('w') as fh:
        convert(csv, fh, resolver=SatNameResolver({'IRIDIUM 999': 100972}), time_system='utc')

    text = output.read_text()
    assert 'RINEX-LEO 2.00' in text
    assert 'D100972' in text
    df = to_dataframe(str(output))
    assert df.iloc[0]['sat'] == 'D100972'
    assert int(df.iloc[0]['sat'][1:]) == 100972


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


def test_orbcomm_frequency_slots(rinex_file):
    path, _ = rinex_file
    csv, _ = read_leo_csv(CSV)
    orbcomm = [line for line in open(path) if line.startswith('B041182')]
    slots = sorted(int(line[44:58].split('.')[0]) for line in orbcomm)
    expected = sorted(int(round((f - 137.2e6) / 2500)) for f in csv[csv['constellation'] == 'orbcomm']['frequency'])
    assert slots == expected


def test_globalstar_only(tmp_path):
    path = str(tmp_path / 'globalstar.rnx')
    with open(path, 'w') as fh:
        convert(CSV, fh, constellations=['globalstar'])

    text = open(path).read()
    assert 'A    2 D9C S9C' in text
    assert 'SYS / # / OBS TYPES' in text and text.count('SYS / # / OBS TYPES') == 1

    csv, _ = read_leo_csv(CSV)
    csv = csv[csv['constellation'] == 'globalstar']
    df = to_dataframe(path)

    assert len(df) == len(csv) == 823
    assert set(df['constellation']) == {'A'}
    assert set(df['sat']) == {'A037741', 'A038045', 'A039076'}
    assert np.allclose(np.sort(df['doppler'].to_numpy()), np.sort(csv['doppler'].to_numpy()), atol=1e-3)
    assert np.allclose(np.sort(df['snr'].to_numpy()), np.sort(csv['snr'].to_numpy()), atol=1e-3)


def test_rinex_to_parquet_leo(rinex_file, tmp_path):
    path, _ = rinex_file
    output = str(tmp_path / 'leo.parquet')
    to_parquet([path], output_filename=output, station_name='TEST')

    df = pd.read_parquet(output)
    assert len(df) == 873
    assert set(df['station']) == {'test'}
    assert set(df['constellation']) == {'A', 'B', 'D'}
    assert {'A037741', 'B041182', 'D041921'} <= set(df['sat'])

    csv, _ = read_leo_csv(CSV)
    orbcomm = df[df['constellation'] == 'B']
    expected = sorted(int(round((f - 137.2e6) / 2500)) for f in csv[csv['constellation'] == 'orbcomm']['frequency'])
    assert sorted(orbcomm['freq_slot'].astype(int)) == expected
    assert df[df['constellation'] != 'B']['freq_slot'].isna().all()


def test_freq_slot_absent_without_fdma(tmp_path):
    path = str(tmp_path / 'globalstar.rnx')
    with open(path, 'w') as fh:
        convert(CSV, fh, constellations=['globalstar'])
    assert 'freq_slot' not in to_dataframe(path).columns
