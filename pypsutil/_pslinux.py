# pylint: disable=too-many-lines
import ctypes
import dataclasses
import os
import resource
import signal
import sys
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
    no_type_check,
)

from . import _cache, _ffi, _psposix, _util
from ._errors import AccessDenied, ZombieProcess
from ._util import ProcessCPUTimes, ProcessStatus

if TYPE_CHECKING:  # pragma: no cover
    from ._process import Process


@dataclasses.dataclass
class ProcessOpenFile(_util.ProcessOpenFile):
    position: int
    flags: int

    @property
    def mode(self) -> str:
        if self.flags & os.O_WRONLY == os.O_WRONLY:
            if self.flags & os.O_APPEND == os.O_APPEND:
                return "a"
            else:
                return "w"
        elif self.flags & os.O_RDWR == os.O_RDWR:
            if self.flags & os.O_APPEND == os.O_APPEND:
                return "a+"
            else:
                return "r+"
        else:
            return "r"


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


@dataclasses.dataclass
class ProcessMemoryInfo:
    rss: int
    vms: int
    shared: int
    text: int
    data: int


PowerSupplySensorInfo = _util.PowerSupplySensorInfo
BatteryInfo = _util.BatteryInfo
BatteryStatus = _util.BatteryStatus
ACPowerInfo = _util.ACPowerInfo


@dataclasses.dataclass
class TempSensorInfo:
    label: str
    current: float
    high: Optional[float]
    critical: Optional[float]

    @property
    def current_farenheit(self) -> float:
        return self.current * 1.8 + 32

    @property
    def high_farenheit(self) -> Optional[float]:
        return (self.high * 1.8 + 32) if self.high is not None else None

    @property
    def critical_farenheit(self) -> Optional[float]:
        return (self.critical * 1.8 + 32) if self.critical is not None else None


SwapInfo = _util.SwapInfo
ThreadInfo = _util.ThreadInfo


def _get_sysfs_path() -> str:
    return sys.modules[__package__].SYSFS_PATH  # type: ignore


def parse_sigmask(raw_mask: str, *, include_internal: bool = False) -> Set[int]:
    return _util.expand_sig_bitmask(int(raw_mask, 16), include_internal=include_internal)


def _parse_procfs_stat_fields(line: str) -> List[str]:
    lparen = line.index("(")
    rparen = line.rindex(")")

    items = line[:lparen].split()
    items.append(line[lparen + 1: rparen])
    items.extend(line[rparen + 1:].split())

    return items


def _get_pid_stat_fields(pid: int) -> List[str]:
    try:
        with open(os.path.join(_util.get_procfs_path(), str(pid), "stat")) as file:
            line = file.readline().strip()
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex
    else:
        return _parse_procfs_stat_fields(line)


@_cache.CachedByProcess
def _get_proc_stat_fields(proc: "Process") -> List[str]:
    return _get_pid_stat_fields(proc.pid)


@_cache.CachedByProcess
def _get_proc_status_text(proc: "Process") -> str:
    try:
        return _util.read_file(os.path.join(_util.get_procfs_path(), str(proc.pid), "status"))
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex


def _iter_proc_status_entries(proc: "Process") -> Iterator[Tuple[str, str]]:
    for line in _get_proc_status_text(proc).splitlines():
        name, value = line.split(":\t", maxsplit=1)
        yield name, value.rstrip("\n")


def _get_proc_status_entry(proc: "Process", name: str) -> str:
    for entry_name, entry_value in _iter_proc_status_entries(proc):
        if entry_name == name:
            return entry_value

    raise KeyError


def pid_raw_create_time(pid: int) -> float:
    ctime_ticks = int(_get_pid_stat_fields(pid)[21])
    return ctime_ticks / _util.CLK_TCK


def translate_create_time(raw_create_time: float) -> float:
    return _internal_boot_time() + raw_create_time


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


def _remove_deleted_suffix(fname: str) -> str:
    return fname[:-10] if fname.endswith(" (deleted)") else fname


def proc_cwd(proc: "Process") -> str:
    try:
        return _remove_deleted_suffix(
            os.readlink(os.path.join(_util.get_procfs_path(), str(proc.pid), "cwd"))
        )
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
        return _remove_deleted_suffix(os.readlink("exe", dir_fd=pid_fd))
    except FileNotFoundError:
        return ""
    finally:
        os.close(pid_fd)  # pytype: disable=bad-return-type


