from dataclasses import dataclass
import datetime
import enum
from typing import List

from ..gnss.types import TrackingChannel, Satellite



@dataclass
class ObservableType(object):
    type: str
    channel: TrackingChannel

    @staticmethod
    def from_string(observable_type: str) -> 'ObservableType':

        if len(observable_type) != 3:
            raise ValueError(f'Invalid length for observable type [ {observable_type} ] (must conform to RINEX v3 3-char format)')
        return ObservableType(observable_type[0], TrackingChannel.from_rinex3_code(observable_type))

    def __repr__(self):
        return f'{self.type:1s}{self.channel}'


@dataclass
class ObservableValue(object):
    value: float
    lli: int
    snr: int


@dataclass
class Record(object):
    epoch: datetime.datetime
    sat: Satellite
    channel: TrackingChannel
    range: float
    phase: float
    doppler: float
    snr: float
    slip: int

    def set_value(self, observable_type: ObservableType, observable_value: ObservableValue) -> None:

        if observable_type.type == 'C':
            self.range = observable_value.value
        elif observable_type.type == 'L':
            self.phase = observable_value.value
        elif observable_type.type == 'D':
            self.doppler = observable_value.value
        elif observable_type.type == 'S':
            self.snr = observable_value.value
        else:
            raise TypeError(f'Unrecognise observable type {observable_type.type}')

        if observable_value.lli != 0:
            self.slip = 1

    def aslist(self) -> list:

        return [self.epoch, self.sat.constellation.value, str(self.sat), str(self.channel),
                f'{self.sat}{self.channel}', self.range, self.phase, self.doppler, self.snr, self.slip]

    @staticmethod
    def get_list_fieldnames() -> List[str]:
        return ["epoch", "constellation", "sat", "channel", "signal", "range", "phase", "doppler", "snr", "slip"]


class EpochFlag(enum.Enum):

    OK = 0
    POWER_FAILURE = 1
    MOVING_ANTENNA = 2
    NEW_SITE = 3
    HEADER_INFO = 4
    EXTERNAL_EVENT = 5

    @staticmethod
    def get_from_line(line: str) -> 'EpochFlag':
        """
        Extract the epoch flag from the incoming line

        >>> EpochFlag.get_from_line(">                              4 95")
        <EpochFlag.HEADER_INFO: 4>
        >>> EpochFlag.get_from_line("> 2023 08 03 12 00  8.0000000  0 38")
        <EpochFlag.OK: 0>
        >>> EpochFlag.get_from_line(None)
        Traceback (most recent call last):
        ...
        ValueError: The line [ None ] does not have an Epoch Flag
        >>> EpochFlag.get_from_line("")
        Traceback (most recent call last):
        ...
        ValueError: The line [  ] does not have an Epoch Flag
        >>> EpochFlag.get_from_line("> 2023 08 03 1")
        Traceback (most recent call last):
        ...
        ValueError: The line [ > 2023 08 03 1 ] does not have an Epoch Flag
        """

        INDEX = 31

        if line and len(line) >= INDEX + 1 and line[0] == '>':
            epoch_flag = int(line[INDEX])
            return EpochFlag(epoch_flag)

        raise ValueError(f'The line [ {line} ] does not have an Epoch Flag')
