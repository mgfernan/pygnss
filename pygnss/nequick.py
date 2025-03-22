import datetime
import math
from typing import List

import numpy as np

import nequick

from pygnss import ionex
import pygnss.iono.gim


class GimIonexHandler(nequick.GimHandler):
    """
    A handler that accumulates GIMs and then generates an IONEX file
    """

    def __init__(self, coeffs: nequick.Coefficients):
        self._coeffs = coeffs
        self._gims: List[nequick.gim.Gim] = []

    def process(self, gim: nequick.Gim):
        """
        Store the incoming gim for later process
        """

        # Check that the latitude and longitude values are
        # the same as the last appended gim
        if len(self._gims) > 0:
            last_gim = self._gims[-1]
            if np.array_equal(last_gim.latitudes, gim.latitudes) == False:
                raise ValueError("Latitude values do not match")
            if np.array_equal(last_gim.longitudes, gim.longitudes) == False:
                raise ValueError("Longitude values do not match")

        self._gims.append(gim)

    def to_ionex(self, filename: str, pgm: str = "pygnss", runby: str = "pygnss") -> None:

        comment_lines = [
            "Maps computed using the NeQuick model with the following",
            "coefficients:",
            f"a0={self._coeffs.a0:<17.6f}a1={self._coeffs.a1:<17.8f}a2={self._coeffs.a2:<17.11f}"
        ]

        ionex.write(filename, self._gims, pygnss.iono.gim.GimType.TEC, pgm, runby,
                    comment_lines=comment_lines)


def to_ionex(filename: str, coeffs: nequick.Coefficients, dates: List[datetime.datetime]):

    gim_handler = GimIonexHandler(coeffs)

    for date in dates:
        nequick.to_gim(coeffs, date, gim_handler=gim_handler)

    gim_handler.to_ionex(filename)
