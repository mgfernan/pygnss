import datetime
import doctest
import os
import subprocess
from io import StringIO
import tempfile

import numpy as np
import pandas as pd

from pygnss.orbit.tle import read_celestrak
import pygnss.rinex as rnx


def test__read_rinex_nav():
    """Rinex :: Read Rinex NAVs with LEO block """

    doc = """     4.99           NAVIGATION DATA     M                   RINEX VERSION / TYPE
rinex_from_file     rokubun             20240222 055117 UTC PGM / RUN BY / DATE
    18                                                      LEAP SECONDS
                                                            END OF HEADER
> EPH X40044
    2024 02 17 10 33 35 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 3.279281678280e-01
     0.000000000000e+00 5.512000000000e-03 0.000000000000e+00 2.648447814380e+03
     0.000000000000e+00 0.000000000000e+00 1.315210795611e+00 0.000000000000e+00
     1.704902190530e+00 0.000000000000e+00 5.953803280085e+00 0.000000000000e+00
     0.000000000000e+00 2.504547476612e-09 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00
> EPH X41873
    2024 02 17 08 43 58 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 1.426646093214e+00
     0.000000000000e+00 1.854000000000e-04 0.000000000000e+00 2.603067761507e+03
     0.000000000000e+00 0.000000000000e+00 3.093066003545e+00 0.000000000000e+00
     9.018308231272e-01 0.000000000000e+00 4.857904061440e+00 0.000000000000e+00
     0.000000000000e+00 4.857833084718e-08 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00"""

    rinex_nav = rnx.Nav(StringIO(doc))
    assert len(rinex_nav) == 2

    blocks = list(rinex_nav)
    assert blocks[0].epoch == datetime.datetime(2024, 2, 17, 10, 33, 35)
    assert blocks[1].epoch == datetime.datetime(2024, 2, 17,  8, 43, 58)

    sorted_blocks = list(sorted(rinex_nav))
    assert sorted_blocks[0].epoch == datetime.datetime(2024, 2, 17,  8, 43, 58)
    assert sorted_blocks[0].satellite.prn == 41873

    assert sorted_blocks[1].epoch == datetime.datetime(2024, 2, 17, 10, 33, 35)
    assert sorted_blocks[1].satellite.prn == 40044


def test__merge_rinex_navs():
    """Rinex :: Merge Rinex NAVs """

    doc1 = """     4.99           NAVIGATION DATA     M                   RINEX VERSION / TYPE
rinex_from_file     rokubun             20240222 055117 UTC PGM / RUN BY / DATE
    18                                                      LEAP SECONDS
                                                            END OF HEADER
> EPH X40044
    2024 02 17 10 33 35 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 3.279281678280e-01
     0.000000000000e+00 5.512000000000e-03 0.000000000000e+00 2.648447814380e+03
     0.000000000000e+00 0.000000000000e+00 1.315210795611e+00 0.000000000000e+00
     1.704902190530e+00 0.000000000000e+00 5.953803280085e+00 0.000000000000e+00
     0.000000000000e+00 2.504547476612e-09 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00"""

    doc2 = """     4.99           NAVIGATION DATA     M                   RINEX VERSION / TYPE
rinex_from_file     rokubun             20240222 055117 UTC PGM / RUN BY / DATE
    18                                                      LEAP SECONDS
                                                            END OF HEADER
> EPH X41873
    2024 02 17 08 43 58 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 1.426646093214e+00
     0.000000000000e+00 1.854000000000e-04 0.000000000000e+00 2.603067761507e+03
     0.000000000000e+00 0.000000000000e+00 3.093066003545e+00 0.000000000000e+00
     9.018308231272e-01 0.000000000000e+00 4.857904061440e+00 0.000000000000e+00
     0.000000000000e+00 4.857833084718e-08 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00"""

    merged_rinex_str = rnx.merge_nav([StringIO(doc1), StringIO(doc2)])
    merged_rinex = rnx.Nav(StringIO(merged_rinex_str))

    blocks = list(merged_rinex)

    assert len(blocks) == 2
    assert blocks[0].satellite.prn == 41873
    assert blocks[1].satellite.prn == 40044


