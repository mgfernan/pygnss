from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime
import enum
from typing import List

import numpy as np


class GimType(enum.Enum):
    """
    Type of Global Ionospheric Map (VTEC, RMS)
    """

    TEC = enum.auto()
    RMS = enum.auto()


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


class GimHandler(ABC):

    @abstractmethod
    def process(self, gim: Gim, type: GimType):
        """
        Process a GIM file
        """
        pass

class GimHandlerArray(GimHandler):
    """
    Handler to store the incoming GIMs in arrays
    """

    def __init__(self):
        self.vtec_gims: List[Gim] = []
        self.rms_gims: List[Gim] = []

    def process(self, gim: Gim, type: GimType):
        """
        Process a GIM file
        """

        if type == GimType.TEC:
            self.vtec_gims.append(gim)

        elif type == GimType.RMS:
            self.rms_gims.append(gim)

        else:
            raise ValueError(f'Gim Type [ {type} ] not supported')


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


def subtract_gims(lhs: List[Gim], rhs: List[Gim]) -> List[Gim]:
    """
    Subtract the VTEC values of two lists of GIMs (lhs - rhs).

    The subtraction is performed only for GIMs with matching epochs, latitudes, and longitudes.
    If a GIM in one list does not have a matching epoch in the other list, it is ignored.

    :param lhs: The first list of GIMs (left-hand operand).
    :param rhs: The second list of GIMs (right-hand operand).
    :return: A list of GIMs resulting from the subtraction.
    :raises ValueError: If latitudes or longitudes do not match for matching epochs.
    """
    result = []

    # Create a dictionary for quick lookup of GIMs in the rhs list by epoch
    rhs_dict = {gim.epoch: gim for gim in rhs}

    for gim_lhs in lhs:

        # Check if there is a matching epoch in the rhs list
        if gim_lhs.epoch in rhs_dict:
            gim_rhs = rhs_dict[gim_lhs.epoch]

            try:
                result.append(gim_lhs - gim_rhs)
            except ValueError as e:
                raise ValueError(f"Error subtracting GIMs for epoch {gim_lhs.epoch}: {e}")

    return result

