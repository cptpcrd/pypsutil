from . import _process, _system
from ._detect import BSD, FREEBSD, LINUX, MACOS, NETBSD, OPENBSD
from ._errors import AccessDenied, Error, NoSuchProcess, TimeoutExpired, ZombieProcess
from ._process import (
    Connection,
    ConnectionStatus,
    Gids,
    Popen,
    Process,
    ProcessCPUTimes,
    ProcessFd,
    ProcessFdType,
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
    ACPowerInfo,
    BatteryInfo,
    BatteryStatus,
    CPUFrequencies,
    CPUStats,
    DiskUsage,
    NetIOCounts,
    PowerSupplySensorInfo,
    SwapInfo,
    VirtualMemoryInfo,
    boot_time,
    disk_usage,
    physical_cpu_count,
    swap_memory,
    time_since_boot,
    virtual_memory,
)

_OPTIONAL_SYSTEM = [
    "uptime",
    "cpu_freq",
    "percpu_freq",
    "cpu_stats",
    "CPUTimes",
    "cpu_times",
    "percpu_times",
    "sensors_power",
    "sensors_battery",
    "sensors_battery_total",
    "sensors_is_on_ac_power",
    "TempSensorInfo",
    "sensors_temperatures",
    "net_connections",
    "net_io_counters",
    "pernic_net_io_counters",
]

_OPTIONAL_PROCESS = ["ProcessMemoryMap", "ProcessMemoryMapGrouped"]

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
    "ProcessFd",
    "ProcessFdType",
    "Connection",
    "ConnectionStatus",
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
    "SwapInfo",
    "VirtualMemoryInfo",
    "virtual_memory",
    "swap_memory",
    "PowerSupplySensorInfo",
    "ACPowerInfo",
    "BatteryInfo",
    "BatteryStatus",
    "NetIOCounts",
    "Uids",
    "Gids",
    "Error",
    "NoSuchProcess",
    "ZombieProcess",
    "AccessDenied",
    "TimeoutExpired",
]

for name in _OPTIONAL_SYSTEM:
    if hasattr(_system, name):
        globals()[name] = getattr(_system, name)
        __all__.append(name)

for name in _OPTIONAL_PROCESS:
    if hasattr(_process, name):
        globals()[name] = getattr(_process, name)
        __all__.append(name)

DEVFS_PATH = "/dev"

PROCFS_PATH = "/proc"

if LINUX:
    SYSFS_PATH = "/sys"
    __all__.append("SYSFS_PATH")
