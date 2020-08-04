# pylint: disable=invalid-name,too-few-public-methods
import ctypes
import errno
import os
import resource
import sys
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple, cast

from . import _bsd, _cache, _ffi, _psposix, _util
from ._util import ProcessSignalMasks

if TYPE_CHECKING:
    from ._process import Process

CTL_KERN = 1
KERN_BOOTTIME = 21
KERN_PROC = 14
KERN_PROC_ALL = 0
KERN_PROC_PID = 1
KERN_PROC_ARGS = 7
KERN_PROC_PATHNAME = 12
KERN_PROC_GROUPS = 34
KERN_PROC_ENV = 35
KERN_PROC_RLIMIT = 37
KERN_PROC_UMASK = 39
KERN_PROC_CWD = 52

KI_NSPARE_INT = 2
KI_NSPARE_LONG = 12
KI_NSPARE_PTR = 6

MAXCOMLEN = 19

WMESGLEN = 8
LOCKNAMELEN = 8
TDNAMLEN = 16
COMMLEN = 19
KI_EMULNAMELEN = 16
KI_NGROUPS = 16
LOGNAMELEN = 17
LOGINCLASSLEN = 17

KI_CRF_GRP_OVERFLOW = 0x80000000

gid_t = ctypes.c_uint32  # pylint: disable=invalid-name
rlim_t = ctypes.c_int64  # pylint: disable=invalid-name

if sys.maxsize > 2 ** 32 or os.uname().machine.startswith("riscv"):
    # 64-bit or RISCV
    vm_size_t = ctypes.c_uint64
    segsz_t = ctypes.c_int64
else:
    # 32-bit and not RISCV
    vm_size_t = ctypes.c_uint32  # type: ignore
    segsz_t = ctypes.c_int32  # type: ignore

fixpt_t = ctypes.c_uint32
lwpid_t = ctypes.c_int32

if os.uname().machine.startswith("x86") and sys.maxsize <= 2 ** 32:
    # x86, 32-bit
    time_t = ctypes.c_int32
else:
    time_t = ctypes.c_int64  # type: ignore

suseconds_t = ctypes.c_long


class Rlimit(ctypes.Structure):
    _fields_ = [
        ("rlim_cur", rlim_t),
        ("rlim_max", rlim_t),
    ]

    @classmethod
    def construct_opt(cls, limits: Optional[Tuple[int, int]]) -> Optional["Rlimit"]:
        return cls(rlim_cur=limits[0], rlim_max=limits[1]) if limits is not None else None

    def unpack(self) -> Tuple[int, int]:
        return self.rlim_cur, self.rlim_max


class Sigset(ctypes.Structure):
    _fields_ = [
        ("bits", (ctypes.c_uint32 * 4)),
    ]

    def pack(self) -> int:
        # https://github.com/freebsd/freebsd/blob/5f6c3c7df6e969e83bf9e64f76290d411c6e2069/sys/sys/_sigset.h
        # https://github.com/freebsd/freebsd/blob/c2d0d7c3d08302498a7a85fc059772b0533b63f9/sys/sys/signalvar.h

        return cast(int, self.bits[0])


class Timeval(ctypes.Structure):
    _fields_ = [
        ("tv_sec", time_t),
        ("tv_usec", suseconds_t),
    ]

    def to_float(self) -> float:
        return cast(float, self.tv_sec + (self.tv_usec / 1000000.0))


class Priority(ctypes.Structure):
    _fields_ = [
        ("pri_class", ctypes.c_ubyte),
        ("pri_level", ctypes.c_ubyte),
        ("pri_native", ctypes.c_ubyte),
        ("pri_user", ctypes.c_ubyte),
    ]


class Rusage(ctypes.Structure):
    _fields_ = [
        ("ru_utime", Timeval),
        ("ru_stime", Timeval),
        ("ru_maxrss", ctypes.c_long),
        ("ru_ixrss", ctypes.c_long),
        ("ru_idrss", ctypes.c_long),
        ("ru_isrss", ctypes.c_long),
        ("ru_minflt", ctypes.c_long),
        ("ru_majflt", ctypes.c_long),
        ("ru_nswap", ctypes.c_long),
        ("ru_inblock", ctypes.c_long),
        ("ru_oublock", ctypes.c_long),
        ("ru_msgsnd", ctypes.c_long),
        ("ru_msgrcv", ctypes.c_long),
        ("ru_nsignals", ctypes.c_long),
        ("ru_nvcsw", ctypes.c_long),
        ("ru_nivcsw", ctypes.c_long),
    ]


