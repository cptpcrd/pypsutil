# pylint: disable=too-few-public-methods
import ctypes
import dataclasses
import errno
import os
import time
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple, cast

from . import _bsd, _cache, _ffi, _psposix, _util
from ._util import ProcessCPUTimes, ProcessSignalMasks, ProcessStatus

if TYPE_CHECKING:
    from ._process import Process

CTL_KERN = 1
CTL_PROC = 10

PROC_PID_LIMIT = 2
PROC_PID_LIMIT_TYPE_SOFT = 1
PROC_PID_LIMIT_TYPE_HARD = 2

KERN_CP_TIME = 51
KERN_BOOTTIME = 83
KERN_PROC2 = 47
KERN_PROC_ARGS = 48
KERN_PROC_ALL = 0
KERN_PROC_PID = 1
KERN_PROC_ARGV = 1
KERN_PROC_ENV = 3
KERN_PROC_PATHNAME = 5
KERN_PROC_CWD = 6

KI_NGROUPS = 16
KI_MAXCOMLEN = 24
KI_WMESGLEN = 8
KI_MAXLOGNAME = 24
KI_MAXEMULLEN = 16

rlim_t = ctypes.c_uint64  # pylint: disable=invalid-name

time_t = ctypes.c_int64  # pylint: disable=invalid-name

rlimit_max_value = _ffi.ctypes_int_max(rlim_t)

_clk_tck = os.sysconf(os.sysconf_names["SC_CLK_TCK"])


def _proc_rlimit_getset(proc: "Process", res: int, new_limit: Optional[int], hard: bool) -> int:
    new_limit_raw = ctypes.byref(rlim_t(new_limit)) if new_limit is not None else None
    old_limit = rlim_t(0)

    _bsd.sysctl(  # pytype: disable=wrong-arg-types
        [
            CTL_PROC,
            proc.pid,
            PROC_PID_LIMIT,
            res + 1,
            (PROC_PID_LIMIT_TYPE_HARD if hard else PROC_PID_LIMIT_TYPE_SOFT),
        ],
        new_limit_raw,  # type: ignore
        old_limit,  # type: ignore
    )

    return old_limit.value


def proc_rlimit(
    proc: "Process", res: int, new_limits: Optional[Tuple[int, int]] = None
) -> Tuple[int, int]:
    _util.check_rlimit_resource(res)

    new_soft: Optional[int]
    new_hard: Optional[int]
    if new_limits is not None:
        new_soft = new_limits[0]
        new_hard = new_limits[1]

        if new_soft > rlimit_max_value or new_hard > rlimit_max_value:
            raise OverflowError("resource limit value is too large")
    else:
        new_soft = None
        new_hard = None

    old_soft: Optional[int]
    try:
        old_soft = _proc_rlimit_getset(proc, res, new_soft, False)
    except OSError as ex:
        if ex.errno == errno.EINVAL:
            old_soft = None
        else:
            raise

    old_hard = _proc_rlimit_getset(proc, res, new_hard, True)

    if old_soft is None:
        old_soft = _proc_rlimit_getset(proc, res, new_soft, False)

    return old_soft, old_hard


proc_getrlimit = proc_rlimit


@dataclasses.dataclass
class CPUTimes:
    # The order of these fields must match the order of the numbers returned by the kern.cp_time
    # sysctl
    # https://github.com/IIJ-NetBSD/netbsd-src/blob/master/sys/sys/sched.h#L136
    user: float
    nice: float
    system: float
    irq: float
    idle: float


class Timespec(ctypes.Structure):
    _fields_ = [
        ("tv_sec", time_t),
        ("tv_nsec", ctypes.c_long),
    ]

    def to_float(self) -> float:
        return cast(float, self.tv_sec + (self.tv_nsec / 1000000000.0))


class KiSigset(ctypes.Structure):
    _fields_ = [
        ("bits", (ctypes.c_uint32 * 4)),
    ]

    def pack(self) -> int:
        # https://github.com/IIJ-NetBSD/netbsd-src/blob/e4505e0610ceb1b2db8e2a9ed607b4bfa076aa2f/sys/sys/sigtypes.h

        return cast(int, self.bits[0])