def proc_root(proc: "Process") -> str:
    try:
        return _remove_deleted_suffix(
            os.readlink(os.path.join(_util.get_procfs_path(), str(proc.pid), "root"))
        )
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex


def proc_open_files(proc: "Process") -> List[ProcessOpenFile]:
    results = []

    proc_dir = os.path.join(_util.get_procfs_path(), str(proc.pid))

    try:
        for name in os.listdir(os.path.join(proc_dir, "fd")):
            fd = int(name)

            try:
                path = os.readlink(os.path.join(proc_dir, "fd", name))
                if path[0] != "/":
                    continue

                if not os.path.isfile(path):
                    continue

                position = None
                flags = None
                with open(os.path.join(proc_dir, "fdinfo", name)) as file:
                    for line in file:
                        if line.startswith("pos:"):
                            position = int(line[4:].strip())
                        elif line.startswith("flags:"):
                            flags = int(line[6:].strip(), 8)

                        if position is not None and flags is not None:
                            break
                    else:
                        # "pos" and/or "flags" fields not found; skip
                        continue

            except FileNotFoundError:
                pass
            else:
                results.append(
                    ProcessOpenFile(  # pytype: disable=wrong-keyword-args
                        fd=fd, path=path, flags=flags, position=position
                    )
                )

    except FileNotFoundError as ex:
        raise ProcessLookupError from ex
    else:
        return results


def proc_num_fds(proc: "Process") -> int:
    try:
        return len(os.listdir(os.path.join(_util.get_procfs_path(), str(proc.pid), "fd")))
    except FileNotFoundError as ex:
        raise ProcessLookupError from ex


def proc_num_threads(proc: "Process") -> int:
    if proc._is_cache_enabled():  # pylint: disable=protected-access
        return int(_get_proc_stat_fields(proc)[19])
    else:
        # Surprisingly, this is actually faster than checking the field in /proc/$PID/stat
        try:
            return len(os.listdir(os.path.join(_util.get_procfs_path(), str(proc.pid), "task")))
        except FileNotFoundError as ex:
            raise ProcessLookupError from ex


def proc_threads(proc: "Process") -> List[ThreadInfo]:
    threads = []

    try:
        with os.scandir(os.path.join(_util.get_procfs_path(), str(proc.pid), "task")) as task_it:
            for entry in task_it:
                tid = int(entry.name)

                try:
                    with open(os.path.join(entry.path, "stat")) as file:
                        line = file.readline().strip()
                except FileNotFoundError:
                    pass
                else:
                    fields = _parse_procfs_stat_fields(line)

                    threads.append(
                        ThreadInfo(
                            id=tid,
                            user_time=int(fields[13]) / _util.CLK_TCK,
                            system_time=int(fields[14]) / _util.CLK_TCK,
                        )
                    )

    except FileNotFoundError as ex:
        raise ProcessLookupError from ex
    else:
        return threads


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
    if proc._is_cache_enabled():  # pylint: disable=protected-access
        return _get_proc_stat_fields(proc)[1]
    else:
        try:
            return _util.read_file_first_line(
                os.path.join(_util.get_procfs_path(), str(proc.pid), "comm")
            )
        except FileNotFoundError as ex:
            raise ProcessLookupError from ex


def proc_ppid(proc: "Process") -> int:
    return int(_get_proc_stat_fields(proc)[3])


def proc_uids(proc: "Process") -> Tuple[int, int, int]:
    ruid, euid, suid, _ = map(int, _get_proc_status_entry(proc, "Uid").split())
    return ruid, euid, suid


def proc_gids(proc: "Process") -> Tuple[int, int, int]:
    rgid, egid, sgid, _ = map(int, _get_proc_status_entry(proc, "Gid").split())
    return rgid, egid, sgid


def proc_fsuid(proc: "Process") -> int:
    return int(_get_proc_status_entry(proc, "Uid").rsplit(maxsplit=1)[1])


def proc_fsgid(proc: "Process") -> int:
    return int(_get_proc_status_entry(proc, "Gid").rsplit(maxsplit=1)[1])


def proc_getgroups(proc: "Process") -> List[int]:
    return list(map(int, _get_proc_status_entry(proc, "Groups").split()))


def proc_umask(proc: "Process") -> Optional[int]:
    for name, value in _iter_proc_status_entries(proc):
        if name == "State":
            if value.startswith("Z"):
                raise ZombieProcess(proc.pid)  # pylint: disable=raise-missing-from
        elif name == "Umask":
            return int(value, 8)

    return None


