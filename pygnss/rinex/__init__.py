"""
RINEX reading/writing utilities.

The implementation is split in submodules, but the public API is kept
available at the ``pygnss.rinex`` level for backwards compatibility.
"""

from .defs import *  # noqa: F401,F403
from .ids import *  # noqa: F401,F403
from .observables import *  # noqa: F401,F403
from .clock import *  # noqa: F401,F403
from .period import *  # noqa: F401,F403
from .obs import *  # noqa: F401,F403
from .nav import *  # noqa: F401,F403
from .cli import *  # noqa: F401,F403

from .obs import _parse_obs_line, _parse_rnx3_epoch  # noqa: F401
from .nav import _parse_nav_epoch_line, _parse_nav_orb_line, _get_eph_type_from_rinex4_nav_block_header  # noqa: F401
