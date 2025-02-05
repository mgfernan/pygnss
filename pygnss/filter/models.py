import numpy as np

from . import Model, ModelObs


class RangePositioning2D(Model):
    """
    Basic 2D range-based positioning model
    """

    def __init__(self, Phi: np.array, nodes: np.array):
        """
        Instantiate a RangePositioning2D

        :param Phi: a 2 x 2 matrix that propagates the state from k-1 to k
        :param nodes: list of nodes of the positioning system, from which the
        range will be computed
        """
        self._Phi = Phi
        self.nodes = nodes

    def propagate_state(self, state: np.array):
        """
        Propagate the state from k-1 to k

        >>> Phi = np.eye(2)
        >>> nodes = np.array([[0, 0], [0, 10], [10, 0]])
        >>> model = RangePositioning2D(Phi, nodes)
        >>> state_m = np.array([1, 2])
        >>> model.propagate_state(state_m)
        array([1., 2.])
        """

        return np.dot(self._Phi, state)

    def to_observations(self, state: np.array, compute_jacobian: bool = False) -> ModelObs:
        """
        Convert the state into observations using a range based 2D positioning model

        >>> Phi = np.eye(2)
        >>> nodes = np.array([[0, 0], [0, 10], [10, 0]])
        >>> model = RangePositioning2D(Phi, nodes)
        >>> state_m = np.array([1, 2])
        >>> model.to_observations(state_m)
        (array([2.23606798, 8.06225775, 9.21954446]), None)

        >>> model.to_observations(state_m, compute_jacobian=True)
        (array([2.23606798, 8.06225775, 9.21954446]), array([[ 0.4472136 ,  0.89442719],
               [ 0.12403473, -0.99227788],
               [-0.97618706,  0.21693046]]))
        """
        rho = state - self.nodes
        ranges = np.sqrt(np.sum(np.power(rho, 2), axis=1))

        H = None

        if compute_jacobian is True:
            H = rho / ranges[:, np.newaxis]

        return ranges, H

    def Phi(self):
        """
        Get the state transition matrix

        >>> Phi = np.eye(2)
        >>> nodes = np.array([[0, 0], [0, 10], [10, 0]])
        >>> model = RangePositioning2D(Phi, nodes)
        >>> model.Phi()
        array([[1., 0.],
               [0., 1.]])
        """
        return self._Phi