class KinfoProc(ctypes.Structure):
    _fields_ = [
        ("ki_structsize", ctypes.c_int),
        ("ki_layout", ctypes.c_int),
        ("ki_args", ctypes.c_void_p),
        ("ki_paddr", ctypes.c_void_p),
        ("ki_addr", ctypes.c_void_p),
        ("ki_tracep", ctypes.c_void_p),
        ("ki_textvp", ctypes.c_void_p),
        ("ki_fd", ctypes.c_void_p),
        ("ki_vmspace", ctypes.c_void_p),
        ("ki_wchan", ctypes.c_void_p),
        ("ki_pid", _ffi.pid_t),
        ("ki_ppid", _ffi.pid_t),
        ("ki_pgid", _ffi.pid_t),
        ("ki_tpgid", _ffi.pid_t),
        ("ki_sid", _ffi.pid_t),
        ("ki_tsid", _ffi.pid_t),
        ("ki_jobc", ctypes.c_short),
        ("ki_spare_short1", ctypes.c_short),
        ("ki_tdev_freebsd11", ctypes.c_uint32),
        ("ki_siglist", Sigset),
        ("ki_sigmask", Sigset),
        ("ki_sigignore", Sigset),
        ("ki_sigcatch", Sigset),
        ("ki_uid", _ffi.uid_t),
        ("ki_ruid", _ffi.uid_t),
        ("ki_svuid", _ffi.uid_t),
        ("ki_rgid", _ffi.uid_t),
        ("ki_svgid", _ffi.gid_t),
        ("ki_ngroups", ctypes.c_short),
        ("ki_spare_short2", ctypes.c_short),
        ("ki_groups", (_ffi.gid_t * KI_NGROUPS)),
        ("ki_size", vm_size_t),
        ("ki_rssize", segsz_t),
        ("ki_swrss", segsz_t),
        ("ki_tsize", segsz_t),
        ("ki_dsize", segsz_t),
        ("ki_ssize", segsz_t),
        ("ki_xstat", ctypes.c_ushort),
        ("ki_acflag", ctypes.c_ushort),
        ("ki_pctcpu", fixpt_t),
        ("ki_estcpu", ctypes.c_uint),
        ("ki_slptime", ctypes.c_uint),
        ("ki_swtime", ctypes.c_uint),
        ("ki_cow", ctypes.c_int),
        ("ki_runtime", ctypes.c_uint64),
        ("ki_start", Timeval),
        ("ki_childtime", Timeval),
        ("ki_flag", ctypes.c_long),
        ("ki_kiflag", ctypes.c_long),
        ("ki_traceflag", ctypes.c_int),
        ("ki_stat", ctypes.c_char),
        ("ki_nice", ctypes.c_char),
        ("ki_lock", ctypes.c_char),
        ("ki_rqindex", ctypes.c_char),
        ("ki_oncpu_old", ctypes.c_ubyte),
        ("ki_lastcpu_old", ctypes.c_ubyte),
        ("ki_tdname", (ctypes.c_char * (TDNAMLEN + 1))),
        ("ki_wmesg", (ctypes.c_char * (WMESGLEN + 1))),
        ("ki_login", (ctypes.c_char * (LOGNAMELEN + 1))),
        ("ki_lockname", (ctypes.c_char * (LOCKNAMELEN + 1))),
        ("ki_comm", (ctypes.c_char * (COMMLEN + 1))),
        ("ki_emul", (ctypes.c_char * (KI_EMULNAMELEN + 1))),
        ("ki_loginclass", (ctypes.c_char * (LOGINCLASSLEN + 1))),
        ("ki_moretdname", (ctypes.c_char * (MAXCOMLEN - TDNAMLEN + 1))),
        ("ki_sparestrings", (ctypes.c_char * 46)),
        ("ki_spareints", (ctypes.c_int * KI_NSPARE_INT)),
        ("ki_tdev", ctypes.c_uint64),
        ("ki_oncpu", ctypes.c_int),
        ("ki_lastcpu", ctypes.c_int),
        ("ki_tracer", ctypes.c_int),
        ("ki_flag2", ctypes.c_int),
        ("ki_fibnum", ctypes.c_int),
        ("ki_cr_flags", ctypes.c_uint),
        ("ki_jid", ctypes.c_int),
        ("ki_numthreads", ctypes.c_int),
        ("ki_tid", lwpid_t),
        ("ki_pri", Priority),
        ("ki_rusage", Rusage),
        ("ki_rusage_ch", Rusage),
        ("ki_pcb", ctypes.c_void_p),
        ("ki_kstack", ctypes.c_void_p),
        ("ki_udata", ctypes.c_void_p),
        ("ki_tdaddr", ctypes.c_void_p),
        ("ki_spareptrs", (ctypes.c_void_p * KI_NSPARE_PTR)),
        ("ki_sparelongs", (ctypes.c_void_p * KI_NSPARE_LONG)),
        ("ki_sflag", ctypes.c_long),
        ("ki_tdflags", ctypes.c_long),
    ]

    def get_groups(self) -> List[int]:
        return list(self.ki_groups[: self.ki_ngroups])


