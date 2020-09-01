import dataclasses
import os
import resource
import signal
import time
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Set, Tuple, Union, no_type_check

from . import _cache, _psposix, _util
from ._errors import AccessDenied, NoSuchProcess, ZombieProcess
from ._util import ProcessCPUTimes, ProcessStatus, translate_proc_errors

if TYPE_CHECKING:
    from ._process import Process


@dataclasses.dataclass
class ProcessSignalMasks(_util.ProcessSignalMasks):
    process_pending: Set[Union[signal.Signals, int]]  # pylint: disable=no-member


@dataclasses.dataclass
class CPUTimes:  # pylint: disable=too-many-instance-attributes
    # The order of these fields must match the order of the "cpu" entries in /proc/stat
    user: float
    nice: float
    system: float
    idle: float
    iowait: float
    irq: float
    softirq: float
    steal: float
    guest: float
    guest_nice: float


@dataclasses.dataclass
class VirtualMemoryInfo:  # pylint: disable=too-many-instance-attributes
    total: int
    available: int
    used: int
    free: int
    active: int
    inactive: int
    buffers: int
    cached: int
    shared: int
    slab: int

    @property
    def percent(self) -> float:
        return 100 - self.available * 100.0 / self.total


SwapInfo = _util.SwapInfo


def parse_sigmask(raw_mask: str, *, include_internal: bool = False) -> Set[int]:
    return _util.expand_sig_bitmask(int(raw_mask, 16), include_internal=include_internal)


def _get_pid_stat_fields(pid: int) -> List[str]:
    try:
        with open(os.path.join(_util.get_procfs_path(), str(pid), "stat")) as file:
            line = file.readline().strip()

        lparen = line.index("(")
        rparen = line.rindex(")")

        items = line[:lparen].split()
        items.append(line[lparen + 1: rparen])
        items.extend(line[rparen + 1:].split())

        return items
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex


@_cache.CachedByProcess
def _get_proc_stat_fields(proc: "Process") -> List[str]:
    return _get_pid_stat_fields(proc.pid)


@_cache.CachedByProcess
def _get_proc_status_dict(proc: "Process") -> Dict[str, str]:
    try:
        res = {}

        with open(os.path.join(_util.get_procfs_path(), str(proc.pid), "status")) as file:
            for line in file:
                name, value = line.split(":\t", maxsplit=1)
                res[name] = value.rstrip("\n")

        return res
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex


_clk_tck = os.sysconf(os.sysconf_names["SC_CLK_TCK"])


@translate_proc_errors
def pid_create_time(pid: int) -> float:
    ctime_ticks = int(_get_pid_stat_fields(pid)[21])
    return _internal_boot_time() + ctime_ticks / _clk_tck


_PROC_STATUSES = {
    "R": ProcessStatus.RUNNING,
    "S": ProcessStatus.SLEEPING,
    "D": ProcessStatus.DISK_SLEEP,
    "Z": ProcessStatus.ZOMBIE,
    "T": ProcessStatus.STOPPED,
    "t": ProcessStatus.TRACING_STOP,
    "X": ProcessStatus.DEAD,
    "x": ProcessStatus.DEAD,
    "K": ProcessStatus.WAKE_KILL,
    "W": ProcessStatus.WAKING,
    "P": ProcessStatus.PARKED,
    "I": ProcessStatus.IDLE,
}


def proc_status(proc: "Process") -> ProcessStatus:
    return _PROC_STATUSES[_get_proc_stat_fields(proc)[2]]


def proc_cwd(proc: "Process") -> str:
    try:
        return os.readlink(os.path.join(_util.get_procfs_path(), str(proc.pid), "cwd"))
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex


