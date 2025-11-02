import gzip
import pandas as pd
import tempfile

try:
    from pygnss._c_ext import _read_crx  # compiled C extension for fast CRX parsing
except Exception as exc:  # pragma: no cover - environment-specific
    _import_err = exc

    def _read_crx(*args, **kwargs):
        """Fallback stub when the compiled extension is missing.

        The real implementation lives in the compiled extension module
        ``pygnss._c_ext``. If that extension isn't available (for example on
        CI or when the package wasn't built/installed), attempting to read a
        CRX file will raise a clear ImportError with instructions.
        """
        raise ImportError(
            "pygnss C extension 'pygnss._c_ext' is not available.\n"
            "To enable Hatanaka (.crx) parsing, build and install the package so\n"
            "that the compiled extension is present (e.g. running 'pip install .',\n"
            "or building the wheel in your CI).\n"
            f"Original import error: {type(_import_err).__name__}: {_import_err}"
        ) from _import_err

def to_dataframe(filename:str, station:str = "none", strict_lli: bool = True) -> pd.DataFrame:
    """
    Convert a Compressed (crx.gz) or uncompressed (crx) Hatanaka file into a
    DataFrame

    :param filename: Hatanaka [gzip compressed] filename
    :param station: force station name
    :param strict_lli: Mark cycle slips only when Phase LLI is 1 (as per RINEX convention).
    If False, any value of Phase LLI will trigger a cycle slip flag
    """

    if filename.endswith('crx.gz') or filename.endswith('crx.Z') or filename.endswith('crz'):
        try:
            with gzip.open(filename, 'rb') as f_in:
                with tempfile.NamedTemporaryFile(delete=False) as f_out:
                    f_out.write(f_in.read())
                    f_out.seek(0)
                    array = _read_crx(f_out.name)
        except gzip.BadGzipFile:
            raise ValueError(f"{filename} is not a valid gzip file.")

    else:
        array = _read_crx(filename)

    df = pd.DataFrame(array, columns=['epoch', 'sat', 'rinex3_code', 'value', 'lli'])
    df['channel'] = df['rinex3_code'].str[-2:]
    df['signal'] = df['sat'] + df['channel']
    MAPPING = {'C': 'range', 'L': 'phase', 'D': 'doppler', 'S': 'snr'}
    df['obstype'] = df['rinex3_code'].str[0].map(lambda x: MAPPING.get(x, 'Unknown'))
    df = df.pivot_table(index=['epoch', 'signal', 'sat', 'channel'], columns=['obstype'], values=['value', 'lli'])

    # Remove all LLI columns except for the phase (for the cycle slips)
    if strict_lli:
        df['cslip'] = (df.loc[:, pd.IndexSlice['lli', 'phase']] % 2) == 1
    else:
        df['cslip'] = df.loc[:, pd.IndexSlice['lli', 'phase']] > 0

    df.drop('lli', axis=1, inplace=True)
    df.columns = [v[1] if v[0] == 'value' else v[0] for v in df.columns.values]

    df.reset_index(inplace=True)

    df['station'] = station

    return df