def _get_kinfo_proc_pid(pid: int) -> KinfoProc:
    proc_info = KinfoProc()

    length = _bsd.sysctl([CTL_KERN, KERN_PROC, KERN_PROC_PID, pid], None, proc_info)

    if length == 0:
        raise ProcessLookupError

    return proc_info


@_cache.CachedByProcess
def _get_kinfo_proc(proc: "Process") -> KinfoProc:
    return _get_kinfo_proc_pid(proc.pid)


def _list_kinfo_procs() -> List[KinfoProc]:
    kinfo_proc_data = _bsd.sysctl_bytes_retry([CTL_KERN, KERN_PROC, KERN_PROC_ALL], None)
    nprocs = len(kinfo_proc_data) // ctypes.sizeof(KinfoProc)
    return list((KinfoProc * nprocs).from_buffer_copy(kinfo_proc_data))


def iter_pid_create_time() -> Iterator[Tuple[int, float]]:
    for kinfo in _list_kinfo_procs():
        yield kinfo.ki_pid, kinfo.ki_start.to_float()


def iter_pids() -> Iterator[int]:
    for kinfo in _list_kinfo_procs():
        yield kinfo.ki_pid


def pid_create_time(pid: int) -> float:
    return cast(float, _get_kinfo_proc_pid(pid).ki_start.to_float())


def proc_umask(proc: "Process") -> int:
    if proc.pid == 0:
        # Unlike the other FreeBSD functions, we can't accept pid=0, because the
        # KERN_PROC_UMASK sysctl uses that to mean the current process.
        # It won't produce the desired effect of actually operating on PID 0.
        raise ProcessLookupError

    umask = ctypes.c_ushort()

    _bsd.sysctl(  # pytype: disable=wrong-arg-types
        [CTL_KERN, KERN_PROC, KERN_PROC_UMASK, proc.pid], None, umask  # type: ignore
    )

    return umask.value


def proc_uids(proc: "Process") -> Tuple[int, int, int]:
    kinfo = _get_kinfo_proc(proc)
    return kinfo.ki_ruid, kinfo.ki_uid, kinfo.ki_svuid


def proc_gids(proc: "Process") -> Tuple[int, int, int]:
    kinfo = _get_kinfo_proc(proc)
    return kinfo.ki_rgid, kinfo.ki_groups[0], kinfo.ki_svgid


