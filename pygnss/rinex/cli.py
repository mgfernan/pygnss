import argparse
import numpy as np
import pandas as pd
from typing import List
import sys


from ..orbit.tle import read_celestrak
from .clock import GnssRandomClock, LEOCodeBiases, ZeroClockModel, ZeroCodeBiases
from .defs import RANDOM_STR, ZERO_STR
from .nav import Nav, merge_nav
from .obs import to_dataframe


def merge_nav_cli():

    parser = argparse.ArgumentParser(description="Tool to merge various RINEX 4 files",
                                     formatter_class=argparse.RawDescriptionHelpFormatter)  # for verbatim

    parser.add_argument('files', metavar='FILE', type=str, nargs='+', help='input RINEX4 file(s)')

    args = parser.parse_args()

    merged_rinex_str = merge_nav(args.files)

    sys.stdout.write(merged_rinex_str)


def rinex_from_file():

    parser = argparse.ArgumentParser(description="Tool to convert an input file to RINEX navigation file",
                                     formatter_class=argparse.RawDescriptionHelpFormatter)  # for verbatim

    # Define the mutually exclusive group
    input_options = parser.add_mutually_exclusive_group(required=True)

    input_options.add_argument('--celestrak_file', metavar='<filename>', type=str,
                               help='File from Celestrak with the TLE elements to convert to RINEX.' +
                                    'Based on https://arxiv.org/abs/2401.17767')

    input_options.add_argument('--csv', metavar='<filename>', type=str,
                               help='CSV file with the description of ')

    parser.add_argument('--clock-model', '-c', choices=[ZERO_STR, RANDOM_STR], required=False,
                        help="Choose the clock model to be applied to satellites where clock \
                            bias and drift has not been provided. Defaults to '{ZERO_STR}'")

    parser.add_argument('--rinex2', action='store_true',
                        help='Output the format in Rinex 2 GPS format. Will skip satellites \
                            with PRN larger than 99')

    # Parse the command-line arguments
    args = parser.parse_args()

    sat_clock_model = ZeroClockModel()
    if args.clock_model == RANDOM_STR:
        sat_clock_model = GnssRandomClock()

    code_biases = ZeroCodeBiases()
    if args.code_biases == RANDOM_STR:
        TGD_MAX_S = 10.0e-9
        tgd_s = np.random.uniform(low=-TGD_MAX_S, high=TGD_MAX_S)
        isc_s9c_s = np.random.uniform(low=-TGD_MAX_S, high=TGD_MAX_S)
        code_biases = LEOCodeBiases(tgd_s, isc_s9c_s)

    if args.celestrak_file:
        tle_list = read_celestrak(args.celestrak_file)
        Nav.write_from_tle(sys.stdout, tle_list, rinex2=args.rinex2, sat_clock_model=sat_clock_model, code_biases=code_biases)

    elif args.csv:
        df = pd.read_csv(args.csv, parse_dates=['epoch'])
        Nav.write_from_dataframe(sys.stdout, df, rinex2=args.rinex2, sat_clock_model=sat_clock_model, code_biases=code_biases)

def to_parquet(rinex_files:List[str], output_filename:str, station_name:str = None):
    """
    Convert a list of RINEX files into a parquet file
    """

    if output_filename is None:
        output_filename = rinex_files[0] + '.parquet'

    dfs = []

    for rinex_file in rinex_files:
        df = to_dataframe(rinex_file, station_name=station_name)
        dfs.append(df)

    df = pd.concat(dfs)

    df.to_parquet(output_filename)


def rinex_to_parquet():

    parser = argparse.ArgumentParser(description="Tool to convert an observable RINEX file to parquet file",
                                     formatter_class=argparse.RawDescriptionHelpFormatter)  # for verbatim

    parser.add_argument('rinex_files', metavar='N', type=str, nargs='+',
                   help='rinex file(s) to convert to a single parquet file')

    parser.add_argument('-o',  '--output', type=str, help="output parquet file name. If not provided, the first file ended with the 'parquet' extension will be used")
    parser.add_argument('-n',  '--name', type=str, help="Station name to be included in the parquet file. If not provided, will nbe inferred from the RINEX file")

    # Parse the command-line arguments
    args = parser.parse_args()

    to_parquet(args.rinex_files, output_filename=args.output, station_name=args.name)
