"""pygnss.filter.particle
=================================

Lightweight particle filtering utilities for non-linear / non-Gaussian
state estimation.

This module provides:

- ``Particles``: a minimal container for particle states and weights.
- ``multinomial_resample``: a simple inverse-CDF resampler that returns
    equally weighted copies of drawn particles.
- ``WeightEstimatorInterface`` / ``WeightEstimatorGaussian``: pluggable
    likelihood estimators that map pre-fit residuals to non-negative weights.
- ``Filter``: a straightforward sequential Monte Carlo (particle) filter
    that uses a user-supplied ``Model`` and a ``StateHandler`` to consume
    state estimates.

Design notes
-----------
- User models must implement the ``Model`` contract (``propagate_state`` and
    ``to_observations``).
- Weights passed into resampling functions are assumed to be non-negative;
    the filter normalizes weights internally before sampling.
- The filter applies a post-resample "roughening" step to mitigate sample
    impoverishment. Per-component roughening standard deviations are available
    on the ``Filter`` instance as ``roughening_sigma_pos`` and
    ``roughening_sigma_vel`` (position and velocity components respectively).

Examples
--------
See ``tests/filter/test_model.py`` for an end-to-end usage example with
synthetic observations.
"""

from abc import ABC, abstractmethod
import copy
from dataclasses import dataclass
import logging
from typing import Callable, List, Tuple, Optional
import numpy as np

from . import Model, State, StateHandler, FilterInterface


@dataclass
class Particles:
    """Container holding a set of particles and their associated weights.

    Parameters
    ----------
    particles
        List of candidate states (particles). Each state must be compatible
        with the ``Model`` used by the filter (e.g., a NumPy array).
    weights
        List or array of non-negative weights, one per particle. In typical
        usage these are normalized to sum to 1.

    Notes
    -----
    The container is intentionally minimal. Helper methods are provided to
    retrieve common summaries (e.g., the maximum-likelihood particle).
    """

    particles: List[State]
    weights: List[float]

    def get_max_likely(self) -> State:
        """Return the particle with the highest weight.

        Returns
        -------
        State
            The particle corresponding to ``argmax(weights)``.
        """

        return self.particles[np.argmax(self.weights)]

    def __len__(self) -> int:
        """Return the number of particles contained."""

        return len(self.particles)


ResampleFunctionSignature = Callable[
    [List[State], np.ndarray, int], Tuple[List[State], np.ndarray]
]
ParticleCallbackSignature = Callable[[List[State], np.ndarray], None]


def void_particle_callback(_particles: List[State], _weights: np.ndarray) -> None:
    """No-op particle callback.

    This function implements the ``ParticleCallbackSignature`` and performs no
    action. It is provided as the default callback for ``Filter`` when the
    user does not need any per-epoch particle inspection.
    """