def test__read_rinex_nav_with_eop_sto_ion():
    """Rinex :: Read Rinex Nav with EOP STO ION fields """

    doc = """     4.00           NAVIGATION DATA     M                   RINEX VERSION / TYPE
BCEmerge            congo               20240218 004604 GMT PGM / RUN BY / DATE
Merged GPS/GLO/GAL/BDS/QZS/SBAS/IRNSS navigation file       COMMENT
based on CONGO and IGS tracking data                        COMMENT
DLR/GSOC: O. Montenbruck; P. Steigenberger                  COMMENT
https://doi.org/10.57677/BRD400DLR                          DOI
       94                                                   MERGED FILE
    18    18  1929     7                                    LEAP SECONDS
                                                            END OF HEADER
> STO C20 CNVX
    2024 02 16 23 20 00 BDGA
     5.184360000000e+05-1.853914000094e-08-1.465494392505e-14-7.792703114740e-20
> EOP G24 CNVX
    2024 02 18 17 04 00 3.496837615967e-02-1.758575439453e-03 0.000000000000e+00
                        2.492733001709e-01 1.537799835205e-03 0.000000000000e+00
    -8.632800000000e+04-2.960562705994e-03-3.077089786530e-04 0.000000000000e+00
> ION G01 LNAV
    2024 02 17 00 18 54 2.328306436539e-08 0.000000000000e+00-1.192092895508e-07
     1.192092895508e-07 1.351680000000e+05-8.192000000000e+04 6.553600000000e+04
    -4.587520000000e+05
> EPH G01 LNAV
G01 2024 02 17 00 00 00 1.698434352875e-04 1.591615728103e-12 0.000000000000e+00
     8.200000000000e+01-4.312500000000e+01 3.931592338030e-09 1.768412599632e+00
    -2.397224307060e-06 1.273380708881e-02 5.612149834633e-06 5.154006444931e+03
     5.184000000000e+05-3.110617399216e-07-2.364190393722e+00-1.881271600723e-07
     9.907039110916e-01 2.890625000000e+02 9.981819972125e-01-7.899257607215e-09
    -5.928818387655e-11 1.000000000000e+00 2.301000000000e+03 0.000000000000e+00
     4.000000000000e+00 6.300000000000e+01 5.122274160385e-09 8.200000000000e+01
     5.112180000000e+05 4.000000000000e+00                                      """

    rinex_nav = rnx.Nav(StringIO(doc))

    blocks = list(rinex_nav)

    assert len(blocks) == 1
    assert blocks[0].satellite.prn == 1


def test__write_leo_rinex():
    """Rinex :: Write LEO Rinex from TLE :: ONEWEB """

    doc = """ONEWEB-0012
1 44057U 19010A   24048.46720274 -.00000208  00000+0 -57902-3 0  9998
2 44057  87.9056  38.1049 0002697  78.3061 281.8373 13.16593911239624
ONEWEB-0010
1 44058U 19010B   24048.56855024  .00000095  00000+0  21501-3 0  9990
2 44058  87.9061  38.0627 0001996  67.4050 292.7292 13.16593857239686
ONEWEB-0008
1 44059U 19010C   24048.51787914  .00000040  00000+0  69755-4 0  9992
2 44059  87.9061  38.0745 0001821  94.6884 265.4455 13.16596956239795"""

    with tempfile.NamedTemporaryFile() as fh:

        fh.write(doc.encode('utf-8'))

        # rewind the file-handler
        fh.seek(0)

        tle_list = read_celestrak(fh.name)

    with tempfile.NamedTemporaryFile() as fh:

        rnx.Nav.write_from_tle(fh.name, tle_list)

        fh.seek(0)

        doc = fh.read().decode('utf-8')

        assert '> EPH O44057' in doc
        assert '2024 02 17 11 12 46' in doc
        assert '1.534242150941e+00 0.000000000000e+00 1.366699269396e+00 0.000000000000e+00' in doc

        assert '> EPH O44058' in doc
        assert '2024 02 17 13 38 42' in doc
        assert '0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 5.109088356729e+00' in doc

        assert '> EPH O44059' in doc
        assert '2024 02 17 12 25 44' in doc
        assert '0.000000000000e+00 1.821000000000e-04 0.000000000000e+00 2.752432321090e+03' in doc


