from dataclasses import dataclass
import datetime
from typing import List

import numpy as np

@dataclass
class Gim():
    epoch: datetime.datetime
    longitudes: List[float]
    latitudes: List[float]
    vtec_values: List[List[float]]  # Grid of VTEC values n_latitudes (rows) x n_longitudes (columns)

    def __sub__(self, other: 'Gim') -> 'Gim':
        """
        Subtract the VTEC values of another Gim from this Gim

        :param other: The Gim to subtract.

        :return: A new Gim with the resulting VTEC values.
        """

        return subtract(self, other)


def subtract(lhs: Gim, rhs: Gim) -> Gim:
    """
    Subtract the VTEC values of two GIMs (lhs - rhs)

    :param lhs: Left-hand operand
    :param rhs: Right-hand operand

    :return: A new Gim with the resulting difference of VTEC values.

    :raises ValueError: If the dimensions of the GIMs do not match.
    """

    if lhs.epoch != rhs.epoch:
        raise ValueError(f"Epochs of both GIMs differ: {lhs.epoch} != {rhs.epoch}")

    if np.array_equal(lhs.latitudes, rhs.latitudes) == False:
        raise ValueError("Latitudes do not match between the two GIMs.")

    if np.array_equal(lhs.longitudes, rhs.longitudes) == False:
        raise ValueError("Longitude do not match between the two GIMs.")

    vtec_diff = np.subtract(lhs.vtec_values, rhs.vtec_values)

    return Gim(
        epoch=lhs.epoch,  # Keep the epoch of the first Gim
        longitudes=lhs.longitudes,
        latitudes=lhs.latitudes,
        vtec_values=vtec_diff.tolist(),
    )