def multinomial_resample(
    particles: List[State], weights: np.ndarray, new_n_particles: int | None = None
) -> Tuple[List[State], np.ndarray]:
    """Resample particles via inverse-CDF (multinomial) sampling.

    The function draws ``new_n_particles`` indices from the discrete
    distribution defined by ``weights`` using sorted uniform thresholds and
    the cumulative distribution function (CDF). Returned particles are deep
    copies of the selected inputs and are assigned equal weights
    ``1/new_n_particles``.

    Notes
    -----
    - Input weights are normalized internally. If the weight sum is zero a
      uniform fallback distribution is used to avoid division by zero.
    - This implementation is simple and clear; for large numbers of
      particles consider using ``numpy.random.choice`` with the
      ``p=weights`` argument for optimized sampling.

    Parameters
    ----------
    particles : list[State]
        Candidate particle states.
    weights : numpy.ndarray
        Non-negative weights matching ``particles``. They will be
        normalized before sampling.
    new_n_particles : int, optional
        Number of particles to draw. Defaults to ``len(particles)``.

    Returns
    -------
    (list[State], numpy.ndarray)
        Tuple containing the resampled list of particle states (deep copies)
        and an array of equal weights summing to 1.
    """

    # Normalize weights defensively and build CDF
    w = np.asarray(weights, dtype=float)
    w_sum = float(w.sum())
    if w_sum <= 0:
        # Avoid division by zero; fall back to uniform
        w = np.full_like(w, 1.0 / len(w), dtype=float)
    else:
        w = w / w_sum

    cumulative_distribution = np.cumsum(w)

    if new_n_particles is None:
        new_n_particles = len(particles)

    q = np.sort(np.random.uniform(size=new_n_particles))

    particle_indices = [int(np.argmax(cumulative_distribution > th)) for th in q]

    new_particles = [copy.deepcopy(particles[i]) for i in particle_indices]

    # New weights are set equal to avoid Degenerate particles after resampling
    # As explained in Section 4.2.1 of https://pmc.ncbi.nlm.nih.gov/articles/PMC7826670/pdf/sensors-21-00438.pdf
    new_weights = np.full(new_n_particles, 1.0 / new_n_particles, dtype=float)

    return new_particles, new_weights


class WeightEstimatorInterface(ABC):
    """
    Interface for computing particle weights (likelihoods).

    Concrete implementations should map a vector of pre-fit residuals to a
    non-negative weight (likelihood). Larger values indicate more plausible
    particles given the observations.
    """

    @abstractmethod
    def compute(self, prefits: np.ndarray, **kwargs) -> float:
        """Compute a non-negative likelihood weight from pre-fit residuals.

        Parameters
        ----------
        prefits : numpy.ndarray
            Array of pre-fit residuals (measured - modelled observations)
            for the candidate particle.
        **kwargs : dict
            Optional algorithm-specific parameters (for example measurement
            noise statistics) that concrete implementations may accept.

        Returns
        -------
        float
            A non-negative scalar proportional to the particle's likelihood.
            The filter will normalize these weights across particles before
            resampling.
        """


class WeightEstimatorGaussian(WeightEstimatorInterface):
    """
    Gaussian likelihood weight estimator.

    The weight is computed as the product of per-measurement Gaussian
    likelihoods assuming i.i.d. errors. A crude bias estimate (the mean
    of the pre-fits) is removed before evaluating the likelihood.

    Notes
    -----
    The resulting product can suffer from numerical underflow for long
    measurement vectors. In practical applications a log-likelihood sum
    is preferred; this implementation trades numerical robustness for
    simplicity.
    """

    def __init__(self):
        pass

    def compute(self, prefits: np.ndarray, **kwargs) -> float:
        r"""Compute a Gaussian product likelihood weight.

            Parameters
            ----------
            prefits : numpy.ndarray
                Vector of pre-fit residuals. A constant bias term is estimated
                and removed before computing the likelihood.

            Returns
            -------
            float
                Product of per-measurement Gaussian likelihoods.

            Math
            ----
            The weight corresponds to

              .. math::
                  w = \prod_{i=1}^{N} \frac{1}{\sigma \sqrt{2\pi}} \exp\left(-\tfrac{1}{2}\left(\tfrac{x_i-\mu}{\sigma}\right)^2\right)

        where :math:`x_i` are the bias-corrected pre-fits and :math:`\mu,\sigma`
            are respectively the sample mean and standard deviation of the original
            pre-fits.
        """

        # Rough estimation of the hardware bias to remove it from the measurements
        bias = np.average(prefits)
        std = np.std(prefits)

        # Use Gaussian PDF with mean=bias and sigma=std
        likelihoods = gaussian(prefits, bias, std)

        weight = np.prod(likelihoods)

        return weight


