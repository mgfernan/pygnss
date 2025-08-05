"""
Module to compute the Chapman ionospheric model.

This module provides functions to compute the Chapman ionospheric model,
which is used to estimate the electron density in the ionosphere based on
solar zenith angle and other parameters.
"""

import numpy as np

HEIGHTS_KM = np.arange(60, 1000, 10)

def compute_profile(hmF2_km: float, NmF2: float, H_km: float, zenith_angle_deg: float, heights_km: float | np.ndarray =HEIGHTS_KM) -> float | np.ndarray:
    """
    Compute the Chapman ionospheric model.

    Parameters:
    zenith_angle (float or np.ndarray): Solar zenith angle, the angle between the vertical and the direction to the Sun.
    hmF2_km (float): Height of the F2 layer in kilometers.
    NmF2 (float): Peak electron density at hmF2 in electrons/m^3.
    H_km (float): Scale height in kilometers (typical values between 30 and 50 km).
    heights_km (np.ndarray, optional): Heights at which to compute the electron density.
        If None, defaults to a range from 0 to 100 km.

    Returns:
    float or np.ndarray: Computed electron density based on the Chapman model.
    """
    # Convert zenith angle from degrees to radians
    zenith_angle_rad = np.radians(zenith_angle_deg)

    # Include scale height
    z = (heights_km - hmF2_km) / H_km

    # Compute the Chapman function
    return NmF2 * np.exp( 0.5 * (1 - z - np.exp(-z) / np.cos(zenith_angle_rad)))
