from ._errors import ZombieProcess
from ._process import Process, ProcessSignalMasks, pid_exists, pids, process_iter
from ._system import boot_time

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