class Filter(FilterInterface):
    """Simple particle filter (sequential Monte Carlo).

    The ``Filter`` implements a basic particle filter algorithm that relies on
    a user-supplied ``Model`` to propagate states and synthesize expected
    observations, a ``WeightEstimatorInterface`` to convert residuals into
    likelihood weights, and a ``StateHandler`` to consume the selected state
    estimate at each epoch.

    The class performs the standard steps each epoch: propagate particles,
    compute weights from pre-fit residuals, normalize weights, optionally
    resample, apply a configurable post-resample roughening noise, and
    forward the chosen state to the handler.

    The constructor accepts several optional hooks to customize resampling
    and roughening behavior; see ``__init__`` for parameter details.
    """

    def __init__(
        self,
        initial_states: List[State],
        weight_estimator: WeightEstimatorInterface,
        model: Model,
        state_handler: StateHandler,
        resample_threshold: Optional[float] = None,
        resample_function: ResampleFunctionSignature = multinomial_resample,
        particle_callback: ParticleCallbackSignature = void_particle_callback,
        roughening_std: Optional[List[float]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Create a Filter instance.

        Parameters
        ----------
        initial_states : list[State] or numpy.ndarray
            Initial particle set. Can be a list of state arrays or an ndarray
            with shape (N, state_dim). The constructor will convert an
            ndarray into a list of per-particle arrays.
        weight_estimator : WeightEstimatorInterface or type
            Either an instance implementing ``WeightEstimatorInterface`` or
            the class (e.g., ``WeightEstimatorGaussian``). If a class is
            provided the ctor will instantiate it.
        model : Model
            System model providing ``propagate_state`` and ``to_observations``.
        state_handler : StateHandler
            Consumer of the selected state estimate via
            ``state_handler.process_state``.
        resample_threshold : float | None, optional
            If provided, resampling will be triggered when the effective
            sample size falls below ``resample_threshold * n_particles``.
            If ``None`` (default) resampling is performed every epoch.
        resample_function : callable, optional
            Resampling function implementing the ``ResampleFunctionSignature``.
            Defaults to ``multinomial_resample``.
        particle_callback : callable, optional
            Callback invoked after weight normalization with signature
            ``(particles, weights)`` for visualization or diagnostics.
        roughening_std : list[float] | None, optional
            If provided, a per-state-dimension standard-deviation vector used
            to add zero-mean Gaussian noise to particles after resampling.
            Its length must match the state dimension. If ``None`` no
            roughening is applied.
        logger : logging.Logger | None, optional
            Logger for debug/tracing messages. If ``None`` the module logger
            is used.

        Notes
        -----
        The constructor accepts either a ``WeightEstimator`` instance or the
        class and will instantiate the latter for backward compatibility.
        """

        self.particles = initial_states

        self.weight_estimator = weight_estimator
        self.model = model
        self.state_handler = state_handler
        self._resample_threshold = resample_threshold
        self._resample: ResampleFunctionSignature = resample_function
        self._particle_callback: ParticleCallbackSignature = particle_callback
        self._roughening_std = roughening_std
        self.logger = logger or logging.getLogger(__name__)

        # Initial set of weights for the particles. Assuming equally weighted
        n_particles = len(self.particles)
        self.weights = np.array([1.0 / n_particles] * n_particles)

        # Check that the roughening std is compatible with the state dimension
        if self._roughening_std is not None:
            state_dim = len(self.particles[0])
            if len(self._roughening_std) != state_dim:
                raise ValueError(
                    f"Roughening std length {len(self._roughening_std)} does not match "
                    f"state dimension {state_dim}."
                )

    def process(self, y_k: np.ndarray, R: np.ndarray, **kwargs):
        """Process one epoch: propagate, weight, resample, roughen, and report.

        Performs the sequential Monte Carlo steps for a single observation
        epoch:

        1. Propagate particles using ``model.propagate_state`` (time update).
        2. Compute pre-fit residuals and map them to weights using
           ``weight_estimator.compute``.
        3. Normalize weights and invoke ``particle_callback`` for monitoring
           or visualization.
        4. Resample particles when needed and apply post-resample roughening
           noise (if configured) to mitigate sample impoverishment.
        5. Compute the selected state estimate and forward it to
           ``state_handler.process_state`` along with diagnostics.

        Parameters
        ----------
        y_k : numpy.ndarray
            Observation vector at the current epoch.
        R : numpy.ndarray
            Measurement noise covariance matrix (forwarded via ``**kwargs``
            to estimators that may need it).
        **kwargs : dict
            Additional keyword arguments forwarded to ``model.to_observations``
            and to ``weight_estimator.compute``.

        Notes
        -----
        The method updates ``self.particles`` and ``self.weights`` in-place
        (resampling replaces the particle set). The selected state that is
        passed to ``state_handler`` is produced by ``_get_solution`` (by
        default the maximum-weight particle).
        """

        # Time update ----------------------------------------------------------
        particles = [
            self.model.propagate_state(particle) for particle in self.particles
        ]

        for i, particle in enumerate(particles):
            prefits = y_k - self.model.to_observations(particle).y_m
            self.weights[i] = self.weight_estimator.compute(prefits, **kwargs)

        # Normalize the weights
        self.weights = self.weights / sum(self.weights)

        self._particle_callback(particles, self.weights, **kwargs)

        # Commit the propagated particle set before resampling
        # Resampling only if the effective number of particles is low (Algorithm 3 of
        # https://pmc.ncbi.nlm.nih.gov/articles/PMC7826670/pdf/sensors-21-00438.pdf)
        if self._needs_resample(self.weights):
            self.particles, self.weights = self._resample(
                particles, self.weights, len(particles)
            )

        # Perform particle "roughening" if need be
        n_particles = len(self.particles)
        noise = np.zeros((n_particles, len(self.particles[0])))

        if self._roughening_std is not None:
            for dim in range(len(self.particles[0])):
                noise[:, dim] = np.random.normal(
                    0.0, self._roughening_std[dim], size=(n_particles,)
                )

        self.particles = self.particles + noise

        # Compute postfit residuals
        x = self._get_solution()

        r = y_k - self.model.to_observations(x, **kwargs).y_m

        self.state_handler.process_state(x, np.eye(len(x)), postfits=r, **kwargs)

    def _needs_resample(self, weights: np.ndarray) -> bool:
        """Determine if resampling is needed based on the effective number of particles.

        Parameters
        ----------
        weights : numpy.ndarray
            Array of particle weights.
        threshold : float
            Resampling threshold as a fraction of the total number of particles.
            Default is 0.25.
        Returns
        -------
        bool
            True if resampling is needed, False otherwise.
        """

        if self._resample_threshold is None:
            return True

        else:
            n_particles = len(weights)
            effective_n = 1.0 / np.sum(np.square(weights))
            return effective_n < self._resample_threshold * n_particles

    def _get_solution(self) -> State:
        """Return the current state estimate from the particle set.

        The default implementation returns the maximum-weight particle.
        Alternative selection strategies can be implemented if needed.

        Returns
        -------
        State
            The selected state estimate.
        """

        return self.particles[np.argmax(self.weights)]


def gaussian(x, mu, sigma):
    """
    Evaluates a Gaussian function (normal distribution).

    :param x: The input value(s) (scalar or NumPy array).
    :type x: float or numpy.ndarray
    :param mu: The mean (center) of the Gaussian.
    :type mu: float
    :param sigma: The standard deviation (width) of the Gaussian.
    :type sigma: float
    :return: The value(s) of the Gaussian function at x.
    :rtype: float or numpy.ndarray

    Example
    -------
    >>> import numpy as np
    >>> mean = 0
    >>> std_dev = 1
    >>> x_values = np.linspace(-3, 3, 100)
    >>> y_values = gaussian(x_values, mean, std_dev)
    >>> print(y_values[0:5])
    [0.00443185 0.00530579 0.00632878 0.00752133 0.00890582]
    """
    return (1.0 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma) ** 2)
