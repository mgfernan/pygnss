from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime
import numpy as np

from ..gnss.types import TrackingChannel, Satellite



@dataclass
class Clock(object):
    bias_s: float
    drift_s_per_s: float
    drift_rate_s_per_s2: float

    ref_epoch: datetime = None


class ClockModel(ABC):
    """
    This abstract class provides with an interface to provide with a Clock model
    """

    @abstractmethod
    def get_clock(self, satellite: Satellite, epoch: datetime.datetime) -> Clock:
        """
        Get the clock for a satellite and an epoch
        """
        pass


class ZeroClockModel(ClockModel):
    """
    Clock model with 0 bias and drift
    """

    def get_clock(self, satellite: Satellite, epoch: datetime.datetime) -> Clock:
        return Clock(0, 0, 0)


class GnssRandomClock(ClockModel):
    """
    Generate a clock model with random realizations for the clock bias and
    drift.
    """

    def __init__(self, bias_max_s: float = 0.0005, drift_max_s_per_s: float = 1.0e-11):
        """
        Initialize the object with the threshold values for the bias and drift.
        In certain works, the typical values of bias and drift for GPS, Galileo
        and Beidou are usually contained between -/+0.5ms and-/+1e-11 respectively
        """
        self.bias_max_s = bias_max_s
        self.drift_max_s_per_s = drift_max_s_per_s

        # Internal memory to store the state of the previous clock
        self.clocks = {}

    def get_clock(self, satellite: Satellite, epoch: datetime.datetime) -> Clock:

        clock = self.clocks.get(satellite, None)

        if clock is None:
            bias_s = np.random.uniform(low=-self.bias_max_s, high=self.bias_max_s)
            drift_s_per_s = np.random.uniform(low=-self.drift_max_s_per_s, high=self.drift_max_s_per_s)

            clock = Clock(bias_s, drift_s_per_s, 0.0, ref_epoch=epoch)

            self.clocks[satellite] = clock

        # Compute the bias for the updated clock
        dt = (epoch - clock.ref_epoch).total_seconds() if clock.ref_epoch else 0.0
        clock = Clock(clock.bias_s + clock.drift_s_per_s * dt, clock.drift_s_per_s, 0.0)

        return clock


@dataclass
class CodeBiases(ABC):
    """
    This abstract class provides with an interface to provide with the code biases
    """

    @abstractmethod
    def get_base_tgd(self) -> float:
        """
        Get the base group delay
        """
        return 0.0

    @abstractmethod
    def get_code_bias(self, channel: TrackingChannel) -> float:
        """
        Get the code bias for the given channel
        """
        return 0.0


class ZeroCodeBiases(CodeBiases):

    def get_base_tgd(self) -> float:
        return super().get_base_tgd()

    def get_code_bias(self, channel: TrackingChannel) -> float:
        return super().get_code_bias(channel)

@dataclass
class LEOCodeBiases(CodeBiases):
    """
    Class to handle the code biases for the generic LEO constellation
    """
    tgd_s: float
    isc_s9c_s: float

    def get_base_tgd(self) -> float:
        return self.tgd_s

    @abstractmethod
    def get_code_bias(self, channel: TrackingChannel) -> float:

        if channel == TrackingChannel.from_string('9C'):
            return self.isc_s9c_s

        raise ValueError(f'Tracking channel [ {channel} ] not supported by LEO constellations')
