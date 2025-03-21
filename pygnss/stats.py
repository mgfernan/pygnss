import argparse
import sys
from typing import Iterable, Tuple

import numpy as np


def cdf_cli():
    argParser = argparse.ArgumentParser(description=__doc__,
                                        formatter_class=argparse.RawDescriptionHelpFormatter)  # verbatim

    argParser.add_argument('--n-bins', '-n', metavar='<int>', type=int,
                           help='Number of bins', default=10)

    args = argParser.parse_args()

    samples = []

    for sample in sys.stdin:
        try:
            _ = float(sample)
        except ValueError:
            continue

        samples.append(float(sample))

    pdf, edges = np.histogram(samples, bins=args.n_bins, density=True)
    binwidth = edges[1] - edges[0]

    pdf = np.array(pdf) * binwidth
    cdf = np.cumsum(pdf)

    for i in range(args.n_bins):
        print(f"{edges[i]} {pdf[i]} {cdf[i]}")



def compute_robust(data:Iterable) -> Tuple[float, float]:
    """
    Compute the robust statistics for the input data set. These robust
    statistics are:
    - median
    - Median Absolute Deviation (MAD) (https://en.wikipedia.org/wiki/Median_absolute_deviation)

    :param data: input data (array-like)
    :return: the median and mad

    Example (extracted from http://kldavenport.com/absolute-deviation-around-the-median/)
    >>> data = [2, 6, 6, 12, 17, 25 ,32]
    >>> median, mad = compute_robust(data)
    >>> np.allclose(median, 12)
    True
    >>> np.allclose(mad, 6)
    True
    """

    if len(data) == 0:
        raise ValueError("Unable to compute the robust statistics for an empty list or array")

    median = np.median(data)

    mad = np.median(np.abs(data - median))

    return median, mad


def rms(values: Iterable) -> float:
    """
    Compute the Root Mean Square of an array of values

    >>> array = [1, 2, 3, 4, 5]
    >>> rms(array)
    3.3166247903554
    """
    return np.sqrt(np.mean(np.square(values)))
