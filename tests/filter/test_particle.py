import numpy as np

from pygnss.filter import particle, models, StateHandler


def test__particle_filter_simple():
    """Simple smoke test for the particle filter using a small 2D range model.

    This avoids external dataset dependencies by creating a synthetic set of
    nodes and a single observation epoch.
    """

    n_particles = 100
    # Simple 2D beacons
    nodes = np.array([[0.0, 0.0], [0.0, 10.0], [10.0, 0.0]])

    # Initialize particles spread over a region covering the nodes
    particles = np.random.uniform(low=[-5.0, -5.0], high=[15.0, 15.0], size=(n_particles, 2))

    # Use a WeightEstimator instance (the Filter currently expects an
    # instantiated estimator object).
    weight_estimator = particle.WeightEstimatorGaussian()

    model = models.RangePositioning2D(np.eye(2), nodes)

    class LocalHandler(StateHandler):
        def process_state(self, state: np.array, _covariance_matrix: np.array, **kwargs):
            # basic sanity check: state has the expected dimension
            assert np.asarray(state).shape == (2,)

    handler = LocalHandler()

    pf = particle.Filter(particles, weight_estimator, model, handler)

    # True state and its range observations
    true_state = np.array([2.0, 1.0])
    y_k = model.to_observations(true_state)[0]
    R = np.eye(len(y_k)) * 0.5

    # Run one filter step (should call handler.process_state)
    pf.process(y_k, R)

    # Ensure particle set still has the same number of particles
    assert len(pf.particles) == n_particles


