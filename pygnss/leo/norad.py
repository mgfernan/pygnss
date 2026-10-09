import json
import urllib.parse
import urllib.request
from typing import Dict, Optional

from ..logger import logger

CELESTRAK_GP_URL = "https://celestrak.org/NORAD/elements/gp.php"
CELESTRAK_TIMEOUT_S = 20

# NORAD ids of the satellites found in the sample data (source: Celestrak)
BUNDLED_NORAD_IDS: Dict[str, int] = {
    'GLOBALSTAR M078': 39076,
    'GLOBALSTAR M086': 38045,
    'GLOBALSTAR M091': 37741,
    'IRIDIUM 103': 41918,
    'IRIDIUM 105': 41921,
    'IRIDIUM 109': 41919,
    'IRIDIUM 166': 43570,
    'ORBCOMM FM110': 41182,
}


def _normalize(name: str) -> str:
    return ' '.join(name.upper().split())


def load_norad_map(filename: str) -> Dict[str, int]:
    """
    Load a JSON file with a {"SATELLITE NAME": norad_id} dictionary
    """

    with open(filename, 'r', encoding='utf-8') as fh:
        return {_normalize(name): int(norad_id) for name, norad_id in json.load(fh).items()}


class SatNameResolver:
    """
    Map satellite names (e.g. 'IRIDIUM 105') to NORAD ids.

    The ids are looked up, in order, in the user-provided map, the bundled table and,
    if enabled, in Celestrak.
    """

    def __init__(self, overrides: Optional[Dict[str, int]] = None, online: bool = False):
        self._known = dict(BUNDLED_NORAD_IDS)
        if overrides:
            self._known.update({_normalize(name): int(norad_id) for name, norad_id in overrides.items()})
        self._online = online

    def resolve(self, name: str) -> int:
        """
        >>> SatNameResolver().resolve('Iridium  105')
        41921
        >>> SatNameResolver({'IRIDIUM 105': 1}).resolve('IRIDIUM 105')
        1
        >>> SatNameResolver().resolve('UNKNOWN SAT')
        Traceback (most recent call last):
        ...
        KeyError: 'No NORAD id found for satellite [ UNKNOWN SAT ]'
        """

        key = _normalize(name)

        if key not in self._known and self._online:
            norad_id = self._lookup_celestrak(key)
            if norad_id is not None:
                self._known[key] = norad_id

        if key not in self._known:
            raise KeyError(f'No NORAD id found for satellite [ {name} ]')

        return self._known[key]

    @staticmethod
    def _lookup_celestrak(name: str) -> Optional[int]:

        url = f'{CELESTRAK_GP_URL}?{urllib.parse.urlencode({"NAME": name, "FORMAT": "json"})}'
        try:
            with urllib.request.urlopen(url, timeout=CELESTRAK_TIMEOUT_S) as response:
                entries = json.load(response)
        except (OSError, ValueError) as e:
            logger.warning(f'Celestrak lookup for [ {name} ] failed: {e}')
            return None

        for entry in entries if isinstance(entries, list) else []:
            if _normalize(entry.get('OBJECT_NAME', '')) == name:
                return int(entry['NORAD_CAT_ID'])

        return None
