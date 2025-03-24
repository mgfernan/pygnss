import argparse
import datetime
import math
import os
from typing import List

import nequick
import numpy as np


from .iono import gim
from .decorator import read_contents


def load(filename: str,  gim_handler: gim.GimHandler):
    """
    Load an IONEX file and process its contents using the provided GIM handler.

    :param filename: The path to the IONEX file to load.
    :param gim_handler: An instance of a GIM handler to process the GIMs read from the file.
    :return: The result of processing the IONEX file.
    """

    return _load(filename, gim_handler)


def write(filename: str, gims: List[gim.Gim], gim_type: gim.GimType,
          pgm: str = "pygnss", runby: str = "pygnss", comment_lines: List[str] = []) -> None:
    """
    Write a list of GIMs to an IONEX file.

    :param filename: The path to the IONEX file to write.
    :param gims: A list of GIM objects to write to the file.
    """

    EXPONENT = -1
    FACTOR = math.pow(10, EXPONENT)

    if not gims:
        raise ValueError("The list of GIMs is empty. Cannot write to the IONEX file.")

    # Extract latitudes and longitudes from the first GIM
    latitudes = gims[0].latitudes
    longitudes = gims[0].longitudes

    lon1 = longitudes[0]
    lon2 = longitudes[-1]
    dlon = longitudes[1] - longitudes[0]

    # Ensure all GIMs have the same latitudes and longitudes
    for gim_obj in gims:
        if np.array_equal(gim_obj.latitudes, latitudes) == False or \
           np.array_equal(gim_obj.longitudes, longitudes) == False:
            raise ValueError("All GIMs must have the same latitudes and longitudes.")

    # Sort the IONEX files by epoch
    gims.sort(key=lambda gim: gim.epoch)

    first_epoch = gims[0].epoch
    last_epoch = gims[-1].epoch
    n_maps = len(gims)

    lat_0 = gims[0].latitudes[0]
    lat_1 = gims[0].latitudes[-1]
    dlat = gims[0].latitudes[1] - gims[0].latitudes[0]

    # We will print the map from North to South, therefore check if the
    # latitudes need to be reversed
    latitude_reversal = lat_0 < lat_1
    if latitude_reversal:
        lat_0 = gims[0].latitudes[-1]
        lat_1 = gims[0].latitudes[0]
        dlat = gims[0].latitudes[0] - gims[0].latitudes[1]

    lon_0 = gims[0].longitudes[0]
    lon_1 = gims[0].longitudes[-1]
    dlon = gims[0].longitudes[1] - gims[0].longitudes[0]

    doc = ""

    # Header
    today = datetime.datetime.now()
    epoch_str = today.strftime('%d-%b-%y %H:%M')

    doc +="     1.0            IONOSPHERE MAPS     NEQUICK             IONEX VERSION / TYPE\n"
    doc +=f"{pgm[:20]:<20}{runby[:20]:<20}{epoch_str[:20]:<20}PGM / RUN BY / DATE\n"

    for comment_line in comment_lines:
        doc += f"{comment_line[:60]:<60}COMMENT\n"

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
    doc += f"{EXPONENT:>6}                                                      EXPONENT\n"
    doc += "                                                            END OF HEADER\n"

    # Write each GIM
    for i_map, gim_obj in enumerate(gims):

        doc += f"{i_map+1:>6}                                                      START OF {gim_type.name} MAP\n"

        # Write the epoch
        epoch = gim_obj.epoch
        doc += epoch.strftime("  %Y    %m    %d    %H    %M    %S                        EPOCH OF CURRENT MAP\n")


        for i, _ in enumerate(latitudes):

            if latitude_reversal:
                i = len(latitudes) - 1 - i

            lat = latitudes[i]

            doc += f"  {lat:6.1f}{lon1:6.1f}{lon2:6.1f}{dlon:6.1f} 450.0                            LAT/LON1/LON2/DLON/H\n"

            lat_row = gim_obj.vtec_values[i]
            for j in range(0, len(longitudes), 16):
                doc += "".join(f"{round(vtec / FACTOR):5d}" for vtec in lat_row[j:j+16]) + "\n"

        doc += f"{i_map+1:>6}                                                      END OF {gim_type.name} MAP\n"

    # Tail
    doc += "                                                            END OF FILE\n"

    with open(filename, "wt") as fh:
        fh.write(doc)