def proc_exe(proc: "Process") -> str:
    # We need to distinguish between two meanings of ENOENT:
    # 1. /proc/<pid> doesn't exist -> the process is dead
    # 2. /proc/<pid>/exe doesn't exist (happens for some kernel processes; we should return an
    #    empty string)
    #
    # So we open a directory file descriptor to /proc/<pid>, then call readlinkat().

    try:
        pid_fd = os.open(
            os.path.join(_util.get_procfs_path(), str(proc.pid)), os.O_RDONLY | os.O_DIRECTORY
        )
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex

    try:
        return os.readlink("exe", dir_fd=pid_fd)
    except FileNotFoundError:
        return ""
    finally:
        os.close(pid_fd)


def proc_root(proc: "Process") -> str:
    try:
        return os.readlink(os.path.join(_util.get_procfs_path(), str(proc.pid), "root"))
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex


def proc_num_fds(proc: "Process") -> int:
    try:
        return len(os.listdir(os.path.join(_util.get_procfs_path(), str(proc.pid), "fd")))
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex


def proc_num_threads(proc: "Process") -> int:
    try:
        return len(os.listdir(os.path.join(_util.get_procfs_path(), str(proc.pid), "task")))
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex


def proc_cmdline(proc: "Process") -> List[str]:
    try:
        with open(os.path.join(_util.get_procfs_path(), str(proc.pid), "cmdline"), "rb") as file:
            cmdline = file.read()
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex

    if not cmdline:
        if proc_status(proc) == ProcessStatus.ZOMBIE:
            raise ZombieProcess(proc.pid)
        else:
            return []

    return _util.parse_cmdline_bytes(cmdline)


def proc_environ(proc: "Process") -> Dict[str, str]:
    try:
        with open(os.path.join(_util.get_procfs_path(), str(proc.pid), "environ"), "rb") as file:
            env_data = file.read()
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex

    return _util.parse_environ_bytes(env_data)


def proc_name(proc: "Process") -> str:
    return _get_proc_stat_fields(proc)[1]


def proc_ppid(proc: "Process") -> int:
    return int(_get_proc_stat_fields(proc)[3])


def proc_uids(proc: "Process") -> Tuple[int, int, int]:
    ruid, euid, suid, _ = map(int, _get_proc_status_dict(proc)["Uid"].split())
    return ruid, euid, suid


def proc_gids(proc: "Process") -> Tuple[int, int, int]:
    rgid, egid, sgid, _ = map(int, _get_proc_status_dict(proc)["Gid"].split())
    return rgid, egid, sgid


def proc_getgroups(proc: "Process") -> List[int]:
    return list(map(int, _get_proc_status_dict(proc)["Groups"].split()))


def proc_umask(proc: "Process") -> Optional[int]:
    proc_status_info = _get_proc_status_dict(proc)

    try:
        umask_str = proc_status_info["Umask"]
    except KeyError:
        if proc_status_info["State"].startswith("Z"):
            raise ZombieProcess(proc.pid)  # pylint: disable=raise-missing-from
        else:
            return None
    else:
        return int(umask_str, 8)


def proc_sigmasks(proc: "Process", *, include_internal: bool = False) -> ProcessSignalMasks:
    proc_status_info = _get_proc_status_dict(proc)

    return ProcessSignalMasks(  # pytype: disable=wrong-keyword-args
        process_pending=parse_sigmask(
            proc_status_info["ShdPnd"], include_internal=include_internal
        ),
        pending=parse_sigmask(proc_status_info["SigPnd"], include_internal=include_internal),
        blocked=parse_sigmask(proc_status_info["SigBlk"], include_internal=include_internal),
        ignored=parse_sigmask(proc_status_info["SigIgn"], include_internal=include_internal),
        caught=parse_sigmask(proc_status_info["SigCgt"], include_internal=include_internal),
    )


def proc_cpu_times(proc: "Process") -> ProcessCPUTimes:
    fields = _get_proc_stat_fields(proc)

    return ProcessCPUTimes(
        user=int(fields[13]) / _clk_tck,
        system=int(fields[14]) / _clk_tck,
        children_user=int(fields[15]) / _clk_tck,
        children_system=int(fields[16]) / _clk_tck,
    )