class KinfoProc2(ctypes.Structure):
    _fields_ = [
        ("p_forw", ctypes.c_uint64),
        ("p_back", ctypes.c_uint64),
        ("p_paddr", ctypes.c_uint64),
        ("p_addr", ctypes.c_uint64),
        ("p_fd", ctypes.c_uint64),
        ("p_cwdi", ctypes.c_uint64),
        ("p_stats", ctypes.c_uint64),
        ("p_limit", ctypes.c_uint64),
        ("p_vmspace", ctypes.c_uint64),
        ("p_sigacts", ctypes.c_uint64),
        ("p_sess", ctypes.c_uint64),
        ("p_tsess", ctypes.c_uint64),
        ("p_ru", ctypes.c_uint64),
        ("p_eflag", ctypes.c_int32),
        ("p_exitsig", ctypes.c_int32),
        ("p_flag", ctypes.c_int32),
        ("p_pid", ctypes.c_int32),
        ("p_ppid", ctypes.c_int32),
        ("p_sid", ctypes.c_int32),
        ("p__pgid", ctypes.c_int32),
        ("p_tpgid", ctypes.c_int32),
        ("p_uid", ctypes.c_uint32),
        ("p_ruid", ctypes.c_uint32),
        ("p_gid", ctypes.c_uint32),
        ("p_rgid", ctypes.c_uint32),
        ("p_groups", (ctypes.c_uint32 * KI_NGROUPS)),
        ("p_ngroups", ctypes.c_int16),
        ("p_jobc", ctypes.c_int16),
        ("p_tdev", ctypes.c_uint32),
        ("p_estcpu", ctypes.c_uint32),
        ("p_rtime_sec", ctypes.c_uint32),
        ("p_rtime_usec", ctypes.c_uint32),
        ("p_cpticks", ctypes.c_int32),
        ("p_cptcpu", ctypes.c_uint32),
        ("p_swtime", ctypes.c_uint32),
        ("p_slptime", ctypes.c_uint32),
        ("p_schedflags", ctypes.c_int32),
        ("p_uticks", ctypes.c_uint64),
        ("p_sticks", ctypes.c_uint64),
        ("p_iticks", ctypes.c_uint64),
        ("p_tracep", ctypes.c_uint64),
        ("p_traceflag", ctypes.c_int32),
        ("p_holdcnt", ctypes.c_int32),
        ("p_siglist", KiSigset),
        ("p_sigmask", KiSigset),
        ("p_sigignore", KiSigset),
        ("p_sigcatch", KiSigset),
        ("p_stat", ctypes.c_int8),
        ("p_priority", ctypes.c_uint8),
        ("p_usrpri", ctypes.c_uint8),
        ("p_nice", ctypes.c_uint8),
        ("p_xstat", ctypes.c_uint16),
        ("p_acflag", ctypes.c_uint16),
        ("p_comm", (ctypes.c_char * KI_MAXCOMLEN)),
        ("p_wmesg", (ctypes.c_char * KI_WMESGLEN)),
        ("p_wchan", ctypes.c_uint64),
        ("p_login", (ctypes.c_char * KI_MAXLOGNAME)),
        ("p_vm_rssize", ctypes.c_int32),
        ("p_vm_tsize", ctypes.c_int32),
        ("p_vm_dsize", ctypes.c_int32),
        ("p_vm_ssize", ctypes.c_int32),
        ("p_uvalid", ctypes.c_int64),
        ("p_ustart_sec", ctypes.c_uint32),
        ("p_ustart_usec", ctypes.c_uint32),
        ("p_uutime_sec", ctypes.c_uint32),
        ("p_uutime_usec", ctypes.c_uint32),
        ("p_ustime_sec", ctypes.c_uint32),
        ("p_ustime_usec", ctypes.c_uint32),
        ("p_uru_maxrss", ctypes.c_uint64),
        ("p_uru_ixrss", ctypes.c_uint64),
        ("p_uru_idrss", ctypes.c_uint64),
        ("p_uru_isrss", ctypes.c_uint64),
        ("p_uru_minflt", ctypes.c_uint64),
        ("p_uru_majflt", ctypes.c_uint64),
        ("p_uru_nswap", ctypes.c_uint64),
        ("p_uru_inblock", ctypes.c_uint64),
        ("p_uru_oublock", ctypes.c_uint64),
        ("p_uru_msgsnd", ctypes.c_uint64),
        ("p_uru_msgrcv", ctypes.c_uint64),
        ("p_uru_nsignals", ctypes.c_uint64),
        ("p_uru_nvcsw", ctypes.c_uint64),
        ("p_uru_nivcsw", ctypes.c_uint64),
        ("p_uctime_sec", ctypes.c_uint32),
        ("p_uctime_usec", ctypes.c_uint32),
        ("p_cpuid", ctypes.c_uint64),
        ("p_realflag", ctypes.c_uint64),
        ("p_nlwps", ctypes.c_uint64),
        ("p_nrlwps", ctypes.c_uint64),
        ("p_realstat", ctypes.c_uint64),
        ("p_svuid", ctypes.c_uint64),
        ("p_svgid", ctypes.c_uint64),
        ("p_ename", (ctypes.c_char * KI_MAXEMULLEN)),
        ("p_vm_vsize", ctypes.c_int64),
        ("p_vm_msize", ctypes.c_int64),
    ]

    def get_groups(self) -> List[int]:
        return list(self.p_groups[: self.p_ngroups])


