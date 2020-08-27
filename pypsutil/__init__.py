from ._detect import BSD, FREEBSD, LINUX, MACOS, NETBSD, OPENBSD
from ._errors import AccessDenied, Error, NoSuchProcess, TimeoutExpired, ZombieProcess
from ._process import (
    Gids,
    Process,
    ProcessSignalMasks,
    Uids,
    pid_exists,
    pids,
    process_iter,
    process_iter_available,
    wait_procs,
)
from ._system import boot_time, time_since_boot

try:
    from ._system import uptime  # noqa  # pytype: disable=import-error
except ImportError:
    pass

__version__ = "0.2.0"

__all__ = [
    "PROCFS_PATH",
    "LINUX",
    "MACOS",
    "FREEBSD",
    "NETBSD",
    "OPENBSD",
    "BSD",
    "boot_time",
    "time_since_boot",
    "Process",
    "ProcessSignalMasks",
    "pid_exists",
    "pids",
    "process_iter",
    "process_iter_available",
    "wait_procs",
    "ProcessSignalMasks",
    "Uids",
    "Gids",
    "Error",
    "NoSuchProcess",
    "ZombieProcess",
    "AccessDenied",
    "TimeoutExpired",
]

if "uptime" in globals():
    __all__.append("uptime")

PROCFS_PATH = "/proc"