@no_type_check
def proc_rlimit(
    proc: "Process", res: int, new_limits: Optional[Tuple[int, int]] = None
) -> Tuple[int, int]:
    if new_limits is None:
        return resource.prlimit(  # pylint: disable=no-member  # pytype: disable=missing-parameter
            proc.pid, res
        )
    else:
        return resource.prlimit(proc.pid, res, new_limits)  # pylint: disable=no-member


proc_getrlimit = proc_rlimit


def proc_tty_rdev(proc: "Process") -> Optional[int]:
    tty_nr = int(_get_proc_stat_fields(proc)[6])
    return tty_nr if tty_nr != 0 else None


def iter_pids() -> Iterator[int]:
    for name in os.listdir(_util.get_procfs_path()):
        try:
            yield int(name)
        except ValueError:
            pass


def iter_pid_create_time(*, skip_perm_error: bool = False) -> Iterator[Tuple[int, float]]:
    for name in os.listdir(_util.get_procfs_path()):
        try:
            pid = int(name)
        except ValueError:
            continue

        try:
            ctime = pid_create_time(pid)
        except NoSuchProcess:
            continue
        except AccessDenied:
            if skip_perm_error:
                continue
            else:
                raise

        yield (pid, ctime)


def _iter_procfs_cpuinfo_entries() -> Iterator[Tuple[str, str]]:
    with open(os.path.join(_util.get_procfs_path(), "cpuinfo")) as file:
        for line in file:
            if ":" in line:
                name, value = line.split(":", maxsplit=1)
                yield (name.strip(), value.strip())
            else:
                yield ("", "")


def _iter_procfs_stat_entries() -> Iterator[List[str]]:
    with open(os.path.join(_util.get_procfs_path(), "stat")) as file:
        for line in file:
            yield line.split()


def physical_cpu_count() -> Optional[int]:
    try:
        cpu_infos = []
        cur_info = {}

        for name, value in _iter_procfs_cpuinfo_entries():
            if name:
                cur_info[name] = value
            else:
                cpu_infos.append(cur_info)
                cur_info = {}

    except FileNotFoundError:
        return None
    else:
        return len({(info["physical id"], info["core id"]) for info in cpu_infos})


def percpu_freq() -> List[Tuple[float, float, float]]:
    # First, try looking in /sys/devices/system
    # This allows us to get the current, minimum, and maximum frequencies.
    try:
        cpu_device_dir = "/sys/devices/system/cpu"
        names = [
            name
            for name in os.listdir(cpu_device_dir)
            if name.startswith("cpu") and name[3:].isdigit()
        ]
        names.sort(key=lambda name: int(name[3:]))

        results = []

        for name in names:
            cpufreq_path = os.path.join(cpu_device_dir, name, "cpufreq")

            results.append(
                (
                    int(_util.read_file(os.path.join(cpufreq_path, "scaling_cur_freq"))) / 1000,
                    int(_util.read_file(os.path.join(cpufreq_path, "scaling_min_freq"))) / 1000,
                    int(_util.read_file(os.path.join(cpufreq_path, "scaling_max_freq"))) / 1000,
                )
            )

    except (FileNotFoundError, PermissionError):
        pass
    else:
        if results:
            return results

    # If that fails. try /proc/cpuinfo
    # This only allows us to get the current frequency, but at least it's something.
    try:
        return [
            (float(value), 0.0, 0.0)
            for name, value in _iter_procfs_cpuinfo_entries()
            if name == "cpu MHz"
        ]
    except (FileNotFoundError, PermissionError):
        return []


def cpu_freq() -> Optional[Tuple[float, float, float]]:
    freqs = percpu_freq()
    if not freqs:
        return None

    cur_total = 0.0
    min_total = 0.0
    max_total = 0.0

    for cur_freq, min_freq, max_freq in freqs:
        cur_total += cur_freq
        min_total += min_freq
        max_total += max_freq

    return cur_total / len(freqs), min_total / len(freqs), max_total / len(freqs)


