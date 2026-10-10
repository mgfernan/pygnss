"""
Convert Two-Line Elements (TLE) into SP3-d orbit files (ECEF positions with an
error estimate), propagating the TLEs with SGP4.

Format reference: https://files.igs.org/pub/data/format/sp3d.pdf

Notes:

- SP3 satellite identifiers only have two digits, so satellites are named
  ``Lnn`` (``L`` is the LEO constellation letter) and the mapping to NORAD
  catalog numbers is stored in the ``/*`` comment lines as ``NORAD Lnn=id``.
- SGP4 outputs TEME coordinates, that are rotated to ECEF with the GMST angle
  (polar motion neglected, which is far below the TLE accuracy).
- The error is a simple empirical model that grows linearly with the time
  distance to the TLE epoch. It is reported as the 1-sigma position standard
  deviation in the P records, as ``base**n`` mm (base set in the ``%f`` line).
"""
import argparse
import datetime
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import numpy as np
from sgp4.api import Satrec, jday
from sgp4.propagation import gstime

from .. import time as gtime
from .tle import TLE, read_celestrak

SP3_CONSTELLATION = 'L'
MAX_SATS_PER_FILE = 85
POS_STD_BASE = 1.25
BAD_CLOCK = 999999.999999
COMMENT_WIDTH = 57


@dataclass
class ErrorModel:
    """
    1-sigma TLE position error in the orbit frame (radial, along-track, cross-track),
    in km: ``offset + rate * |days from TLE epoch|``
    """
    radial_km: float = 0.5
    radial_km_per_day: float = 0.5
    along_km: float = 1.0
    along_km_per_day: float = 2.0
    cross_km: float = 0.5
    cross_km_per_day: float = 0.5

    def sigmas_km(self, days: float) -> np.ndarray:
        d = abs(days)
        return np.array([self.radial_km + self.radial_km_per_day * d,
                         self.along_km + self.along_km_per_day * d,
                         self.cross_km + self.cross_km_per_day * d])


def teme_to_ecef(r_teme: np.ndarray, jd_ut: float) -> np.ndarray:
    theta = gstime(jd_ut)
    c, s = math.cos(theta), math.sin(theta)
    rot = np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]])
    return rot @ r_teme


def propagate_ecef(tle: TLE, epoch_gps: datetime.datetime, error_model: ErrorModel):
    """
    Propagate the TLE to a GPS-time epoch.

    :return: tuple of ECEF position [m] and per-axis (X, Y, Z) 1-sigma error [m]
    """
    sat = Satrec.twoline2rv(tle.line1, tle.line2)
    epoch_utc = epoch_gps - gtime.get_gps_leapseconds(epoch_gps)
    jd, fr = jday(epoch_utc.year, epoch_utc.month, epoch_utc.day, epoch_utc.hour, epoch_utc.minute,
                  epoch_utc.second + epoch_utc.microsecond * 1e-6)

    err, r, v = sat.sgp4(jd, fr)
    if err != 0:
        raise RuntimeError(f'SGP4 error {err} for NORAD {tle.id} at {epoch_utc}')

    r = np.array(r)
    v = np.array(v)
    days = (epoch_utc - tle.toe).total_seconds() / 86400.0

    # Orbit frame (radial, along-track, cross-track) in TEME, rotated to ECEF
    u_r = r / np.linalg.norm(r)
    u_c = np.cross(r, v)
    u_c /= np.linalg.norm(u_c)
    u_a = np.cross(u_c, u_r)
    sigmas = error_model.sigmas_km(days)
    cov = sum(s**2 * np.outer(u, u) for s, u in zip(sigmas, (u_r, u_a, u_c)))
    theta = gstime(jd + fr)
    c, s_ = math.cos(theta), math.sin(theta)
    rot = np.array([[c, s_, 0.0], [-s_, c, 0.0], [0.0, 0.0, 1.0]])
    cov_ecef = rot @ cov @ rot.T

    return teme_to_ecef(r, jd + fr) * 1e3, np.sqrt(np.diag(cov_ecef)) * 1e3