def diff(filename_lhs: str, filename_rhs: str, output_file: str, pgm="pygnss.ionex") -> None:
    """
    Compute the difference between two IONEX files and write the result in IONEX format
    """

    gim_handler_lhs = gim.GimHandlerArray()
    gim_handler_rhs = gim.GimHandlerArray()

    load(filename_lhs, gim_handler=gim_handler_lhs)
    load(filename_rhs, gim_handler=gim_handler_rhs)

    gim_diffs = gim.subtract_gims(gim_handler_lhs.vtec_gims, gim_handler_rhs.vtec_gims)

    comment_lines = [
        "This IONEX file contains the differences of VTEC values,",
        "computed as vtec_left - vtec_right, where:",
        f"- vtec_left: {os.path.basename(filename_lhs)}",
        f"- vtec_right: {os.path.basename(filename_rhs)}",
    ]

    write(output_file, gim_diffs, gim.GimType.TEC, pgm=pgm, comment_lines=comment_lines)


@read_contents
def _load(doc: str, gim_handler: gim.GimHandler):
    """
    Parse the contents of an IONEX file and process each GIM using the provided handler.

    :param doc: The contents of the IONEX file as a string.
    :param gim_handler: An instance of a GIM handler to process the GIMs read from the file.
    :raises ValueError: If the file is not a valid IONEX file or contains unsupported features.
    """

    lines = doc.splitlines()
    n_lines = len(lines)
    i_body = 0

    latitudes_deg: List[float] = []
    longitudes_deg: List[float] = []

    header_mark_found = False

    # Header
    for i in range(n_lines):

        line = lines[i]

        if line[60:].startswith('IONEX VERSION / TYPE'):
            header_mark_found = True

        elif line[60:].startswith('HGT1 / HGT2 / DHGT'):
            _hgt1, _hgt2, _dhgt = [float(v) for v in line.split()[:3]]
            if _dhgt != 0.0:
                raise ValueError('Multi-layer Ionex files not supported')

        elif line[60:].startswith('LAT1 / LAT2 / DLAT'):
            _lat1, _lat2, _dlat = [float(v) for v in line.split()[:3]]
            latitudes_deg = np.arange(_lat1, _lat2 + _dlat/2, _dlat)

        elif line[60:].startswith('LON1 / LON2 / DLON'):
            _lon1, _lon2, _dlon = [float(v) for v in line.split()[:3]]
            longitudes_deg = np.arange(_lon1, _lon2 + _dlon/2, _dlon)

        elif line[60:].startswith('EXPONENT'):
            exponent: float = float(line[:6])

        elif line[60:].startswith('END OF HEADER'):
            i_body = i + 1
            break

    if header_mark_found is False:
        raise ValueError(f'The input does not seem to be a IONEX file [ {doc[:10]} ]')

    n_lines_lat_row = int(np.ceil(len(longitudes_deg) / 16))

    current_gim = None
    gim_type = None

    # Body
    for i in range(i_body, n_lines):

        line = lines[i]

        if line[60:].startswith('START OF TEC MAP'):

            i_lat_row = 0

            gim_type = gim.GimType.TEC

        elif line[60:].startswith('START OF RMS MAP'):

            i_lat_row = 0

            gim_type = gim.GimType.RMS

        elif line[60:].startswith('EPOCH OF CURRENT MAP'):

            # Initialize map
            current_gim = gim.Gim(_parse_ionex_epoch(line),
                                  longitudes_deg, latitudes_deg,
                                  [[0] * len(longitudes_deg)] * len(latitudes_deg))

        elif line[60:].startswith('LAT/LON1/LON2/DLON/H'):

            lat_row = ''.join([lines[i + 1 + j] for j in range(n_lines_lat_row)])

            values = np.array([float(v) for v in lat_row.split()])

            i += n_lines_lat_row

            current_gim.vtec_values[i_lat_row] = (values * np.power(10, exponent)).tolist()

            i_lat_row = i_lat_row + 1

        # If end of map reached, send them to appropriate processor
        elif line[60:].startswith('END OF TEC MAP') or line[60:].startswith('END OF RMS MAP'):
            gim_handler.process(current_gim, gim_type)


def _parse_ionex_epoch(ionex_line: str) -> datetime.datetime:
    """
    Parse the epoch from a IONEX line

    >>> _parse_ionex_epoch("  2024    12    11     0     0    14                        EPOCH OF FIRST MAP")
    datetime.datetime(2024, 12, 11, 0, 0, 14)
    >>> _parse_ionex_epoch("  2024    12    11     0     0     0                        EPOCH OF CURRENT MAP")
    datetime.datetime(2024, 12, 11, 0, 0)
    """

    _HEADER_EPOCH_FORMAT = "  %Y    %m    %d    %H    %M    %S"

    return datetime.datetime.strptime(ionex_line[:36], _HEADER_EPOCH_FORMAT)



