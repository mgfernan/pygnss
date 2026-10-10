"""
Toolkit to process existing SP3 files.

Subcommands:

- ``compare``: position RMS per common satellite and epoch between two files, split into
  radial (nadir), along-track and cross-track components. The RTN frame is built from the
  first file (reference). Velocity is taken from the ``V`` records when present, otherwise
  from numerical differentiation of the positions.
- ``reassign``: change a satellite identifier into another one.
"""
import argparse
import datetime
import re
import sys
from typing import Optional, Dict, Sequence, Tuple

import numpy as np
import pandas as pd


def read_sp3(path: str) -> pd.DataFrame:
    """
    Read the position (and velocity, if any) records of an SP3 file.

    :return: DataFrame indexed by (epoch, sat) with columns x, y, z [m] and optionally vx, vy, vz [m/s]
    """
    rows: Dict[Tuple, dict] = {}
    epoch = None
    with open(path) as fh:
        for line in fh:
            if line.startswith('*'):
                f = line[1:].split()
                sec = float(f[5])
                epoch = datetime.datetime(int(f[0]), int(f[1]), int(f[2]), int(f[3]), int(f[4])) \
                    + datetime.timedelta(seconds=sec)
            elif epoch is not None and line[0] in 'PV' and len(line) > 4:
                sat = line[1:4].replace(' ', '0')
                vals = [float(line[i:i + 14]) for i in (4, 18, 32)]
                if any(abs(v) >= 999999 for v in vals):
                    continue
                row = rows.setdefault((epoch, sat), {})
                if line[0] == 'P':
                    # km -> m
                    row.update(zip(('x', 'y', 'z'), (v * 1e3 for v in vals)))
                else:
                    # dm/s -> m/s
                    row.update(zip(('vx', 'vy', 'vz'), (v * 0.1 for v in vals)))
    df = pd.DataFrame.from_dict(rows, orient='index')
    df.index = pd.MultiIndex.from_tuples(df.index, names=['epoch', 'sat'])
    return df.dropna(subset=['x', 'y', 'z']).sort_index()


def _velocity(df: pd.DataFrame) -> np.ndarray:
    if {'vx', 'vy', 'vz'} <= set(df.columns) and df[['vx', 'vy', 'vz']].notna().all().all():
        return df[['vx', 'vy', 'vz']].to_numpy()
    vel = np.full((len(df), 3), np.nan)
    sats = df.index.get_level_values('sat')
    for sat in sats.unique():
        mask = np.asarray(sats == sat)
        t = df.index.get_level_values('epoch')[mask].to_numpy().astype('datetime64[ns]').astype(np.int64) * 1e-9
        pos = df.loc[mask, ['x', 'y', 'z']].to_numpy()
        if len(t) > 1:
            vel[mask] = np.column_stack([np.gradient(pos[:, i], t) for i in range(3)])
    return vel


def compare(ref: pd.DataFrame, other: pd.DataFrame) -> pd.DataFrame:
    """
    Differences (other - ref) in the common (epoch, sat) entries: dx, dy, dz (ECEF),
    radial, along, cross and 3D norm, all in metres.
    """
    common = ref.index.intersection(other.index)
    ref = ref.loc[common]
    pos = ref[['x', 'y', 'z']].to_numpy()
    vel = _velocity(ref)
    diff = other.loc[common, ['x', 'y', 'z']].to_numpy() - pos

    r = pos / np.linalg.norm(pos, axis=1, keepdims=True)
    c = np.cross(pos, vel)
    c /= np.linalg.norm(c, axis=1, keepdims=True)
    a = np.cross(c, r)

    out = pd.DataFrame({
        'dx': diff[:, 0], 'dy': diff[:, 1], 'dz': diff[:, 2],
        'radial': np.einsum('ij,ij->i', diff, r),
        'along': np.einsum('ij,ij->i', diff, a),
        'cross': np.einsum('ij,ij->i', diff, c),
        'norm': np.linalg.norm(diff, axis=1),
    }, index=common)
    return out.dropna()


def rms_stats(diffs: pd.DataFrame) -> pd.DataFrame:
    """RMS per satellite plus an 'ALL' row. '3D' is the RMS of the position error norm."""
    def _rms(g):
        return pd.Series({
            'epochs': len(g),
            '3D': np.sqrt((g['norm'] ** 2).mean()),
            'radial': np.sqrt((g['radial'] ** 2).mean()),
            'along': np.sqrt((g['along'] ** 2).mean()),
            'cross': np.sqrt((g['cross'] ** 2).mean()),
        })
    per_sat = diffs.groupby(level='sat').apply(_rms)
    per_sat.loc['ALL'] = _rms(diffs)
    per_sat['epochs'] = per_sat['epochs'].astype(int)
    return per_sat