def proc_sigmasks(proc: "Process", *, include_internal: bool = False) -> ProcessSignalMasks:
    process_pending = set()
    pending = set()
    blocked = set()
    ignored = set()
    caught = set()

    for name, value in _iter_proc_status_entries(proc):
        if name == "ShdPnd":
            process_pending = parse_sigmask(value, include_internal=include_internal)
        elif name == "SigPnd":
            pending = parse_sigmask(value, include_internal=include_internal)
        elif name == "SigBlk":
            blocked = parse_sigmask(value, include_internal=include_internal)
        elif name == "SigIgn":
            ignored = parse_sigmask(value, include_internal=include_internal)
        elif name == "SigCgt":
            caught = parse_sigmask(value, include_internal=include_internal)

    return ProcessSignalMasks(  # pytype: disable=wrong-keyword-args
        process_pending=process_pending,
        pending=pending,
        blocked=blocked,
        ignored=ignored,
        caught=caught,
    )


def proc_cpu_times(proc: "Process") -> ProcessCPUTimes:
    fields = _get_proc_stat_fields(proc)

    return ProcessCPUTimes(
        user=int(fields[13]) / _util.CLK_TCK,
        system=int(fields[14]) / _util.CLK_TCK,
        children_user=int(fields[15]) / _util.CLK_TCK,
        children_system=int(fields[16]) / _util.CLK_TCK,
    )


if hasattr(resource, "prlimit"):

    @no_type_check
    def proc_rlimit(
        proc: "Process", res: int, new_limits: Optional[Tuple[int, int]] = None
    ) -> Tuple[int, int]:
        if new_limits is None:
            return (
                resource.prlimit(  # pylint: disable=no-member  # pytype: disable=missing-parameter
                    proc.pid, res
                )
            )
        else:
            return resource.prlimit(proc.pid, res, new_limits)  # pylint: disable=no-member


else:
    # PyPy doesn't have resource.prlimit() (!)
    rlim_t = ctypes.c_uint64  # pylint: disable=invalid-name
    rlimit_max_value = _ffi.ctypes_int_max(rlim_t)

    class Rlimit(ctypes.Structure):  # pylint: disable=too-few-public-methods
        _fields_ = [
            ("rlim_cur", rlim_t),
            ("rlim_max", rlim_t),
        ]

        @classmethod
        def construct_opt(cls, limits: Optional[Tuple[int, int]]) -> Optional["Rlimit"]:
            if limits is not None:
                soft, hard = limits

                if soft > rlimit_max_value or hard > rlimit_max_value:
                    raise OverflowError("resource limit value is too large")

                return cls(rlim_cur=soft, rlim_max=hard)
            else:
                return None

    libc = _ffi.load_libc()
    libc.prlimit.argtypes = (
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(Rlimit),
        ctypes.POINTER(Rlimit),
    )
    libc.prlimit.restype = ctypes.c_int

    def proc_rlimit(
        proc: "Process", res: int, new_limits: Optional[Tuple[int, int]] = None
    ) -> Tuple[int, int]:
        _util.check_rlimit_resource(res)

        new_limits_raw = Rlimit.construct_opt(new_limits)

        old_limits = Rlimit(rlim_cur=resource.RLIM_INFINITY, rlim_max=resource.RLIM_INFINITY)

        if libc.prlimit(proc.pid, res, new_limits_raw, old_limits) < 0:
            raise _ffi.build_oserror(ctypes.get_errno())

        return old_limits.rlim_cur, old_limits.rlim_max


proc_rlimit.is_atomic = True

proc_getrlimit = proc_rlimit


def proc_tty_rdev(proc: "Process") -> Optional[int]:
    tty_nr = int(_get_proc_stat_fields(proc)[6])
    return tty_nr if tty_nr != 0 else None


def proc_cpu_num(proc: "Process") -> int:
    return int(_get_proc_stat_fields(proc)[38])


def proc_memory_info(proc: "Process") -> ProcessMemoryInfo:
    try:
        with open(os.path.join(_util.get_procfs_path(), str(proc.pid), "statm")) as file:
            items = list(map(int, file.readline().split()))

    except FileNotFoundError as ex:
        raise ProcessLookupError from ex
    else:
        return ProcessMemoryInfo(
            vms=items[0] * _util.PAGESIZE,
            rss=items[1] * _util.PAGESIZE,
            shared=items[2] * _util.PAGESIZE,
            text=items[3] * _util.PAGESIZE,
            data=items[5] * _util.PAGESIZE,
        )