def _std_exponent(sigma_m: float, base: float = POS_STD_BASE) -> int:
    sigma_mm = max(sigma_m * 1e3, 1.0)
    return min(99, max(0, int(round(math.log(sigma_mm) / math.log(base)))))


def _accuracy_exponent(sigma_m: float) -> int:
    return min(99, max(0, int(round(math.log2(max(sigma_m * 1e3, 1.0))))))


def _select_tle(tles: Sequence[TLE], epoch_utc: datetime.datetime) -> TLE:
    return min(tles, key=lambda t: abs((epoch_utc - t.toe).total_seconds()))


def _group_by_norad(tles: Sequence[TLE]) -> Dict[int, List[TLE]]:
    groups = defaultdict(list)
    seen = set()
    for tle in tles:
        key = (tle.line1, tle.line2)
        if key in seen:
            continue
        seen.add(key)
        groups[tle.id].append(tle)
    return dict(sorted(groups.items()))


def parse_sat_id_assignment(text: str) -> tuple:
    """
    Parse a NORAD=SATID assignment (e.g. 40044=L05) into (40044, 'L05')

    >>> parse_sat_id_assignment('40044=L05')
    (40044, 'L05')
    >>> parse_sat_id_assignment('40044=l5')
    (40044, 'L05')
    """
    norad, sep, sat = text.partition('=')
    sat = sat.strip().upper()
    if not sep or not norad.strip().isdigit():
        raise ValueError(f"Invalid sat id assignment '{text}', expected NORAD=SATID (e.g. 40044=L05)")
    if len(sat) == 2 and sat[0].isalpha() and sat[1].isdigit():
        sat = f'{sat[0]}0{sat[1]}'
    if not (len(sat) == 3 and sat[0].isalpha() and sat[1:].isdigit() and int(sat[1:]) > 0):
        raise ValueError(f"Invalid SP3 satellite id '{sat}' in '{text}', expected a letter and two digits (e.g. L05)")
    return int(norad), sat


def _assign_sat_ids(norads: Sequence[int], assigned: Dict[int, str]) -> Dict[int, str]:
    """
    Use the requested ids for the given NORAD ids and automatically number the rest
    (Lnn, skipping ids already in use)
    """
    sat_ids = {n: assigned[n] for n in norads if n in assigned}

    duplicated = [s for s in set(sat_ids.values()) if list(sat_ids.values()).count(s) > 1]
    if duplicated:
        raise ValueError(f'SP3 satellite ids assigned to more than one NORAD id: {sorted(duplicated)}')

    used = set(sat_ids.values())
    free = (f'{SP3_CONSTELLATION}{i:02d}' for i in range(1, 100))
    for n in norads:
        if n not in sat_ids:
            sat = next(f for f in free if f not in used)
            sat_ids[n] = sat
            used.add(sat)

    return sat_ids


def _comment_lines(sat_map: Dict[str, int], names: Dict[str, str], extra: Sequence[str]) -> List[str]:
    lines = ['TLE propagated with SGP4, TEME rotated to ECEF with GMST (polar motion neglected)',
             f'Position std (P records) is an empirical TLE error model, in mm as {POS_STD_BASE}**n']
    lines += list(extra)
    lines.append('Satellite id to NORAD catalog number map (NORAD Lnn=catalog):')

    current = 'NORAD'
    for sat, norad in sat_map.items():
        token = f' {sat}={norad:05d}'
        if len(current) + len(token) > COMMENT_WIDTH:
            lines.append(current)
            current = 'NORAD'
        current += token
    lines.append(current)

    for sat, name in names.items():
        if name:
            lines.append(f'NAME {sat}={name}'[:COMMENT_WIDTH])

    return lines


