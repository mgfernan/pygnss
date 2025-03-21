import datetime
import math
from typing import List

import numpy as np

import nequick


class GimIonexHandler(nequick.GimHandler):
    """
    A handler that accumulates GIMs and then generates an IONEX file
    """

    def __init__(self, coeffs: nequick.Coefficients):
        self._coeffs = coeffs
        self._gims: List[nequick.gim.Gim] = []

    def process(self, gim: nequick.Gim):
        """
        Store the incoming gim for later process
        """

        # Check that the latitude and longitude values are
        # the same as the last appended gim
        if len(self._gims) > 0:
            last_gim = self._gims[-1]
            if np.array_equal(last_gim.latitudes, gim.latitudes) == False:
                raise ValueError("Latitude values do not match")
            if np.array_equal(last_gim.longitudes, gim.longitudes) == False:
                raise ValueError("Longitude values do not match")

        self._gims.append(gim)

    def to_ionex(self, pgm: str = "pygnss", runby: str = "pygnss") -> str:

        EXPONENT = -1

        # Sort the IONEX files by epoch
        self._gims.sort(key=lambda gim: gim.epoch)

        first_epoch = self._gims[0].epoch
        last_epoch = self._gims[-1].epoch
        n_maps = len(self._gims)

        lat_0 = self._gims[0].latitudes[0]
        lat_1 = self._gims[0].latitudes[-1]
        dlat = self._gims[0].latitudes[1] - self._gims[0].latitudes[0]

        # We will print the map from North to South, therefore check if the
        # latitudes need to be reversed
        latitude_reversal = lat_0 < lat_1
        if latitude_reversal:
            lat_0 = self._gims[0].latitudes[-1]
            lat_1 = self._gims[0].latitudes[0]
            dlat = self._gims[0].latitudes[0] - self._gims[0].latitudes[1]

        lon_0 = self._gims[0].longitudes[0]
        lon_1 = self._gims[0].longitudes[-1]
        dlon = self._gims[0].longitudes[1] - self._gims[0].longitudes[0]

        doc = ""

        # Header
        today = datetime.datetime.now()
        epoch_str = today.strftime('%d-%b-%y %H:%M')

        doc +="     1.0            IONOSPHERE MAPS     NEQUICK             IONEX VERSION / TYPE\n"
        doc +=f"{pgm[:20]:<20}{runby[:20]:<20}{epoch_str[:20]:<20}PGM / RUN BY / DATE\n"
        doc +="Maps computed using the NeQuick model with the following    COMMENT\n"
        doc +="coefficients:                                               COMMENT\n"
        doc += f"{EXPONENT:>6}                                                      EXPONENT\n"
        doc +=f"a0={self._coeffs.a0:<17.6f}a1={self._coeffs.a1:<17.8f}a2={self._coeffs.a2:<17.11f}COMMENT\n"
        doc += first_epoch.strftime("  %Y    %m    %d    %H    %M    %S                        EPOCH OF FIRST MAP\n")
        doc += last_epoch.strftime("  %Y    %m    %d    %H    %M    %S                        EPOCH OF LAST MAP\n")
        doc += "     0                                                      INTERVAL\n"
        doc += f"{n_maps:>6}                                                      # OF MAPS IN FILE\n"
        doc += "  NONE                                                      MAPPING FUNCTION\n"
        doc += "     0.0                                                    ELEVATION CUTOFF\n"
        doc += "                                                            OBSERVABLES USED\n"
        doc += "  6371.0                                                    BASE RADIUS\n"
        doc += "     2                                                      MAP DIMENSION\n"
        doc += "   450.0 450.0   0.0                                        HGT1 / HGT2 / DHGT\n"
        doc += f"  {lat_0:6.1f}{lat_1:6.1f}{dlat:6.1f}                                        LAT1 / LAT2 / DLAT\n"
        doc += f"  {lon_0:6.1f}{lon_1:6.1f}{dlon:6.1f}                                        LON1 / LON2 / DLON\n"
        doc += "                                                            END OF HEADER\n"

        # Body: For each GIM file, write the VTEC values
        for i, gim in enumerate(self._gims):

            doc += f"{i+1:>6}                                                      START OF TEC MAP\n"
            doc += gim.epoch.strftime("  %Y    %m    %d    %H    %M    %S                        EPOCH OF CURRENT MAP\n")

            n_latitudes = len(gim.latitudes)

            for i_lat, lat in enumerate(gim.latitudes):

                if latitude_reversal:
                    i_lat = n_latitudes - 1 - i_lat

                lat = gim.latitudes[i_lat]
                doc += f"  {lat:6.1f}{lon_0:6.1f}{lon_1:6.1f}{dlon:6.1f} 450.0                            LAT/LON1/LON2/DLON/H"

                lat_row = gim.vtec_values[i_lat]
                for i_lon, _ in enumerate(gim.longitudes):

                    if i_lon % 16 == 0:
                        doc += "\n"

                    vtec = lat_row[i_lon] / math.pow(10, EXPONENT)
                    doc += f"{int(vtec):>5d}"

                doc += "\n"

            doc += f"{i+1:>6}                                                      END OF TEC MAP\n"

        # Tail
        doc += "                                                            END OF FILE\n"

        return doc

def to_ionex(coeffs: nequick.Coefficients, dates: List[datetime.datetime]) -> str:

    doc = None

    gim_handler = GimIonexHandler(coeffs)

    for date in dates:
        nequick.to_gim(coeffs, date, gim_handler=gim_handler)

    doc = gim_handler.to_ionex()

    return doc