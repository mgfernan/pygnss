import os
import tempfile

import pytest

from pygnss.rinex import (InvalidLeoExtension, InvalidRinexHeader, UnsupportedLeoExtensionVersion,
                          get_obs_line_parser, parse_header, parse_obs_line, to_dataframe)

VERSION_LINE = "     4.01           OBSERVATION DATA    M                   RINEX VERSION / TYPE"
LEO_LINE = "RINEX-LEO 1.00                                              RINEX-LEO EXTENSION"
OBS_G_LINE = "G    4 C1C L1C C2W L2W                                      SYS / # / OBS TYPES"
OBS_Z_LINE = "Z    2 D1C S1C                                              SYS / # / OBS TYPES"
END_LINE = "                                                            END OF HEADER"


def _label(text: str, label: str) -> str:
    return f'{text:<60}{label}'


def test_parse_header_leo():
    """RINEX header :: LEO extension version and observation types are parsed"""

    header = parse_header(iter([
        VERSION_LINE, LEO_LINE, _label('AB33', 'MARKER NAME'),
        _label(' 4780861.4222  176383.0427 4204318.1078', 'APPROX POSITION XYZ'),
        OBS_G_LINE, OBS_Z_LINE, END_LINE]))

    assert header.is_leo
    assert header.version == 4.01
    assert header.leo_extension_version == (1, 0)
    assert header.marker_name == 'AB33'
    assert header.approx_position_xyz == (4780861.4222, 176383.0427, 4204318.1078)
    assert list(header.obs_types) == ['G', 'Z']


def test_parse_header_without_leo_extension():
    """RINEX header :: Regular RINEX files are not flagged as LEO"""

    header = parse_header(iter([VERSION_LINE, OBS_G_LINE, END_LINE]))
    assert not header.is_leo


def test_parse_header_accepts_backwards_compatible_minor():
    """RINEX header :: A newer minor version of the extension is accepted"""

    line = LEO_LINE.replace('1.00', '1.05')
    assert parse_header(iter([VERSION_LINE, line, END_LINE])).leo_extension_version == (1, 5)


@pytest.mark.parametrize("lines, exception", [
    ([VERSION_LINE, LEO_LINE.replace('1.00', '2.00'), END_LINE], UnsupportedLeoExtensionVersion),
    ([VERSION_LINE, LEO_LINE, LEO_LINE, END_LINE], InvalidLeoExtension),
    ([VERSION_LINE, OBS_G_LINE, LEO_LINE, END_LINE], InvalidLeoExtension),
    ([VERSION_LINE, _label('LEO 1.00', 'RINEX-LEO EXTENSION'), END_LINE], InvalidLeoExtension),
    ([LEO_LINE, VERSION_LINE, END_LINE], InvalidRinexHeader),
])
def test_parse_header_errors(lines, exception):
    """RINEX header :: Invalid extension records are rejected"""

    with pytest.raises(exception):
        parse_header(iter(lines))


def test_obs_line_parsers():
    """RINEX obs :: MEO and LEO lines are parsed with their own satellite id width"""

    assert type(get_obs_line_parser('G')).__name__ == 'MeoObsLineParser'
    assert type(get_obs_line_parser('Z')).__name__ == 'LeoObsLineParser'

    sat, values = parse_obs_line("Z43012    732793.036 3    732794.384", 2)
    assert str(sat) == 'Z43012'
    assert sat.prn == 43012
    assert [v.value for v in values] == [732793.036, 732794.384]
    assert [v.snr for v in values] == [3, 0]


def test_to_dataframe_mixed_meo_leo():
    """RINEX obs :: A file with MEO and LEO satellites in the same epoch is read"""

    doc = '\n'.join([
        VERSION_LINE, LEO_LINE, OBS_G_LINE, OBS_Z_LINE, END_LINE,
        "> 2022 12 20 12  1  4.6030000  0 2",
        "G23  24718012.436   129894024.173    24718009.543   101216196.673",
        "Z43012    732793.036      732794.384",
        ""])

    with tempfile.TemporaryDirectory() as tmp:
        filename = os.path.join(tmp, 'leo.rnx')
        with open(filename, 'w') as fh:
            fh.write(doc)

        df = to_dataframe(filename)

    assert sorted(df['sat'].unique()) == ['G23', 'Z43012']
    leo = df[df['sat'] == 'Z43012'].iloc[0]
    assert leo['doppler'] == 732793.036
    assert leo['snr'] == 732794.384


# Constellation types in the table of rinex_leo_format.md
LEO_TABLE = {
    'Z': 'CENTISPACE', 'Y': 'GEELY', 'L': 'LEO', 'A': 'GLOBALSTAR', 'D': 'IRIDIUM',
    'O': 'ONEWEB', 'B': 'ORBCOMM', 'V': 'SPIRE', 'X': 'STARLINK', 'P': 'XONA',
}


@pytest.mark.parametrize("letter, name", LEO_TABLE.items())
def test_leo_constellation_table(letter, name):
    """RINEX-LEO :: Every constellation of the format table is supported end to end"""

    from pygnss.gnss.types import ConstellationId, Satellite
    from pygnss.rinex import EphType, RinexSatIdFactory
    from pygnss.rinex.nav import _get_eph_type_from_rinex4_nav_block_header

    constellation = ConstellationId.from_string(letter)
    assert constellation.name == name
    assert constellation.is_leo()
    assert RinexSatIdFactory.create(constellation).get_constellation_letter() == letter

    assert str(Satellite.from_string(f'{letter}00123')) == f'{letter}00123'
    assert _get_eph_type_from_rinex4_nav_block_header(f'> EPH {letter}00123') == EphType(letter)

    sat, _ = parse_obs_line(f'{letter}00123    732793.036', 1)
    assert (sat.constellation, sat.prn) == (constellation, 123)