def build_sp3(tles: Sequence[TLE],
              start: Optional[datetime.datetime] = None,
              end: Optional[datetime.datetime] = None,
              interval_s: float = 300.0,
              error_model: Optional[ErrorModel] = None,
              agency: str = 'TLE',
              frame: str = 'IGS20',
              comments: Sequence[str] = (),
              sat_id_map: Optional[Dict[int, str]] = None,
              epochs: Optional[Sequence[datetime.datetime]] = None) -> str:
    """
    Build the SP3-d content for the TLE set (at most 85 satellites). Epochs are in GPS time.
    If several TLEs exist for a NORAD id, the closest in time is used at each epoch.
    ``sat_id_map`` optionally assigns SP3 ids (e.g. ``{40044: 'L05'}``) to NORAD ids; the rest are
    numbered automatically.
    If ``epochs`` (GPS time, sorted) is given, it is used instead of ``start``, ``end`` and ``interval_s``,
    which allows irregular epochs (e.g. to match the epochs of another SP3 file).
    """
    error_model = error_model or ErrorModel()
    groups = _group_by_norad(tles)

    if not groups:
        raise ValueError('No TLEs provided')
    if len(groups) > MAX_SATS_PER_FILE:
        raise ValueError(f'SP3 files support at most {MAX_SATS_PER_FILE} satellites, got {len(groups)}')

    sat_ids = _assign_sat_ids(list(groups), sat_id_map or {})
    groups = dict(sorted(groups.items(), key=lambda item: sat_ids[item[0]]))
    sat_ids = {norad: sat_ids[norad] for norad in groups}

    if epochs is not None:
        epochs = list(epochs)
        if not epochs:
            raise ValueError('Empty list of epochs')
        start = epochs[0]
        if len(epochs) > 1:
            interval_s = float(np.median([(b - a).total_seconds() for a, b in zip(epochs[:-1], epochs[1:])]))
    else:
        if start is None or end is None:
            raise ValueError('Either epochs or start and end must be provided')
        epochs = list(gtime.epoch_range(start, end, interval_s))

    body = []
    max_sigma = {sat: 0.0 for sat in sat_ids.values()}
    for epoch in epochs:
        epoch_utc = epoch - gtime.get_gps_leapseconds(epoch)
        body.append('*  {:4d} {:2d} {:2d} {:2d} {:2d} {:11.8f}'.format(
            epoch.year, epoch.month, epoch.day, epoch.hour, epoch.minute,
            epoch.second + epoch.microsecond * 1e-6))
        for norad, sat_tles in groups.items():
            sat = sat_ids[norad]
            tle = _select_tle(sat_tles, epoch_utc)
            pos, sigma = propagate_ecef(tle, epoch, error_model)
            max_sigma[sat] = max(max_sigma[sat], float(sigma.max()))
            xyz = ''.join(f'{c * 1e-3:14.6f}' for c in pos)
            sd = ' '.join(f'{_std_exponent(s):2d}' for s in sigma)
            body.append(f'P{sat}{xyz}{BAD_CLOCK:14.6f} {sd}')

    week = gtime.to_week_tow(start)
    mjd = (start - datetime.datetime(1858, 11, 17)).total_seconds() / 86400.0
    mjd_day = int(math.floor(mjd))
    sec = start.second + start.microsecond * 1e-6

    header = [
        '#dP{:4d} {:2d} {:2d} {:2d} {:2d} {:11.8f} {:7d} {:5s} {:5s} {:3s} {:4s}'.format(
            start.year, start.month, start.day, start.hour, start.minute, sec,
            len(epochs), 'ORBIT', frame, 'FIT', agency),
        '## {:4d} {:15.8f} {:14.8f} {:5d} {:15.13f}'.format(
            week.week, week.tow, interval_s, mjd_day, mjd - mjd_day),
    ]

    ids = list(sat_ids.values())
    accuracies = [_accuracy_exponent(max_sigma[s]) for s in ids]
    n_lines = 5
    for i in range(n_lines):
        chunk = ids[17 * i:17 * (i + 1)]
        prefix = f'+  {len(ids):3d}   ' if i == 0 else '+        '
        header.append(prefix + ''.join(chunk).ljust(51))
    for i in range(n_lines):
        chunk = accuracies[17 * i:17 * (i + 1)]
        header.append('++       ' + ''.join(f'{a:3d}' for a in chunk).ljust(51))

    header += [
        '%c L  cc GPS ccc cccc cccc cccc cccc ccccc ccccc ccccc ccccc',
        '%c cc cc ccc ccc cccc cccc cccc cccc ccccc ccccc ccccc ccccc',
        f'%f {POS_STD_BASE:10.7f}  1.025000000  0.00000000000  0.000000000000000',
        '%f  0.0000000  0.000000000  0.00000000000  0.000000000000000',
        '%i    0    0    0    0      0      0      0      0         0',
        '%i    0    0    0    0      0      0      0      0         0',
    ]

    sat_map = {sat_ids[n]: n for n in groups}
    names = {sat_ids[n]: (g[0].label or '').strip() for n, g in groups.items()}
    comments = _comment_lines(sat_map, names, comments)
    header += [f'/* {c}'.rstrip() for c in comments]

    return '\n'.join(header + body + ['EOF']) + '\n'