class NeQuickGimHandlerArray(gim.GimHandler):
    """
    Handler to store the incoming GIMs in arrays
    """

    def __init__(self):
        self.vtec_gims: List[gim.Gim] = []

    def process(self, nequick_gim: nequick.Gim):
        """
        Process a GIM file
        """

        incoming_gim = gim.Gim(nequick_gim.epoch,
                               nequick_gim.longitudes, nequick_gim.latitudes,
                               nequick_gim.vtec_values)

        self.vtec_gims.append(incoming_gim)


def cli():
    """
    This function allows users to compute the difference between two IONEX files
    or between an IONEX file and the NeQuick model (with three coefficients),
    and save the result in a new IONEX file.


    Example:
        Compute the difference between two IONEX files:
        $ python ionex.py file1.ionex file2.ionex output.ionex

        Compute the difference between an IONEX file and the NeQuick model:
        $ python ionex.py file1.ionex output.ionex --nequick 0.123 0.456 0.789
    """
    parser = argparse.ArgumentParser(description=cli.__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter )

    parser.add_argument(
        "lhs",
        type=str,
        help="Path to the first IONEX file (left-hand side).",
    )

    parser.add_argument(
        "output",
        type=str,
        help="Path to the output IONEX file where the differences will be saved.",
    )

    rhs = parser.add_mutually_exclusive_group(required=True)

    rhs.add_argument(
        "--rhs",
        type=str,
        help="Path to the second IONEX file (right-hand side). If not provided, --nequick must be specified.",
    )

    rhs.add_argument(
        "--nequick",
        type=float,
        nargs=3,
        metavar=("AZ0", "AZ1", "AZ2"),
        help="Use the NeQuick model to compare against the 'lhs' IONEX (instead of another IONEX file). "
        "Specify the three NeQuick coefficients (az0, az1, az2).",
    )

    parser.add_argument(
        "--nequick-ionex",
        type=str,
        default=None,
        required=False,
        metavar='<file>',
        help="Specify a filename to store the NeQuick model in IONEX format",
    )

    args = parser.parse_args()

    PGM = "ionex_diff"

    # Validate input arguments
    if args.rhs is None and args.nequick is None:
        parser.error("Either a second IONEX file (rhs) or the '--nequick' option must be provided.")

    if args.rhs is not None and args.nequick is not None:
        parser.error("You cannot specify both a second IONEX file (rhs) and the '--nequick' option.")

    if args.nequick_ionex is not None and args.nequick is None:
        parser.error("Cannot output the IONEX file with the NeQuick model without the '--nequick' option.")

    # Process the lhs IONEX file
    gim_handler_lhs = gim.GimHandlerArray()
    load(args.lhs, gim_handler=gim_handler_lhs)

    # Add comments to the output file
    comment_lines = [
        "This IONEX file contains the differences of VTEC values,",
        "computed as vtec_left - vtec_right, where:",
        f"- vtec_left: {os.path.basename(args.lhs)}"
    ]

    # Process the rhs input (either an IONEX file or NeQuick coefficients)
    gim_handler_rhs = None
    if args.rhs:
        gim_handler_rhs = gim.GimHandlerArray()
        # Load the second IONEX file
        load(args.rhs, gim_handler=gim_handler_rhs)
        comment_lines += [f"- vtec_right: {os.path.basename(args.rhs)}"]

    else:
        gim_handler_rhs = NeQuickGimHandlerArray()
        # Generate GIMs using NeQuick coefficients
        coeffs = args.nequick
        nequick_desc = ["NeQuick model", f"   az0={coeffs[0]}", f"   az1={coeffs[1]}", f"   az2={coeffs[2]}"]
        comment_lines += [f"- vtec_right: {nequick_desc[0]}"] + nequick_desc[1:]

        for ionex_gim in gim_handler_lhs.vtec_gims:

            nequick.to_gim(nequick.Coefficients(*coeffs),
                           ionex_gim.epoch,
                           latitudes = ionex_gim.latitudes,
                           longitudes = ionex_gim.longitudes,
                           gim_handler= gim_handler_rhs)

    # Compute the difference
    gim_diffs = gim.subtract_gims(gim_handler_lhs.vtec_gims, gim_handler_rhs.vtec_gims)


    # Write the result to the output file
    write(args.output, gim_diffs, gim.GimType.TEC, pgm=PGM, comment_lines=comment_lines)

    if args.nequick_ionex is not None:
        comment_lines = [
            "TEC values generated with the " + nequick_desc[0]
        ] + nequick_desc[1:]

        write(args.nequick_ionex, gim_handler_lhs.vtec_gims, gim.GimType.TEC, pgm=PGM,
              comment_lines=comment_lines )