def cpu_stats() -> Tuple[int, int, int, int]:
    ctx_switches = 0
    interrupts = 0
    soft_interrupts = 0

    for entry in _iter_procfs_stat_entries():
        if entry[0] == "ctxt":
            ctx_switches = int(entry[1])
        elif entry[0] == "intr":
            interrupts = int(entry[1])
        elif entry[0] == "softirq":
            soft_interrupts = int(entry[1])

    return (ctx_switches, interrupts, soft_interrupts, 0)


def cpu_times() -> CPUTimes:
    for entry in _iter_procfs_stat_entries():
        if entry[0] == "cpu":
            return CPUTimes(*(int(item) / _clk_tck for item in entry[1:]))

    raise RuntimeError("'cpu' entry not found in /proc/stat")


def percpu_times() -> List[CPUTimes]:
    return [
        CPUTimes(*(int(item) / _clk_tck for item in entry[1:]))
        for entry in _iter_procfs_stat_entries()
        if entry[0].startswith("cpu") and len(entry[0]) > 3
    ]


VMEM_NAME_MAPPINGS = {
    "total": "MemTotal",
    "available": "MemAvailable",
    "free": "MemFree",
    "active": "Active",
    "inactive": "Inactive",
    "buffers": "Buffers",
    "cached": "Cached",
    "shared": "Shmem",
    "slab": "Slab",
}


def virtual_memory() -> VirtualMemoryInfo:
    raw_meminfo = {}
    with open("/proc/meminfo") as file:
        for line in file:
            line = line.strip()
            if line.endswith(" kB"):
                key, value = line[:-3].split()
                raw_meminfo[key.rstrip(":")] = int(value) * 1024

    info_dict = {name: raw_meminfo[raw_name] for name, raw_name in VMEM_NAME_MAPPINGS.items()}

    return VirtualMemoryInfo(
        used=(
            raw_meminfo["MemTotal"]
            - raw_meminfo["MemFree"]
            - raw_meminfo["Buffers"]
            - raw_meminfo["Cached"]
        ),
        **info_dict,
    )


def swap_memory() -> SwapInfo:
    raw_meminfo = {}
    with open("/proc/meminfo") as file:
        for line in file:
            line = line.strip()
            if line.endswith(" kB"):
                key, value = line[:-3].split()
                raw_meminfo[key.rstrip(":")] = int(value) * 1024

    swap_in = 0
    swap_out = 0
    with open("/proc/vmstat") as file:
        for line in file:
            if line.startswith("pswpin "):
                swap_in = int(line[7:].strip()) * 4096
            elif line.startswith("pswpout "):
                swap_out = int(line[8:].strip()) * 4096

    return SwapInfo(
        total=raw_meminfo["SwapTotal"],
        free=raw_meminfo["SwapFree"],
        used=raw_meminfo["SwapTotal"] - raw_meminfo["SwapFree"],
        sin=swap_in,
        sout=swap_out,
    )


_cached_boot_time = None


def boot_time() -> float:
    global _cached_boot_time  # pylint: disable=global-statement

    # Round the result to reduce small variations.
    btime = round(time.time() - time_since_boot(), 4)

    _cached_boot_time = btime
    return btime


def _internal_boot_time() -> float:
    return _cached_boot_time if _cached_boot_time is not None else boot_time()


def time_since_boot() -> float:
    return time.clock_gettime(time.CLOCK_BOOTTIME)  # pylint: disable=no-member


def uptime() -> float:
    return time.clock_gettime(time.CLOCK_MONOTONIC)


proc_pgid = _psposix.proc_pgid
proc_sid = _psposix.proc_sid

proc_getpriority = _psposix.proc_getpriority

DiskUsage = _psposix.DiskUsage
disk_usage = _psposix.disk_usage
