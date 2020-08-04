# Type checkers don't like the wrapper names not existing.
# mypy: ignore-errors
# pytype: disable=module-attr
import sys

from ._errors import ZombieProcess

__version__ = "0.2.0"

__all__ = (
    "PROCFS_PATH",
    "boot_time",
    "Process",
    "ProcessSignalMasks",
    "pid_exists",
    "pids",
    "process_iter",
    "ZombieProcess",
)

PROCFS_PATH = "/proc"


def _get_procfs_path() -> str:
    return PROCFS_PATH


if sys.platform.startswith("linux"):
    from . import _pslinux

    _psimpl = _pslinux
elif sys.platform.startswith("freebsd"):
    from . import _psfreebsd

    _psimpl = _psfreebsd
elif sys.platform.startswith("netbsd"):
    from . import _psnetbsd

    _psimpl = _psnetbsd
elif sys.platform.startswith("openbsd"):
    from . import _psopenbsd

    _psimpl = _psopenbsd
elif sys.platform.startswith("dragonfly"):
    from . import _psdragonfly

    _psimpl = _psdragonfly
elif sys.platform.startswith("darwin"):
    from . import _psmacosx

    _psimpl = _psmacosx
else:
    _psimpl = None

# These need to be at the bottom because of circular dependencies, but
# unless they're in a separate block isort will try to move them up to the top.

if True:  # pylint: disable=using-constant-test
    from ._system import boot_time
    from ._process import Process, ProcessSignalMasks, pid_exists, pids, process_iter