def test__write_leo_rinex_from_csv():
    """Rinex :: Write LEO Rinex from CSV :: SPIRE """

    doc = f"""{rnx.SAT_STR},{rnx.EPOCH_STR},{rnx.A_M_STR},{rnx.ECCENTRICITY_STR},{rnx.INCLINATION_DEG_STR},{rnx.RIGHT_ASCENSION_DEG_STR},{rnx.ARG_PERIGEE_DEG_STR},{rnx.TRUE_ANOMALY_DEG_STR}
V10000,2022-01-01 00:01:00,7366775.464,0.034093880517252914,81.45317692780878,354.6023196668008,216.5849516825415,-174.80318047601247
V10000,2022-01-01 02:01:00,7366775.464,0.034093880517252914,81.45317692780878,354.6023196668008,216.5849516825415,-125.74340748919079
V10000,2022-01-01 04:01:00,7366775.464,0.034093880517252914,81.45317692780878,354.6023196668008,216.5849516825415,-74.34506652494632
V10000,2022-01-01 06:01:00,7366775.464,0.034093880517252914,81.45317692780878,354.6023196668008,216.5849516825415,-19.99904454886491"""

    with tempfile.NamedTemporaryFile() as fh:

        fh.write(doc.encode('utf-8'))

        # rewind the file-handler
        fh.seek(0)

        df = pd.read_csv(fh.name, parse_dates=['epoch'])

    # Zero clock satellite block
    with tempfile.NamedTemporaryFile() as fh:

        rnx.Nav.write_from_dataframe(fh.name, df)

        fh.seek(0)

        doc = fh.read().decode('utf-8')

        assert '> EPH V10000' in doc
        assert '2022 01 01 06 01 00' in doc
        assert '0.000000000000e+00 0.000000000000e+00 0.000000000000e+00-3.490491746307e-01' in doc
        assert '0.000000000000e+00 3.409388051725e-02 0.000000000000e+00 2.714180440575e+03' in doc
        assert '5.400600000000e+05 0.000000000000e+00 4.535869082549e+00 0.000000000000e+00' in doc
        assert '1.421626123600e+00 0.000000000000e+00 3.780120517133e+00 0.000000000000e+00' in doc
        assert '0.000000000000e+00 0.000000000000e+00 2.190000000000e+03 0.000000000000e+00' in doc
        assert '0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00' in doc


def test__write_leo_rinex_from_csv_random_clk():
    """Rinex :: Write LEO Rinex from CSV :: SPIRE """

    doc = f"""{rnx.SAT_STR},{rnx.EPOCH_STR},{rnx.A_M_STR},{rnx.ECCENTRICITY_STR},{rnx.INCLINATION_DEG_STR},{rnx.RIGHT_ASCENSION_DEG_STR},{rnx.ARG_PERIGEE_DEG_STR},{rnx.TRUE_ANOMALY_DEG_STR}
V10001,2022-01-01 00:01:00,7366775.464,0.034093880517252914,81.45317692780878,354.6023196668008,216.5849516825415,-174.80318047601247
V10000,2022-01-01 02:01:00,7366775.464,0.034093880517252914,81.45317692780878,354.6023196668008,216.5849516825415,-125.74340748919079
V10001,2022-01-01 04:01:00,7366775.464,0.034093880517252914,81.45317692780878,354.6023196668008,216.5849516825415,-74.34506652494632
V10000,2022-01-01 06:01:00,7366775.464,0.034093880517252914,81.45317692780878,354.6023196668008,216.5849516825415,-19.99904454886491"""

    with tempfile.NamedTemporaryFile() as fh:

        fh.write(doc.encode('utf-8'))

        # rewind the file-handler
        fh.seek(0)

        df = pd.read_csv(fh.name, parse_dates=['epoch'])

    # Random clock satellite block
    with tempfile.NamedTemporaryFile() as fh:

        np.random.seed(0)

        rnx.Nav.write_from_dataframe(fh.name, df, sat_clock_model=rnx.GnssRandomClock())

        fh.seek(0)

        doc = fh.read().decode('utf-8')

        assert '> EPH V10000' in doc
        assert '2022 01 01 06 01 00 1.027763024283e-04 8.976636599379e-13 0.000000000000e+00' in doc
        assert '0.000000000000e+00 0.000000000000e+00 0.000000000000e+00-3.490491746307e-01' in doc
        assert '0.000000000000e+00 3.409388051725e-02 0.000000000000e+00 2.714180440575e+03' in doc
        assert '5.400600000000e+05 0.000000000000e+00 4.535869082549e+00 0.000000000000e+00' in doc
        assert '1.421626123600e+00 0.000000000000e+00 3.780120517133e+00 0.000000000000e+00' in doc
        assert '0.000000000000e+00 0.000000000000e+00 2.190000000000e+03 0.000000000000e+00' in doc


def test__write_leo_rinex2_from_rinex():
    """Rinex :: Write LEO Rinex from RINEX2 :: LEO """

    doc = """     4.99           NAVIGATION DATA     M                   RINEX VERSION / TYPE
rinex_from_file     rokubun             20240414 183239 UTC PGM / RUN BY / DATE
    18                                                      LEAP SECONDS
                                                            END OF HEADER
> EPH L00001
    2022 01 01 00 10 00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00-2.166473122116e+00
     0.000000000000e+00 4.900228161470e-02 0.000000000000e+00 2.767826529427e+03
     5.190000000000e+05 0.000000000000e+00 6.244167969239e+00 0.000000000000e+00
     1.328645263796e+00 0.000000000000e+00 2.360400817089e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 2.190000000000e+03 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00
     0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00"""

    with tempfile.NamedTemporaryFile() as fh:

        fh.write(doc.encode('utf-8'))

        # rewind the file-handler
        fh.seek(0)

        nav = rnx.Nav(fh.name)

    with tempfile.NamedTemporaryFile() as fh:

        nav.write(fh.name, rinex2=True)

        fh.seek(0)

        doc = fh.read().decode('utf-8')

        assert ' 1 22 01 01 00 10 00.0 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00' in doc
        assert '    0.000000000000e+00 0.000000000000e+00 0.000000000000e+00-2.166473122116e+00' in doc
        assert '    0.000000000000e+00 4.900228161470e-02 0.000000000000e+00 2.767826529427e+03' in doc
        assert '    5.190000000000e+05 0.000000000000e+00 6.244167969239e+00 0.000000000000e+00' in doc
        assert '    1.328645263796e+00 0.000000000000e+00 2.360400817089e+00 0.000000000000e+00' in doc
        assert '    0.000000000000e+00 0.000000000000e+00 2.190000000000e+03 0.000000000000e+00' in doc
        assert '    0.000000000000e+00 0.000000000000e+00 0.000000000000e+00 0.000000000000e+00' in doc
        assert '    5.190000000000e+05 0.000000000000e+00' in doc

