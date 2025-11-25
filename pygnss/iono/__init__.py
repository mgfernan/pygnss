import numpy as np


def compute_pierce_point(receiver_ecef, sat_ecef, iono_height_m=350000.0):
    """
    Compute the ionospheric pierce point given receiver and satellite positions.

    Parameters:
    receiver_ecef : array-like
        ECEF coordinates of the receiver (x, y, z) in meters.
    sat_ecef : array-like
        ECEF coordinates of the satellite (x, y, z) in meters.
    iono_height_m : float
        Height of the ionospheric shell in meters.

    Returns:
    pierce_point_ecef : array-like
        ECEF coordinates of the pierce point (x, y, z) in meters.

    >>> receiver_ecef = [0, 0, 6470000.0]
    >>> sat_ecef = [0.0, 0.0, 20000000.0]
    >>> pierce_point = compute_pierce_point(receiver_ecef, sat_ecef)
    >>> np.round(pierce_point, 3)
    array([      0.  ,       0.  , 6829466.77])
    """

    receiver_ecef = np.array(receiver_ecef)
    sat_ecef = np.array(sat_ecef)

    # Vector from receiver to satellite
    rho = sat_ecef - receiver_ecef
    rho_norm = np.linalg.norm(rho)

    # Unit vector in the direction from receiver to satellite
    rho_unit = rho / rho_norm

    # Compute the distance from the Earth's center to the pierce point
    r_receiver = np.linalg.norm(receiver_ecef)
    r_iono = r_receiver + iono_height_m

    # Compute the distance along the line of sight to the pierce point
    d = (r_iono**2 - r_receiver**2) / (2.0 * np.dot(receiver_ecef, rho_unit))

    # Compute the pierce point coordinates
    pierce_point_ecef = receiver_ecef + d * rho_unit

    return pierce_point_ecef