def _get_kinfo_proc2_pid(pid: int) -> KinfoProc2:
    proc_info = KinfoProc2()

    length = _bsd.sysctl(
        [CTL_KERN, KERN_PROC2, KERN_PROC_PID, pid, ctypes.sizeof(proc_info), 1], None, proc_info
    )

    if length == 0:
        raise ProcessLookupError

    return proc_info


@_cache.CachedByProcess
def _get_kinfo_proc2(proc: "Process") -> KinfoProc2:
    return _get_kinfo_proc2_pid(proc.pid)


def _list_kinfo_procs2() -> List[KinfoProc2]:
    kinfo_size = ctypes.sizeof(KinfoProc2)

    while True:
        nprocs = (
            _bsd.sysctl([CTL_KERN, KERN_PROC2, KERN_PROC_ALL, 0, kinfo_size, 1000000], None, None)
            // kinfo_size
        )

        proc_arr = (KinfoProc2 * nprocs)()

        try:
            nprocs = (
                _bsd.sysctl(
                    [CTL_KERN, KERN_PROC2, KERN_PROC_ALL, 0, kinfo_size, nprocs], None, proc_arr
                )
                // kinfo_size
            )
        except OSError as ex:
            # ENOMEM means a range error; retry
            if ex.errno != errno.ENOMEM:
                raise
        else:
            return proc_arr[:nprocs]


def iter_pid_create_time(
    *,
    skip_perm_error: bool = False,  # pylint: disable=unused-argument
) -> Iterator[Tuple[int, float]]:
    for kinfo in _list_kinfo_procs2():
        yield kinfo.p_pid, cast(float, kinfo.p_ustart_sec + kinfo.p_ustart_usec / 1000000.0)


def iter_pids() -> Iterator[int]:
    for kinfo in _list_kinfo_procs2():
        yield kinfo.p_pid


def pid_create_time(pid: int) -> float:
    kinfo = _get_kinfo_proc2_pid(pid)
    return cast(float, kinfo.p_ustart_sec + kinfo.p_ustart_usec / 1000000.0)


_PROC_STATUSES = {
    1: ProcessStatus.IDLE,
    2: ProcessStatus.RUNNING,
    3: ProcessStatus.STOPPED,
    4: ProcessStatus.STOPPED,
    5: ProcessStatus.ZOMBIE,
    6: ProcessStatus.DEAD,
}


def proc_status(proc: "Process") -> ProcessStatus:
    return _PROC_STATUSES[_get_kinfo_proc2(proc).p_stat]


def proc_name(proc: "Process") -> str:
    return cast(str, _get_kinfo_proc2(proc).p_comm.decode())


def proc_uids(proc: "Process") -> Tuple[int, int, int]:
    kinfo = _get_kinfo_proc2(proc)
    return kinfo.p_uid, kinfo.p_ruid, kinfo.p_svuid


def proc_gids(proc: "Process") -> Tuple[int, int, int]:
    kinfo = _get_kinfo_proc2(proc)
    return kinfo.p_gid, kinfo.p_rgid, kinfo.p_svgid


def proc_getgroups(proc: "Process") -> List[int]:
    return _get_kinfo_proc2(proc).get_groups()


def proc_cwd(proc: "Process") -> str:
    return _bsd.sysctl_bytes_retry(
        [CTL_KERN, KERN_PROC_ARGS, KERN_PROC_CWD, proc.pid], None, trim_nul=True
    ).decode()


def proc_exe(proc: "Process") -> str:
    return _bsd.sysctl_bytes_retry(
        [CTL_KERN, KERN_PROC_ARGS, KERN_PROC_PATHNAME, proc.pid], None, trim_nul=True
    ).decode()