def test__rinex_to_parquet_cli():
    """Rinex :: Rinex to Parquet """

    executable = "rinex_to_parquet"

    # Write sample RINEX obs file
    doc = """     3.01           OBSERVATION DATA    G                   RINEX VERSION / TYPE
teqc  2020Oct7      UNAVCO Archive Ops  20240511 09:44:10UTCPGM / RUN BY / DATE
AB33                                                        MARKER NAME
                                                            MARKER NUMBER
Glen Mattioli       UNAVCO                                  OBSERVER / AGENCY
4614207052          TRIMBLE NETRS       1.3-2               REC # / TYPE / VERS
0220369841          TRM29659.00     SCIT                    ANT # / TYPE
        0.0083        0.0000        0.0000                  ANTENNA: DELTA H/E/N
 -2145891.0801 -1230329.3656  5859603.6578                  APPROX POSITION XYZ
G    7 C1C C2C C2W L1C L2W S1C S2W                          SYS / # / OBS TYPES
     1     1                                                WAVELENGTH FACT L1/2
    18                                                      LEAP SECONDS
     1.000                                                  INTERVAL
  2024     5    10     0     0    0.0000000     GPS         TIME OF FIRST OBS
  2024     5    10    23    59   59.0000000     GPS         TIME OF LAST OBS
                                                            END OF HEADER
> 2024 05 10 00 00 00.0000000  0 11
G07  24240074.602    24240066.355    24240066.762    -8998575.524 6  -6993780.075 6        39.800          38.300
G08  22366294.281    22366288.379    22366287.906   -10407041.175 7  -8083576.879 7        44.500          43.800
G10  23072017.359    23072012.277    23072012.629    -9745357.576 7  -7587925.639 7        45.300          45.600
G13  22795355.211                    22795347.137    -7904676.063 6  -5970261.86044        41.100          28.500
G15  22182238.531    22182232.570    22182232.391   -14890350.343 7 -11536879.011 7        43.200          43.900
G16  22678773.367                    22678764.121    -9289365.096 7  -7165429.80745        45.200          32.700
G18  21699737.234    21699729.457    21699729.395   -18660214.875 7 -14533852.543 8        46.100          50.200
G23  21108098.141    21108089.543    21108089.422   -22176633.537 7 -17266992.090 8        47.300          51.000
G26  25326531.172    25326532.773    25326532.945     4952661.301 5   3878011.003 6        31.800          38.200
G27  20593558.922    20593551.730    20593551.551   -22679690.334 8 -17657510.885 8        50.200          52.300
G30  24134387.953    24134384.398    24134383.574    -7369455.104 6  -5729164.212 6        38.700          39.500
"""

    with tempfile.NamedTemporaryFile() as fh:

        fh.write(doc.encode('utf-8'))

        # rewind the file-handler
        fh.seek(0)

        # No argument run
        _ = subprocess.run([executable, '-h'], capture_output=True, text=True, check=True)

        output_file = fh.name + '.parquet'

        # Simple conversion to parquet
        _ = subprocess.run([executable, '-o', output_file, fh.name],
                           capture_output=True, text=True, check=True)
        df = pd.read_parquet(output_file)
        assert len(df) == 33
        assert df.iloc[0]['station'] == "AB33".lower()

        # Change station name
        station_name = "TEST"
        _ = subprocess.run([executable, '-o', output_file, '-n', station_name, fh.name],
                           capture_output=True, text=True, check=True)

        df = pd.read_parquet(output_file)
        assert len(df) == 33
        assert df.iloc[0]['station'] == station_name.lower()

        # Clean
        os.remove(output_file)


def test_doctest():
    """Rinex :: Number of failed doctests should be 0"""

    fails, tests = doctest.testmod(rnx)
    assert tests > 0
    assert fails == 0
