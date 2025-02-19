"""
Module for the EKF
"""
import logging
from typing import Tuple

import numpy as np

from . import StateHandler, Model


class Ekf(object):
    """
    Extended Kalman Filter (EKF)
    """

    def __init__(self,
                 x0: np.array,
                 P0: np.array,
                 Q: np.array,
                 model: Model,
                 state_handler: StateHandler,
                 logger: logging.Logger = logging):
        """
        Initialize the EKF filter object
        """

        self.x = x0
        self.P = P0
        self.Q = Q

        self.model = model
        self.state_handler = state_handler

        self.logger = logger

        self.L = len(self.x)

    def process(self, y_k: np.array, R: np.array, **kwargs):
        """
        Process an observation batch
        """

        # Time update ----------------------------------------------------------
        x_m, P_m = self._time_update()

        # Measurement update ---------------------------------------------------
        y_m, H = self.model.to_observations(x_m, compute_jacobian=True, **kwargs)

        P_yy = H @ P_m @ H.T + R
        P_xy = P_m @ H.T

        self.x = x_m
        self.P = P_m

        try:
            K = P_xy @ np.linalg.inv(P_yy)  # Calculate Kalman gain

            self.x = self.x + K @ (y_k - y_m)  # Update state estimate
            self.P = self.P - K @ H @ P_m  # Update covariance estimate

        except np.linalg.LinAlgError as e:
            self.logger.warning(f'Unable to compute state, keeping previous one. Error: {e}')

        # Compute postfit residuals
        r = y_k - self.model.to_observations(self.x, **kwargs).y_m

        self.state_handler.process_state(self.x, self.P, postfits=r, **kwargs)

    def _time_update(self) -> Tuple[np.array, np.array]:
        """
        Perform a time update step
        """

        Phi = self.model.Phi

        x_m = self.model.propagate_state(self.x)
        P_m = Phi @ self.P @ Phi.T + self.Q

        return x_m, P_m
