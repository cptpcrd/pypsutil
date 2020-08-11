from ._errors import ZombieProcess
from ._process import (
    Process,
    ProcessSignalMasks,
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
    "boot_time",
    "time_since_boot",
    "Process",
    "ProcessSignalMasks",
    "pid_exists",
    "pids",
    "process_iter",
    "process_iter_available",
    "wait_procs",
    "ZombieProcess",
]

if "uptime" in globals():
    __all__.append("uptime")

PROCFS_PATH = "/proc"
