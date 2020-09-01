# pylint: disable=too-few-public-methods
import ctypes
import dataclasses
import errno
import os
import time
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple, cast

from . import _bsd, _cache, _psposix, _util
from ._util import ProcessCPUTimes, ProcessSignalMasks, ProcessStatus

if TYPE_CHECKING:
    from ._process import Process

CTL_KERN = 1

KERN_CPTIME = 40
KERN_CPTIME2 = 71
KERN_BOOTTIME = 21
KERN_PROC = 66
KERN_PROC_PID = 1
KERN_PROC_KTHREAD = 7
KERN_PROC_ARGS = 55
KERN_PROC_CWD = 78
KERN_PROC_ARGV = 1
KERN_PROC_ENV = 3

KI_NGROUPS = 16
KI_MAXCOMLEN = 24
KI_WMESGLEN = 8
KI_MAXLOGNAME = 32
KI_MAXEMULLEN = 16

time_t = ctypes.c_int64  # pylint: disable=invalid-name
suseconds_t = ctypes.c_long  # pylint: disable=invalid-name

_clk_tck = os.sysconf(os.sysconf_names["SC_CLK_TCK"])


@dataclasses.dataclass
class CPUTimes:
    # The order of these fields must match the order of the numbers returned by the kern.cp_time
    # sysctl
    # https://github.com/openbsd/src/blob/master/sys/sys/sched.h#L83
    user: float
    nice: float
    system: float
    lock_spin: float
    irq: float
    idle: float


class Timeval(ctypes.Structure):
    _fields_ = [
        ("tv_sec", time_t),
        ("tv_usec", suseconds_t),
    ]

    def to_float(self) -> float:
        return cast(float, self.tv_sec + (self.tv_usec / 1000000.0))


class KinfoProc(ctypes.Structure):
    _fields_ = [
        ("p_forw", ctypes.c_uint64),
        ("p_back", ctypes.c_uint64),
        ("p_paddr", ctypes.c_uint64),
        ("p_addr", ctypes.c_uint64),
        ("p_fd", ctypes.c_uint64),
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
        ("p_siglist", ctypes.c_int32),
        ("p_sigmask", ctypes.c_uint32),
        ("p_sigignore", ctypes.c_uint32),
        ("p_sigcatch", ctypes.c_uint32),
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
        ("p_ustart_sec", ctypes.c_uint64),
        ("p_ustart_usec", ctypes.c_uint64),
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
        ("p_uctime_sec", ctypes.c_uint32),
        ("p_uctime_usec", ctypes.c_uint32),
        ("p_psflags", ctypes.c_int32),
        ("p_spare", ctypes.c_int32),
        ("p_svuid", ctypes.c_uint32),
        ("p_svgid", ctypes.c_uint32),
        ("p_emul", (ctypes.c_char * KI_MAXEMULLEN)),
        ("p_rlim_rss_cur", ctypes.c_uint64),
        ("p_cpuid", ctypes.c_uint64),
        ("p_vm_map_size", ctypes.c_uint64),
        ("p_tid", ctypes.c_int32),
        ("p_rtableid", ctypes.c_uint32),
        ("p_pledge", ctypes.c_uint64),
    ]

    def get_groups(self) -> List[int]:
        return list(self.p_groups[: self.p_ngroups])


def _get_kinfo_proc_pid(pid: int) -> KinfoProc:
    proc_info = KinfoProc()

    length = _bsd.sysctl(
        [CTL_KERN, KERN_PROC, KERN_PROC_PID, pid, ctypes.sizeof(proc_info), 1], None, proc_info
    )

    if length == 0:
        raise ProcessLookupError

    return proc_info


@_cache.CachedByProcess
def _get_kinfo_proc(proc: "Process") -> KinfoProc:
    return _get_kinfo_proc_pid(proc.pid)


