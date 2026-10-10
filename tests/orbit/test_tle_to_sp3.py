import datetime
import pathlib

import numpy as np

from pygnss.orbit.tle import TLE
from pygnss.orbit.tle_to_sp3 import build_sp3, ErrorModel, MAX_SATS_PER_FILE
import pytest


def _fix(tle_lines):
    from pygnss.orbit.tle import calculate_checksum
    return [ln[:68] + str(calculate_checksum(ln[:68])) for ln in tle_lines]


def _tle(l1, l2, label):
    a, b = _fix([l1, l2])
    return TLE(a, b, label=label)


def _sample(n=1):
    out = []
    for i in range(n):
        l1 = f"1 {25544 + i:05d}U 98067A   24048.54791667  .00016717  00000+0  30000-3 0  999"
        l2 = f"2 {25544 + i:05d}  51.6416 247.4627 0006703 130.5360 325.0288 15.49815350 1000"
        out.append(_tle(l1, l2, f"SAT-{i}"))
    return out


def test_build_sp3():
    start = datetime.datetime(2024, 2, 17, 13, 0, 18)
    out = build_sp3(_sample(2), start, start + datetime.timedelta(hours=1), 600.0)
    lines = out.splitlines()

    assert lines[0].startswith('#dP2024  2 17 13  0 18.00000000')
    assert lines[2].startswith('+    2   L01L02')
    assert any(ln == '/* NORAD L01=25544 L02=25545' for ln in lines)
    assert lines[-1] == 'EOF'
    assert sum(ln.startswith('*') for ln in lines) == 7

    p = next(ln for ln in lines if ln.startswith('PL01'))
    xyz = np.array([float(p[4 + 14 * i:18 + 14 * i]) for i in range(3)])
    assert 6.5e3 < np.linalg.norm(xyz) < 7.0e3  # km
    assert p[46:60].strip() == '999999.999999'


def test_error_grows_with_age():
    start = datetime.datetime(2024, 2, 17, 13, 0, 18)
    out = build_sp3(_sample(1), start, start + datetime.timedelta(days=3), 86400.0, ErrorModel())
    sds = [int(ln[61:63]) for ln in out.splitlines() if ln.startswith('PL01')]
    assert sds == sorted(sds) and sds[-1] > sds[0]


def test_too_many_sats():
    start = datetime.datetime(2024, 2, 17, 13, 0, 18)
    with pytest.raises(ValueError):
        build_sp3(_sample(MAX_SATS_PER_FILE + 1), start, start, 300.0)


def test_cli_single_file_with_many_tles(tmp_path):
    """One file with several (and duplicated) TLEs of the same platform, CRLF line endings"""
    from pygnss.orbit.tle_to_sp3 import cli
    from pygnss.orbit.tle import read_celestrak

    tle_file = pathlib.Path(__file__).parent.parent / 'data' / 'spire_lemur1_multi_tle.txt'
    assert len(read_celestrak(str(tle_file))) == 8

    out = tmp_path / 'out.sp3'
    cli([str(tle_file), '-o', str(out), '--start', '2026-10-05T12:00:00', '--end', '2026-10-06T12:00:00',
         '--interval', '900'])

    lines = out.read_text().splitlines()
    assert lines[2].startswith('+    1   L01')
    assert '/* NORAD L01=40044' in lines
    assert sum(ln.startswith('PL01') for ln in lines) == 97
    assert lines[-1] == 'EOF'


def test_multiple_platforms_with_several_tles_each():
    start = datetime.datetime(2026, 10, 5, 12)
    tles = _sample(2)
    l1 = "1 25544U 98067A   24048.64791667  .00016717  00000+0  30000-3 0  999"
    l2 = "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.49815350 1000"
    tles.append(_tle(l1, l2, "SAT-0"))
    tles.append(tles[0])
    out = build_sp3(tles, datetime.datetime(2024, 2, 17, 13), datetime.datetime(2024, 2, 17, 14), 1800.0)
    lines = out.splitlines()
    assert lines[2].startswith('+    2   L01L02')
    assert sum(ln.startswith('PL01') for ln in lines) == 3
    assert sum(ln.startswith('PL02') for ln in lines) == 3


def test_sat_id_assignment():
    start = datetime.datetime(2024, 2, 17, 13)
    out = build_sp3(_sample(3), start, start, 300.0, sat_id_map={25545: 'L01', 25544: 'L42'})
    lines = out.splitlines()
    assert lines[2].startswith('+    3   L01L02L42')
    assert '/* NORAD L01=25545 L02=25546 L42=25544' in lines


def test_sat_id_assignment_duplicate():
    start = datetime.datetime(2024, 2, 17, 13)
    with pytest.raises(ValueError):
        build_sp3(_sample(2), start, start, 300.0, sat_id_map={25544: 'L07', 25545: 'L07'})


def test_cli_sat_id(tmp_path):
    from pygnss.orbit.tle_to_sp3 import cli

    tle_file = pathlib.Path(__file__).parent.parent / 'data' / 'spire_lemur1_multi_tle.txt'
    out = tmp_path / 'out.sp3'
    cli([str(tle_file), '-o', str(out), '--start', '2026-10-05T12:00:00', '--end', '2026-10-05T13:00:00',
         '--sat-id', '40044=L05'])
    lines = out.read_text().splitlines()
    assert '/* NORAD L05=40044' in lines
    assert any(ln.startswith('PL05') for ln in lines)

    with pytest.raises(SystemExit):
        cli([str(tle_file), '-o', str(out), '--sat-id', '99999=L05'])
    with pytest.raises(SystemExit):
        cli([str(tle_file), '-o', str(out), '--sat-id', '40044=bad'])
