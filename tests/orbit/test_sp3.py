import numpy as np
import pytest

from pygnss.orbit.sp3 import compare, read_sp3, rms_stats

SP3 = """#dP2026 10  5  7  5  0.00000000       3 ORBIT IGS20 FIT TLE
*  2026 10  5  7  5  0.00000000
PL01   7000.000000      0.000000      0.000000 999999.999999
*  2026 10  5  7 10  0.00000000
PL01   6900.000000   1000.000000      0.000000 999999.999999
*  2026 10  5  7 15  0.00000000
PL01   6700.000000   2000.000000      0.000000 999999.999999
"""


def test_compare_shifted_cross_track(tmp_path):
    a = tmp_path / 'a.sp3'
    a.write_text(SP3)
    df = read_sp3(str(a))
    assert len(df) == 3

    shifted = df.copy()
    shifted['z'] += 10.0
    stats = rms_stats(compare(df, shifted))
    assert np.isclose(stats.loc['L01', 'cross'], 10.0)
    assert np.isclose(stats.loc['L01', '3D'], 10.0)
    assert np.isclose(stats.loc['L01', 'along'], 0.0)


def test_reassign(tmp_path):
    from pygnss.orbit.sp3 import cli, read_sp3
    src = tmp_path / 'a.sp3'
    src.write_text(SP3.replace('#dP', '+    1   L01  0  0\n#dP', 1).replace('+    1   L01  0  0\n#dP', '#dP')
                   + 'EOF\n')
    header = '+    1   L01  0  0  0\n'
    src.write_text(SP3.split('\n', 1)[0] + '\n' + header + SP3.split('\n', 1)[1]
                   + '/* NORAD L01=40044\nEOF\n')
    out = tmp_path / 'b.sp3'
    cli(['reassign', str(src), 'L01', 'L99', '-o', str(out)])
    text = out.read_text()
    assert 'L01' not in text and text.count('L99') == 5
    assert len(read_sp3(str(out))) == 3
    with pytest.raises(SystemExit):
        cli(['reassign', str(out), 'L01', 'L02', '-o', str(tmp_path / 'c.sp3')])