def normalize_sat_id(sat: str) -> str:
    """Normalize an identifier such as ``L1`` or ``l01`` into the 3-character SP3 form (``L01``)"""
    sat = sat.strip().upper()
    m = re.fullmatch(r'([A-Z])\s*(\d{1,2})', sat)
    if not m:
        raise ValueError(f'Invalid satellite identifier: {sat!r}')
    return f'{m.group(1)}{int(m.group(2)):02d}'


def _sat_field(line: str, start: int) -> str:
    return line[start:start + 3].replace(' ', '0')


def reassign_sat(lines: Sequence[str], old: str, new: str) -> Tuple[list, int]:
    """
    Rename satellite ``old`` into ``new`` in SP3 lines (header satellite list, P/V/EP/EV records
    and ``NORAD``/``NAME`` comment maps).

    :return: the new lines and the number of replaced items
    """
    old, new = normalize_sat_id(old), normalize_sat_id(new)
    present = set()
    for line in lines:
        if line.startswith('+ ') and not line.startswith('++'):
            present.update(line[9:60][i:i + 3] for i in range(0, 51, 3))
        elif line[:1] in 'PV' and len(line) > 4:
            present.add(_sat_field(line, 1))
        elif line[:2] in ('EP', 'EV') and len(line) > 5:
            present.add(_sat_field(line, 2))
    present = {p.replace(' ', '0') for p in present}
    if old not in present:
        raise ValueError(f'Satellite {old} not found in the SP3 file')
    if new in present:
        raise ValueError(f'Satellite {new} already exists in the SP3 file')

    count = 0
    out = []
    for line in lines:
        if line.startswith('+ ') and not line.startswith('++'):
            fields = [line[9:60][i:i + 3] for i in range(0, 51, 3)]
            for k, f in enumerate(fields):
                if f.replace(' ', '0') == old:
                    fields[k] = new
                    count += 1
            line = line[:9] + ''.join(fields) + line[60:]
        elif line[:1] in 'PV' and len(line) > 4 and _sat_field(line, 1) == old:
            line = line[0] + new + line[4:]
            count += 1
        elif line[:2] in ('EP', 'EV') and len(line) > 5 and _sat_field(line, 2) == old:
            line = line[:2] + new + line[5:]
            count += 1
        elif line.startswith('/*'):
            line, n = re.subn(rf'\b((?:NORAD|NAME) ){old}=', rf'\g<1>{new}=', line)
            count += n
        out.append(line)
    return out, count


def _cmd_compare(args) -> None:
    diffs = compare(read_sp3(args.reference), read_sp3(args.other))
    if diffs.empty:
        sys.exit('No common satellites/epochs between the two files')

    stats = rms_stats(diffs)
    print('Position RMS [m] (radial = nadir direction)')
    print(stats.to_string(float_format=lambda v: f'{v:.4f}'))
    if args.epochs_output:
        diffs.to_csv(args.epochs_output)
    if args.stats_output:
        stats.to_csv(args.stats_output, index_label='sat')


def _cmd_reassign(args) -> None:
    with open(args.input) as fh:
        lines = fh.read().splitlines()
    try:
        out, count = reassign_sat(lines, args.old, args.new)
    except ValueError as e:
        sys.exit(str(e))
    with open(args.output, 'w') as fh:
        fh.write('\n'.join(out) + '\n')
    print(f'{count} replacements: {normalize_sat_id(args.old)} -> {normalize_sat_id(args.new)} ({args.output})')


def cli(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog='sp3', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    p = sub.add_parser('compare', help='Position RMS between two SP3 files (radial/along/cross)')
    p.add_argument('reference', help='Reference SP3 file (defines the RTN frame)')
    p.add_argument('other', help='SP3 file to compare')
    p.add_argument('--epochs-output', help='Write per-epoch differences to this CSV file')
    p.add_argument('--stats-output', help='Write RMS statistics to this CSV file')
    p.set_defaults(func=_cmd_compare)

    p = sub.add_parser('reassign', help='Change a satellite identifier into another one')
    p.add_argument('input', help='Input SP3 file')
    p.add_argument('old', help='Satellite ID to replace (e.g. L01)')
    p.add_argument('new', help='New satellite ID (e.g. L99)')
    p.add_argument('-o', '--output', required=True, help='Output SP3 file')
    p.set_defaults(func=_cmd_reassign)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    cli()