def proc_cmdline(proc: "Process") -> List[str]:
    cmdline_nul = _bsd.sysctl_bytes_retry(
        [CTL_KERN, KERN_PROC_ARGS, KERN_PROC_ARGV, proc.pid], None
    )
    return _util.parse_cmdline_bytes(cmdline_nul)


def proc_environ(proc: "Process") -> Dict[str, str]:
    env_data = _bsd.sysctl_bytes_retry([CTL_KERN, KERN_PROC_ARGS, KERN_PROC_ENV, proc.pid], None)
    return _util.parse_environ_bytes(env_data)


def proc_sigmasks(proc: "Process", *, include_internal: bool = False) -> ProcessSignalMasks:
    kinfo = _get_kinfo_proc2(proc)

    return ProcessSignalMasks(
        pending=_util.expand_sig_bitmask(kinfo.p_siglist.pack(), include_internal=include_internal),
        blocked=_util.expand_sig_bitmask(kinfo.p_sigmask.pack(), include_internal=include_internal),
        ignored=_util.expand_sig_bitmask(
            kinfo.p_sigignore.pack(), include_internal=include_internal
        ),
        caught=_util.expand_sig_bitmask(kinfo.p_sigcatch.pack(), include_internal=include_internal),
    )


def proc_cpu_times(proc: "Process") -> ProcessCPUTimes:
    kinfo = _get_kinfo_proc2(proc)

    return ProcessCPUTimes(
        user=kinfo.p_uutime_sec + kinfo.p_uutime_usec / 1000000,
        system=kinfo.p_ustime_sec + kinfo.p_ustime_usec / 1000000,
        children_user=kinfo.p_uctime_sec + kinfo.p_uctime_usec / 1000000,
        children_system=kinfo.p_uctime_sec + kinfo.p_uctime_usec / 1000000,
    )


def proc_ppid(proc: "Process") -> int:
    return cast(int, _get_kinfo_proc2(proc).p_ppid)


def proc_pgid(proc: "Process") -> int:
    if proc.pid == 0 or proc._is_cache_enabled():  # pylint: disable=protected-access
        # Either a) pid=0, so we can't use getpgid() (because for that function
        # pid=0 means the current process) or b) we're in a oneshot() and
        # we should retrieve extra information.
        return cast(int, _get_kinfo_proc2(proc).p__pgid)
    else:
        return _psposix.proc_pgid(proc)


def proc_sid(proc: "Process") -> int:
    if proc.pid == 0 or proc._is_cache_enabled():  # pylint: disable=protected-access
        # Either a) pid=0, so we can't use getsid() (because for that function
        # pid=0 means the current process) or b) we're in a oneshot() and
        # we should retrieve extra information.
        return cast(int, _get_kinfo_proc2(proc).p_sid)
    else:
        return _psposix.proc_sid(proc)


def proc_getpriority(proc: "Process") -> int:
    if proc.pid == 0:
        # We don't call _get_kinfo_proc2() if pid != 0 and the cache is enabled because
        # Process.setpriority() can change the priority and make the cache invalid.
        return cast(int, _get_kinfo_proc2(proc).p_nice)
    else:
        return _psposix.proc_getpriority(proc)


def proc_tty_rdev(proc: "Process") -> Optional[int]:
    tdev = _get_kinfo_proc2(proc).p_tdev
    return tdev if tdev != 2 ** 32 - 1 else None


def cpu_times() -> CPUTimes:
    cptimes = (ctypes.c_uint64 * 5)()

    _bsd.sysctl([CTL_KERN, KERN_CP_TIME], None, cptimes)

    return CPUTimes(*(int(item) / _clk_tck for item in cptimes))


def percpu_times() -> List[CPUTimes]:
    results: List[CPUTimes] = []

    cptimes = (ctypes.c_uint64 * 5)()

    while True:
        try:
            _bsd.sysctl([CTL_KERN, KERN_CP_TIME, len(results)], None, cptimes)
        except FileNotFoundError:
            break
        else:
            results.append(CPUTimes(*(int(item) / _clk_tck for item in cptimes)))

    return results


def boot_time() -> float:
    btime = Timespec()
    _bsd.sysctl([CTL_KERN, KERN_BOOTTIME], None, btime)
    return btime.to_float()


def time_since_boot() -> float:
    # Round the result to reduce small variations
    return round(time.time() - boot_time(), 4)


DiskUsage = _psposix.DiskUsage
disk_usage = _psposix.disk_usage