def write_sp3_files(tles: Sequence[TLE], output: str, **kwargs) -> List[str]:
    """
    Write the TLEs into one SP3 file, or several (suffixed ``_NN``) if more than 85 satellites
    """
    groups = _group_by_norad(tles)
    norads = list(groups)
    chunks = [norads[i:i + MAX_SATS_PER_FILE] for i in range(0, len(norads), MAX_SATS_PER_FILE)]

    paths = []
    for i, chunk in enumerate(chunks, start=1):
        path = output
        if len(chunks) > 1:
            stem, dot, ext = output.rpartition('.')
            path = f'{stem}_{i:02d}.{ext}' if dot else f'{output}_{i:02d}'
        subset = [t for n in chunk for t in groups[n]]
        with open(path, 'w') as fh:
            fh.write(build_sp3(subset, **kwargs))
        paths.append(path)

    return paths


def _parse_datetime(text: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(text)


def cli(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('tle_files', nargs='+', help='Celestrak 3-line TLE files')
    parser.add_argument('-o', '--output', required=True, help='Output SP3 file (suffixed if >85 satellites)')
    parser.add_argument('--start', type=_parse_datetime,
                        help='Start epoch, GPS time ISO format (default: earliest TLE epoch, rounded down to the interval)')
    parser.add_argument('--end', type=_parse_datetime, help='End epoch, GPS time (default: start + 1 day)')
    parser.add_argument('--interval', type=float, default=300.0, help='Epoch interval in seconds (default: 300)')
    parser.add_argument('--agency', default='TLE', help='4-character agency code')
    parser.add_argument('--frame', default='IGS20', help='5-character coordinate system label')
    parser.add_argument('--sat-id', action='append', default=[], metavar='NORAD=SATID',
                        help='Assign an SP3 satellite id to a NORAD id, e.g. 40044=L05 (repeatable)')
    parser.add_argument('--along-km', type=float, default=1.0, help='Along-track error at TLE epoch [km]')
    parser.add_argument('--along-km-per-day', type=float, default=2.0, help='Along-track error growth [km/day]')
    args = parser.parse_args(argv)

    tles: List[TLE] = []
    for path in args.tle_files:
        tles += read_celestrak(path)
    if not tles:
        sys.exit('No TLEs found in the input files')

    start = args.start
    if start is None:
        first = min(t.toe for t in tles)
        first += gtime.get_gps_leapseconds(first)
        midnight = first.replace(hour=0, minute=0, second=0, microsecond=0)
        elapsed = (first - midnight).total_seconds()
        start = midnight + datetime.timedelta(seconds=elapsed - elapsed % args.interval)
    end = args.end or start + datetime.timedelta(days=1)

    try:
        sat_id_map = dict(parse_sat_id_assignment(a) for a in args.sat_id)
    except ValueError as e:
        parser.error(str(e))
    missing = set(sat_id_map) - {t.id for t in tles}
    if missing:
        parser.error(f'NORAD ids in --sat-id not found in the TLEs: {sorted(missing)}')

    model = ErrorModel(along_km=args.along_km, along_km_per_day=args.along_km_per_day)
    for path in write_sp3_files(tles, args.output, start=start, end=end, interval_s=args.interval,
                                error_model=model, agency=args.agency[:4], frame=args.frame[:5],
                                sat_id_map=sat_id_map):
        print(path)


if __name__ == '__main__':
    cli()
