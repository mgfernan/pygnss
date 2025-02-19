import logging

import numpy as np

from . import StateHandler, Model


class Ukf(object):
    """
    Class to implement the Unscented Kalman Filter (UKF)
    """

    def __init__(self,
                 x: np.array,
                 P: np.array,
                 Q: np.array,
                 model: Model,
                 state_handler: StateHandler,
                 alpha: float = 1.0,
                 beta: float = 2.0,
                 kappa: float = 0.0,
                 logger: logging.Logger = logging):
        """
        Initialize the Ukf filter object

        :param x: a-priori state (n)
        :param P: a-priori error covariance (n x n)
        :param Q: Process noise covariance (n x n)
        :param model: Object of type Model that describes the underlying estimation model
        :param
        :param alpha: Primary scaling parameter
        :param beta: Secondary scaling parameter (Gaussian assumption)
        :param kappa: Tertiary scaling parameter
        """

        # Store the state, that will be propagated
        self.x = x
        self.P = P
        self.Q = Q

        self.model = model
        self.state_handler = state_handler

        self.logger = logger

        self.L = len(x)  # Number of parameters

        alpha2 = alpha * alpha

        self.lambd = alpha2 * (self.L + kappa) - self.L

        # Weights can be computed now, based on the setup input
        n_sigma_points = 2 * self.L + 1
        weight_k = 1.0 / (2.0 * (self.L + self.lambd))
        self.w_m = np.ones((n_sigma_points,)) * weight_k
        self.w_c = self.w_m.copy()

        k = self.lambd/(self.lambd + self.L)

        self.w_m[0] = k
        self.w_c[0] = k + 1 - alpha2 + beta

    def process(self, y_k: np.array, R: np.array, **kwargs):
        """
        Process an observation batch

        :param y_k: object that contains the observations
        :param R: matrix with the covariance of the measurement (i.e. measurement noise)
        """

        # Time update ----------------------------------------------------------

        chi_p = self._generate_sigma_points()

        # Obtain the propagated sigma points (chi_m, $\mathcal{X}_{k|k-1}^x$)
        chi_m = np.array([self.model.propagate_state(sigma_point) for sigma_point in chi_p])

        # From the propagated sigma points, obtain the averaged state ($\hat x_k^-$)
        x_m = np.sum(chi_m * self.w_m[:, np.newaxis], axis=0)

        # Compute the spread of the sigma points relative to the average
        spread_chi_m = chi_m - x_m

        # Covariance of the averaged propagated state ($\bf P_k^-$)
        P_m = self.Q + _weighted_average_of_outer_product(spread_chi_m, spread_chi_m, self.w_c)

        # Propagate the sigma points to the observation space (psi_m, $\mathcal{Y}_{k|k-1}$)
        psi_m = np.array([self.model.to_observations(sigma_point, **kwargs).y_m for sigma_point in chi_m])
        n_dim = len(psi_m.shape)
        if n_dim == 1:
            raise ValueError(f'Unexpected size for sigma point propagation, got [ {n_dim} ], '
                             'expected >= 2. Check that the method model.to_observations returns '
                             'an array of observations')

        # Compute the average observation from the given sigma points
        y_m = np.sum(psi_m * self.w_m[:, np.newaxis], axis=0)

        # Measurement update ---------------------------------------------------
        spread_psi_m = psi_m - y_m

        P_yy = R + _weighted_average_of_outer_product(spread_psi_m, spread_psi_m, self.w_c)
        P_xy = _weighted_average_of_outer_product(spread_chi_m, spread_psi_m, self.w_c)

        # Compute state
        self.x = x_m
        self.P = P_m

        try:
            # Kalman gain ($\mathcal{K}$))
            K = P_xy @ np.linalg.inv(P_yy)

            self.x = self.x + K @ (y_k - y_m)
            self.P = self.P - K @ P_yy @ K.T

        except np.linalg.LinAlgError as e:
            self.logger.warning(f'Unable to compute state, keeping previous one. Error: {e}')

        # Compute postfit residuals
        r = y_k - self.model.to_observations(self.x, **kwargs).y_m

        self.state_handler.process_state(self.x, self.P, postfits=r, **kwargs)

    def _generate_sigma_points(self) -> np.array:
        """
        Generate the sigma points

        >>> x0 = np.array([0.2, 0.6])
        >>> P0 = np.diag([0.8, 0.3])
        >>> ukf_filter = Ukf(x0, P0, None, None, None)
        >>> ukf_filter._generate_sigma_points()
        array([[ 0.2       ,  0.6       ],
               [ 1.46491106,  0.6       ],
               [ 0.2       ,  1.37459667],
               [-1.06491106,  0.6       ],
               [ 0.2       , -0.17459667]])
        """

        # self.P = _make_positive_definite(self.P)

        sqrt_P = np.linalg.cholesky(self.P)

        offsets = np.sqrt(self.L + self.lambd) * sqrt_P

        chi_p = np.vstack([self.x, self.x + offsets.T, self.x - offsets.T])

        return chi_p