def iter_pids() -> Iterator[int]:
    for name in os.listdir(_util.get_procfs_path()):
        try:
            yield int(name)
        except ValueError:
            pass


def iter_pid_raw_create_time(*, skip_perm_error: bool = False) -> Iterator[Tuple[int, float]]:
    for name in os.listdir(_util.get_procfs_path()):
        try:
            pid = int(name)
        except ValueError:
            continue

        try:
            ctime = pid_raw_create_time(pid)
        except ProcessLookupError:
            continue
        except PermissionError as ex:
            if skip_perm_error:
                continue
            else:
                raise AccessDenied(pid=pid) from ex

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
                if cur_info:
                    cpu_infos.append(cur_info)
                cur_info = {}

        if cur_info:
            cpu_infos.append(cur_info)

        return len({(info["physical id"], info["core id"]) for info in cpu_infos}) or None
    except (FileNotFoundError, KeyError):
        return None


def percpu_freq() -> List[Tuple[float, float, float]]:
    # First, try looking in /sys/devices/system
    # This allows us to get the current, minimum, and maximum frequencies.
    try:
        cpu_device_dir = os.path.join(_get_sysfs_path(), "devices/system/cpu")
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
                    int(_util.read_file_first_line(os.path.join(cpufreq_path, "scaling_cur_freq")))
                    / 1000,
                    int(_util.read_file_first_line(os.path.join(cpufreq_path, "scaling_min_freq")))
                    / 1000,
                    int(_util.read_file_first_line(os.path.join(cpufreq_path, "scaling_max_freq")))
                    / 1000,
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
            return CPUTimes(*(int(item) / _util.CLK_TCK for item in entry[1:11]))

    raise RuntimeError("'cpu' entry not found in /proc/stat")


def percpu_times() -> List[CPUTimes]:
    return [
        CPUTimes(*(int(item) / _util.CLK_TCK for item in entry[1:11]))
        for entry in _iter_procfs_stat_entries()
        if entry[0].startswith("cpu") and len(entry[0]) > 3
    ]


def _get_raw_meminfo() -> Dict[str, int]:
    raw_meminfo = {}
    with open(os.path.join(_util.get_procfs_path(), "meminfo")) as file:
        for line in file:
            line = line.strip()
            if line.endswith(" kB"):
                key, value = line[:-3].split()
                raw_meminfo[key.rstrip(":")] = int(value) * 1024

    return raw_meminfo


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
    raw_meminfo = _get_raw_meminfo()

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
    raw_meminfo = _get_raw_meminfo()

    swap_in = 0
    swap_out = 0
    with open(os.path.join(_util.get_procfs_path(), "vmstat")) as file:
        for line in file:
            if line.startswith("pswpin "):
                swap_in = int(line[7:].strip()) * 4096
            elif line.startswith("pswpout "):
                swap_out = int(line[8:].strip()) * 4096

    return SwapInfo(
        total=raw_meminfo["SwapTotal"],
        used=raw_meminfo["SwapTotal"] - raw_meminfo["SwapFree"],
        sin=swap_in,
        sout=swap_out,
    )


T = TypeVar("T")


class PowerSupplyInfo:
    _empty = object()

    def __init__(self, name: str, path: str) -> None:
        self.name = name
        self.data = {"name": name}
        self.path = path

        # The "uevent" file usually gives us a lot of information in one shot,
        # so let's try that.
        try:
            with open(os.path.join(self.path, "uevent")) as file:
                for line in file:
                    key, value = line.strip().split("=")
                    if key.startswith("POWER_SUPPLY_"):
                        self.data[key[13:].lower()] = value

        except OSError:
            pass

    def get(self, key: str, default: T) -> Union[str, T]:
        if "/" in key:
            # Paranoid sanity check
            return default

        value: Any

        if key in self.data:
            value = self.data[key]
        else:
            try:
                # Try reading the file with the corresponding name
                value = _util.read_file_first_line(os.path.join(self.path, key))
            except OSError:
                value = self._empty

            self.data[key] = value

        return (
            default
            if value is self._empty
            else cast(Union[str, T], value)  # pytype: disable=invalid-typevar
        )

    def __contains__(self, key: str) -> bool:
        return self.get(key, None) is not None

    def __getitem__(self, key: str) -> str:
        value = self.get(key, None)
        if value is None:
            raise KeyError
        else:
            return value


def _iter_power_supply_info() -> Iterator[PowerSupplyInfo]:
    power_supply_dir = os.path.join(_get_sysfs_path(), "class/power_supply")

    try:
        for name in sorted(os.listdir(power_supply_dir)):
            yield PowerSupplyInfo(name, os.path.join(power_supply_dir, name))
    except FileNotFoundError:
        pass