def proc_getgroups(proc: "Process") -> List[int]:
    if proc._is_cache_enabled():  # pylint: disable=protected-access
        # We're in a oneshot(); try to retrieve extra information
        kinfo = _get_kinfo_proc(proc)

        if not kinfo.ki_cr_flags & KI_CRF_GRP_OVERFLOW:
            return kinfo.get_groups()

        # KI_CRF_GRP_OVERFLOW was in ki_cr_flags. The group list was truncated,
        # and we'll have to fall back on the KERN_PROC_GROUPS sysctl.

    while True:
        # Get the number of groups
        groupsize = _bsd.sysctl([CTL_KERN, KERN_PROC, KERN_PROC_GROUPS, proc.pid], None, None)
        ngroups = groupsize // ctypes.sizeof(gid_t)

        # Create an array with that many elements
        groups = (gid_t * ngroups)()

        try:
            # Get the actual group list
            groupsize = _bsd.sysctl([CTL_KERN, KERN_PROC, KERN_PROC_GROUPS, proc.pid], None, groups)
        except OSError as ex:
            # EINVAL means a range error; retry
            if ex.errno != errno.EINVAL:
                raise
        else:
            # Return the group list
            ngroups = groupsize // ctypes.sizeof(gid_t)
            return groups[:ngroups]


def proc_cwd(proc: "Process") -> str:
    return _bsd.sysctl_bytes_retry(
        [CTL_KERN, KERN_PROC, KERN_PROC_CWD, proc.pid], None, trim_nul=True
    ).decode()


def proc_exe(proc: "Process") -> str:
    return _bsd.sysctl_bytes_retry(
        [CTL_KERN, KERN_PROC, KERN_PROC_PATHNAME, proc.pid], None, trim_nul=True
    ).decode()


def proc_cmdline(proc: "Process") -> List[str]:
    cmdline_nul = _bsd.sysctl_bytes_retry([CTL_KERN, KERN_PROC_ARGS, proc.pid], None)
    return _util.parse_cmdline_bytes(cmdline_nul)


def proc_environ(proc: "Process") -> Dict[str, str]:
    env_data = _bsd.sysctl_bytes_retry([CTL_KERN, KERN_PROC_ENV, proc.pid], None)
    return _util.parse_environ_bytes(env_data)


def proc_rlimit(
    proc: "Process", res: int, new_limits: Optional[Tuple[int, int]] = None
) -> Tuple[int, int]:
    _util.check_rlimit_resource(res)

    new_limits_raw = Rlimit.construct_opt(new_limits)

    old_limits = Rlimit(rlim_cur=resource.RLIM_INFINITY, rlim_max=resource.RLIM_INFINITY)

    _bsd.sysctl([CTL_KERN, KERN_PROC, KERN_PROC_RLIMIT, proc.pid, res], new_limits_raw, old_limits)

    return old_limits.unpack()


proc_getrlimit = proc_rlimit


def proc_get_sigmasks(proc: "Process") -> ProcessSignalMasks:
    kinfo = _get_kinfo_proc(proc)

    return ProcessSignalMasks(
        pending=_util.expand_sig_bitmask(kinfo.ki_siglist.pack()),
        blocked=_util.expand_sig_bitmask(kinfo.ki_sigmask.pack()),
        ignored=_util.expand_sig_bitmask(kinfo.ki_sigignore.pack()),
        caught=_util.expand_sig_bitmask(kinfo.ki_sigcatch.pack()),
    )


def proc_ppid(proc: "Process") -> int:
    return cast(int, _get_kinfo_proc(proc).ki_ppid)


def proc_pgid(proc: "Process") -> int:
    if proc.pid == 0 or proc._is_cache_enabled():  # pylint: disable=protected-access
        # Either a) pid=0, so we can't use getpgid() (because for that function
        # pid=0 means the current process) or b) we're in a oneshot() and
        # we should retrieve extra information.
        return cast(int, _get_kinfo_proc(proc).ki_pgid)
    else:
        return _psposix.proc_pgid(proc)


def proc_sid(proc: "Process") -> int:
    if proc.pid == 0 or proc._is_cache_enabled():  # pylint: disable=protected-access
        # Either a) pid=0, so we can't use getsid() (because for that function
        # pid=0 means the current process) or b) we're in a oneshot() and
        # we should retrieve extra information.
        return cast(int, _get_kinfo_proc(proc).ki_sid)
    else:
        return _psposix.proc_sid(proc)


def pid_0_exists() -> bool:
    try:
        _get_kinfo_proc_pid(0)
    except (ProcessLookupError, PermissionError):
        return False
    else:
        return True


def boot_time() -> float:
    btime = Timeval()
    _bsd.sysctl([CTL_KERN, KERN_BOOTTIME], None, btime)
    return btime.to_float()
