from pathlib import Path

import pandas as pd

from pygnss._c_ext import Klobuchar

def test__klobuchar_type():
    """Klobuchar C extension type is available"""

    alphas = [0, 0, 0, 0]
    betas = [0, 0, 0, 0]

    klobuchar = Klobuchar(*alphas, *betas)
    assert isinstance(klobuchar, Klobuchar)


def test__klobuchar_compute_slant_delay():
    """Klobuchar :: Compute Slant Delay"""

    test_file = Path(__file__).parent / '..' / 'data' / 'compute_klobuchar_tests.txt'

    df = pd.read_csv(test_file, header=None, delim_whitespace=True, names=[
        'tow', 'latitude', 'longitude', 'elevation', 'azimuth',
        'alpha0', 'alpha1', 'alpha2', 'alpha3',
        'beta0', 'beta1', 'beta2', 'beta3',
        'delay'])

    for test_case in df.itertuples():
        alphas = [test_case.alpha0, test_case.alpha1,
                           test_case.alpha2, test_case.alpha3]
        betas = [test_case.beta0, test_case.beta1,
                          test_case.beta2, test_case.beta3]

        klobuchar = Klobuchar(*alphas, *betas)

        slant_delay = klobuchar.compute_slant_delay(
            test_case.tow,
            test_case.latitude,
            test_case.longitude,
            test_case.azimuth,
            test_case.elevation
        )

        assert abs(slant_delay - test_case.delay) < 1.0e-10  # Allow small tolerance