class SquareRootUkf(object):
    """
    Class to implement the Unscented Kalman Filter (UKF)
    """

    def __init__(self,
                 x: np.array,
                 P: np.array,
                 model: Model,
                 state_handler: StateHandler,
                 alpha: float = 1.0,
                 beta: float = 2.0,
                 kappa: float = 0.0,
                 logger: logging.Logger = logging):
        """
        Initialize the Ukf filter object

        :param x: a-priori state
        :param P: a-priori error covariance
        :param Phi: State transition matrix (for the time update)
        :param alpha: Primary scaling parameter
        :param beta: Secondary scaling parameter (Gaussian assumption)
        :param kappa: Tertiary scaling parameter
        """

        # Store the state, that will be propagated
        self.x = x
        self.S = np.linalg.cholesky(P)

        self.model = model
        self.state_handler = state_handler

        self.logger = logger

        self.L = len(x)  # Number of parameters

        alpha2 = alpha * alpha

        self.lambd = alpha2 * (self.L + kappa) - self.L

        # Weights can be computed now, based on the setup input
        n_sigma_points = 2 * self.L + 1
        weight_k = 1.0 / (2.0 * (self.L + self.lambd))
        self.w_m = np.ones((n_sigma_points,)) * weight_k
        self.w_c = self.w_m.copy()

        k = self.lambd/(self.lambd + self.L)

        self.w_m[0] = k
        self.w_c[0] = k + 1 - alpha2 + beta

    def process(self, y_k):
        """
        Process an observation batch

        :param y_k: object that contains the observations
        """

        # Time update ----------------------------------------------------------

        chi_p = self._generate_sigma_points()

        # Obtain the propagated sigma points (chi_m, $\mathcal{X}_{k|k-1}^x$)
        chi_m = np.array([self.model.propagate_state(sigma_point) for sigma_point in chi_p])

        # From the propagated sigma points, obtain the averaged state ($\hat x_k^-$)
        x_m = np.sum(chi_m * self.w_m[:, np.newaxis], axis=0)

        # Compute the spread of the sigma points relative to the average
        spread_chi_m = chi_m - x_m

        # Covariance of the averaged propagated state ($\bf P_k^-$)
        P_m = _weighted_average_of_outer_product(spread_chi_m, spread_chi_m, self.w_c)

        # Propagate the sigma points to the observation space (psi_m, $\mathcal{Y}_{k|k-1}$)
        psi_m = np.array([self.model.to_observations(sigma_point) for sigma_point in chi_p])

        # Compute the average observation from the given sigma points
        y_m = np.sum(psi_m * self.w_m[:, np.newaxis], axis=0)

        # Measurement update ---------------------------------------------------
        spread_psi_m = psi_m - y_m

        P_yy = _weighted_average_of_outer_product(spread_psi_m, spread_psi_m, self.w_c)
        P_xy = _weighted_average_of_outer_product(spread_chi_m, spread_psi_m, self.w_c)

        # Compute state
        self.x = x_m
        self.P = P_m

        try:
            # Kalman gain ($\mathcal{K}$))
            K = P_xy @ np.linalg.inv(P_yy)

            self.x = self.x + K @ (y_k - y_m)
            self.P = self.P - K @ P_yy @ K.T

            # # Ensure positive definite matrix, known in issue in standard UKF
            # # https://stackoverflow.com/questions/67360472/negative-covariance-matrix-in-unscented-kalman-filter
            # # Get the diagonal of the matrix
            # diagonal = np.diag(self.P).copy()
            # diagonal[diagonal < 0] = 0
            # diagonal += 1.0e-5  # small jitter for regularization
            # np.fill_diagonal(self.P, diagonal)

        except np.linalg.LinAlgError as e:
            self.logger.warning(f'Unable to compute state, keeping previous one. Error: {e}')

        self.state_handler.process_state(self.x, self.P)

    def _generate_sigma_points(self) -> np.array:


        sqrt_P = np.linalg.cholesky(self.P)

        chi_p = np.vstack([self.x, self.x + sqrt_P, self.x - sqrt_P])

        return chi_p


def _weighted_average_of_outer_product(a: np.array, b: np.array, weights: np.array) -> np.array:
    """
    Computes the weighted average of the outer products of two arrays of lists

    Given two arrays $a$ and $b$, this method implements

    $$
    P = \\sum_{i=0}^N w_i \\cdot \\left( a_i \\cdot b_i^T \\right)
    $$


    >>> a = np.array([[1, 2], [3, 4]])
    >>> b = np.array([[5, 6], [7, 8]])
    >>> weights = np.array([1, 2])
    >>> _weighted_average_of_outer_product(a, b, weights)
    array([[47, 54],
           [66, 76]])
    """

    if a.shape[0] != b.shape[0]:
        raise ValueError(f'Number of rows in input vectors differ: [ {a.shape[0]} ] != [ {b.shape[0]} ]')

    elif a.shape[0] != len(weights):
        raise ValueError(f'Incorrect size of the weights vector: [ {a.shape[0]} ] != [ {len(weights)} ]')

    n_rows = a.shape[0]

    products = [np.outer(a[i], b[i]) * weights[i] for i in range(n_rows)]

    average = np.sum(products, axis=0)

    return average


def _make_positive_definite(matrix, epsilon=1e-6):
    """
    Makes a matrix positive definite by adding a small value to its diagonal.

    Args:
        matrix: The input matrix (NumPy array).
        epsilon: A small positive value to add to the diagonal (default: 1e-6).

    Returns:
        A positive definite matrix.
    """

    eigenvalues, _ = np.linalg.eig(matrix)
    min_eigenvalue = np.min(eigenvalues)

    if min_eigenvalue < 0:
        shift = -min_eigenvalue + epsilon
        return matrix + shift * np.eye(matrix.shape[0])
    else:
        return matrix
