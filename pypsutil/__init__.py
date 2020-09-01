from . import _system
from ._detect import BSD, FREEBSD, LINUX, MACOS, NETBSD, OPENBSD
from ._errors import AccessDenied, Error, NoSuchProcess, TimeoutExpired, ZombieProcess
from ._process import (
    Gids,
    Popen,
    Process,
    ProcessCPUTimes,
    ProcessSignalMasks,
    ProcessStatus,
    Uids,
    pid_exists,
    pids,
    process_iter,
    process_iter_available,
    wait_procs,
)
from ._system import (
    CPUFrequencies,
    CPUStats,
    DiskUsage,
    boot_time,
    disk_usage,
    physical_cpu_count,
    time_since_boot,
)

_OPTIONAL_FUNCS = [
    "uptime",
    "cpu_freq",
    "percpu_freq",
    "cpu_stats",
    "CPUTimes",
    "cpu_times",
    "percpu_times",
    "VirtualMemoryInfo",
    "virtual_memory",
    "SwapInfo",
    "swap_memory",
]

for name in _OPTIONAL_FUNCS:
    if hasattr(_system, name):
        globals()[name] = getattr(_system, name)

__version__ = "0.1.0"

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
    "physical_cpu_count",
    "disk_usage",
    "Process",
    "ProcessCPUTimes",
    "ProcessSignalMasks",
    "ProcessStatus",
    "Popen",
    "pid_exists",
    "pids",
    "process_iter",
    "process_iter_available",
    "wait_procs",
    "CPUFrequencies",
    "CPUStats",
    "DiskUsage",
    "ProcessSignalMasks",
    "Uids",
    "Gids",
    "Error",
    "NoSuchProcess",
    "ZombieProcess",
    "AccessDenied",
    "TimeoutExpired",
]

for name in _OPTIONAL_FUNCS:
    if name in globals():
        __all__.append(name)

PROCFS_PATH = "/proc"