def _list_kinfo_procs() -> List[KinfoProc]:
    kinfo_size = ctypes.sizeof(KinfoProc)

    while True:
        nprocs = (
            _bsd.sysctl(
                [CTL_KERN, KERN_PROC, KERN_PROC_KTHREAD, 0, kinfo_size, 1000000], None, None
            )
            // kinfo_size
        )

        proc_arr = (KinfoProc * nprocs)()

        try:
            nprocs = (
                _bsd.sysctl(
                    [CTL_KERN, KERN_PROC, KERN_PROC_KTHREAD, 0, kinfo_size, nprocs], None, proc_arr
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
    for kinfo in _list_kinfo_procs():
        yield kinfo.p_pid, cast(float, kinfo.p_ustart_sec + kinfo.p_ustart_usec / 1000000.0)


def iter_pids() -> Iterator[int]:
    for kinfo in _list_kinfo_procs():
        yield kinfo.p_pid


def pid_create_time(pid: int) -> float:
    kinfo = _get_kinfo_proc_pid(pid)
    return cast(float, kinfo.p_ustart_sec + kinfo.p_ustart_usec / 1000000.0)


_PROC_STATUSES = {
    1: ProcessStatus.IDLE,
    2: ProcessStatus.RUNNING,
    3: ProcessStatus.SLEEPING,
    4: ProcessStatus.STOPPED,
    5: ProcessStatus.ZOMBIE,
    6: ProcessStatus.DEAD,
    7: ProcessStatus.RUNNING,  # 7 is SONPROC; i.e. actually executing
}


def proc_status(proc: "Process") -> ProcessStatus:
    return _PROC_STATUSES[_get_kinfo_proc(proc).p_stat]


def proc_name(proc: "Process") -> str:
    return cast(str, _get_kinfo_proc(proc).p_comm.decode())


def proc_uids(proc: "Process") -> Tuple[int, int, int]:
    kinfo = _get_kinfo_proc(proc)
    return kinfo.p_ruid, kinfo.p_uid, kinfo.p_svuid


def proc_gids(proc: "Process") -> Tuple[int, int, int]:
    kinfo = _get_kinfo_proc(proc)
    return kinfo.p_rgid, kinfo.p_egid, kinfo.p_svgid


def proc_getgroups(proc: "Process") -> List[int]:
    return _get_kinfo_proc(proc).get_groups()


def proc_cwd(proc: "Process") -> str:
    return _bsd.sysctl_bytes_retry(
        [CTL_KERN, KERN_PROC_CWD, proc.pid], None, trim_nul=True
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
    kinfo = _get_kinfo_proc(proc)

    return ProcessSignalMasks(
        pending=_util.expand_sig_bitmask(kinfo.p_siglist, include_internal=include_internal),
        blocked=_util.expand_sig_bitmask(kinfo.p_sigmask, include_internal=include_internal),
        ignored=_util.expand_sig_bitmask(kinfo.p_sigignore, include_internal=include_internal),
        caught=_util.expand_sig_bitmask(kinfo.p_sigcatch, include_internal=include_internal),
    )


def proc_cpu_times(proc: "Process") -> ProcessCPUTimes:
    kinfo = _get_kinfo_proc(proc)

    return ProcessCPUTimes(
        user=kinfo.p_uutime_sec + kinfo.p_uutime_usec / 1000000,
        system=kinfo.p_ustime_sec + kinfo.p_ustime_usec / 1000000,
        children_user=kinfo.p_uctime_sec + kinfo.p_uctime_usec / 1000000,
        children_system=kinfo.p_uctime_sec + kinfo.p_uctime_usec / 1000000,
    )


def proc_ppid(proc: "Process") -> int:
    return cast(int, _get_kinfo_proc(proc).p_ppid)


def proc_pgid(proc: "Process") -> int:
    if proc.pid == 0 or proc._is_cache_enabled():  # pylint: disable=protected-access
        # Either a) pid=0, so we can't use getpgid() (because for that function
        # pid=0 means the current process) or b) we're in a oneshot() and
        # we should retrieve extra information.
        return cast(int, _get_kinfo_proc(proc).p__pgid)
    else:
        try:
            return _psposix.proc_pgid(proc)
        except PermissionError:
            return cast(int, _get_kinfo_proc(proc).p__pgid)


def proc_sid(proc: "Process") -> int:
    if proc.pid == 0 or proc._is_cache_enabled():  # pylint: disable=protected-access
        # Either a) pid=0, so we can't use getsid() (because for that function
        # pid=0 means the current process) or b) we're in a oneshot() and
        # we should retrieve extra information.
        return cast(int, _get_kinfo_proc(proc).p_sid)
    else:
        try:
            return _psposix.proc_sid(proc)
        except PermissionError:
            return cast(int, _get_kinfo_proc(proc).p_sid)


def proc_getpriority(proc: "Process") -> int:
    if proc.pid == 0:
        # We don't call _get_kinfo_proc() if pid != 0 and the cache is enabled because
        # Process.setpriority() can change the priority and make the cache invalid.
        return cast(int, _get_kinfo_proc(proc).p_nice)
    else:
        return _psposix.proc_getpriority(proc)


def proc_tty_rdev(proc: "Process") -> Optional[int]:
    tdev = _get_kinfo_proc(proc).p_tdev
    return tdev if tdev != 2 ** 32 - 1 else None


def cpu_times() -> CPUTimes:
    cptimes = (ctypes.c_long * 6)()

    _bsd.sysctl([CTL_KERN, KERN_CPTIME], None, cptimes)

    return CPUTimes(*(int(item) / _clk_tck for item in cptimes))


def percpu_times() -> List[CPUTimes]:
    results: List[CPUTimes] = []

    cptimes = (ctypes.c_long * 6)()

    while True:
        try:
            _bsd.sysctl([CTL_KERN, KERN_CPTIME2, len(results)], None, cptimes)
        except FileNotFoundError:
            break
        else:
            results.append(CPUTimes(*(int(item) / _clk_tck for item in cptimes)))

    return results


def boot_time() -> float:
    btime = Timeval()
    _bsd.sysctl([CTL_KERN, KERN_BOOTTIME], None, btime)
    return btime.to_float()


def time_since_boot() -> float:
    return time.clock_gettime(time.CLOCK_BOOTTIME)  # pylint: disable=no-member


def uptime() -> float:
    return time.clock_gettime(time.CLOCK_UPTIME)  # pylint: disable=no-member


DiskUsage = _psposix.DiskUsage
disk_usage = _psposix.disk_usage
