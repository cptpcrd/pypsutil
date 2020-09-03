from . import _system
from ._detect import BSD, FREEBSD, LINUX, MACOS, NETBSD, OPENBSD
from ._errors import AccessDenied, Error, NoSuchProcess, TimeoutExpired, ZombieProcess
from ._process import (
    Gids,
    Popen,
    Process,
    ProcessCPUTimes,
    ProcessMemoryInfo,
    ProcessOpenFile,
    ProcessSignalMasks,
    ProcessStatus,
    ThreadInfo,
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
    "ACPowerInfo",
    "BatteryInfo",
    "BatteryStatus",
    "sensors_power",
    "sensors_battery",
    "sensors_is_on_ac_power",
    "TempSensorInfo",
    "sensors_temperatures",
]

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
    "ProcessMemoryInfo",
    "ProcessOpenFile",
    "ProcessSignalMasks",
    "ProcessStatus",
    "Popen",
    "ThreadInfo",
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
    if hasattr(_system, name):
        globals()[name] = getattr(_system, name)
        __all__.append(name)

PROCFS_PATH = "/proc"

if LINUX:
    SYSFS_PATH = "/sys"
    __all__.append("SYSFS_PATH")