def _iter_sensors_power() -> Iterator[Union[BatteryInfo, ACPowerInfo]]:
    for supply in _iter_power_supply_info():
        ps_type = supply.get("type", "").lower()

        if ps_type == "battery":
            ps_status_text = supply.get("status", "unknown").lower()

            status = {
                "full": BatteryStatus.FULL,
                "charging": BatteryStatus.CHARGING,
                "discharging": BatteryStatus.DISCHARGING,
            }.get(ps_status_text, BatteryStatus.UNKNOWN)

            voltage = None
            for name in ["voltage_min_design", "voltage_min", "voltage_now", "voltage_boot"]:
                if name in supply:
                    voltage = int(supply[name]) / 1000000
                    break

            energy_now = None
            energy_full = None
            power_now = None

            if "power_now" in supply:
                power_now = int(supply["power_now"])
            elif voltage is not None and "current_now" in supply:
                power_now = int(int(supply["current_now"]) * voltage)

            if "energy_now" in supply:
                energy_now = int(supply["energy_now"])
            elif voltage is not None and "charge_now" in supply:
                energy_now = int(int(supply["charge_now"]) * voltage)

            if "energy_full" in supply:
                energy_full = int(supply["energy_full"])
            elif voltage is not None and "charge_full" in supply:
                energy_full = int(int(supply["charge_full"]) * voltage)

            # We can determine the percent capacity more accurately if the "charge"/"energy"
            # fields are present
            if energy_now is not None and energy_full is not None:
                percent = energy_now * 100 / energy_full
            elif "capacity" in supply:
                percent = float(int(supply["capacity"]))
            else:
                # We can't even determine the percent capacity. Something is wrong.
                continue

            yield BatteryInfo(
                name=supply.name,
                power_now=power_now,
                energy_now=energy_now,
                energy_full=energy_full,
                percent=percent,
                status=status,
            )

        elif ps_type == "mains" and "online" in supply:
            yield ACPowerInfo(
                name=supply.name,
                is_online=bool(int(supply["online"])),
            )


def sensors_power() -> PowerSupplySensorInfo:
    batteries = []
    ac_supplies = []

    for info in _iter_sensors_power():
        if isinstance(info, BatteryInfo):
            batteries.append(info)
        else:
            ac_supplies.append(info)

    return PowerSupplySensorInfo(batteries=batteries, ac_supplies=ac_supplies)


def sensors_is_on_ac_power() -> Optional[bool]:
    return sensors_power().is_on_ac_power


def sensors_temperatures() -> Dict[str, List[TempSensorInfo]]:
    results = {}

    try:
        with os.scandir(os.path.join(_get_sysfs_path(), "class/hwmon")) as hwmon_it:
            for hwmon_entry in hwmon_it:
                hwmon_name = _util.read_file_first_line(os.path.join(hwmon_entry.path, "name"))

                sensor_names = {
                    name.split("_")[0]
                    for name in os.listdir(hwmon_entry.path)
                    if name.startswith("temp") and name.endswith("_input")
                }
                if not sensor_names:
                    continue

                sensor_infos = []

                for sensor_name in sorted(sensor_names, key=lambda name: int(name[4:])):
                    try:
                        label = _util.read_file_first_line(
                            os.path.join(hwmon_entry.path, sensor_name + "_label")
                        ).strip()
                    except FileNotFoundError:
                        label = ""

                    current = (
                        int(
                            _util.read_file_first_line(
                                os.path.join(hwmon_entry.path, sensor_name + "_input")
                            )
                        )
                        / 1000
                    )

                    critical: Optional[float]
                    try:
                        critical = (
                            int(
                                _util.read_file_first_line(
                                    os.path.join(hwmon_entry.path, sensor_name + "_crit")
                                )
                            )
                            / 1000
                        )
                    except FileNotFoundError:
                        critical = None

                    high: Optional[float]
                    try:
                        high = (
                            int(
                                _util.read_file_first_line(
                                    os.path.join(hwmon_entry.path, sensor_name + "_max")
                                )
                            )
                            / 1000
                        )
                    except FileNotFoundError:
                        high = critical

                    sensor_infos.append(
                        TempSensorInfo(label=label, current=current, high=high, critical=critical)
                    )

                results[hwmon_name] = sensor_infos

    except FileNotFoundError:
        pass

    return results


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
