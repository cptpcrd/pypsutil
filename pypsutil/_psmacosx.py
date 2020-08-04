# pylint: disable=invalid-name,too-few-public-methods
import ctypes
import dataclasses
import struct
from typing import TYPE_CHECKING, Dict, Iterator, List, Set, Tuple, Union, cast

from . import _bsd, _cache, _ffi, _psposix, _util
from ._ffi import gid_t, pid_t, uid_t

if TYPE_CHECKING:
    from ._process import Process

libc = _ffi.load_libc()
libc.proc_pidinfo.argtypes = (
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint64,
    ctypes.c_void_p,
    ctypes.c_int,
)
libc.proc_pidinfo.restype = ctypes.c_int

WMESGLEN = 7
NGROUPS = 16
COMPAT_MAXLOGNAME = 12
MAXCOMLEN = 16

MAXPATHLEN = 1024

CTL_KERN = 1
KERN_PROCARGS2 = 49
KERN_BOOTTIME = 21
KERN_PROC = 14
KERN_PROC_ALL = 0
KERN_PROC_PID = 1

PROC_PIDVNODEPATHINFO = 9
PROC_PIDPATHINFO = 11
PROC_PIDPATHINFO_MAXSIZE = 4 * MAXPATHLEN

caddr_t = ctypes.c_char_p
segsz_t = ctypes.c_int32
dev_t = ctypes.c_int32
fixpt_t = ctypes.c_uint32
u_quad_t = ctypes.c_uint64
time_t = ctypes.c_long
suseconds_t = ctypes.c_int32
sigset_t = ctypes.c_uint32
fsid_t = ctypes.c_int32 * 2
off_t = ctypes.c_int64


@dataclasses.dataclass
class ProcessSignalMasks:
    ignored: Set[int]
    caught: Set[int]


class Timeval(ctypes.Structure):
    _fields_ = [
        ("tv_sec", time_t),
        ("tv_usec", suseconds_t),
    ]

    def to_float(self) -> float:
        return cast(float, self.tv_sec + (self.tv_usec / 1000000.0))


class ITimerval(ctypes.Structure):
    _fields_ = [
        ("it_interval", Timeval),
        ("it_value", Timeval),
    ]


class ExternProcPunSt1(ctypes.Structure):
    _fields_ = [
        ("p_forw", ctypes.c_void_p),
        ("p_back", ctypes.c_void_p),
    ]


class ExternProcPun(ctypes.Union):
    _fields_ = [
        ("p_st1", ExternProcPunSt1),
        ("p_starttime", Timeval),
    ]


class ExternProc(ctypes.Structure):
    _fields_ = [
        ("p_un", ExternProcPun),
        ("p_vmspace", ctypes.c_void_p),
        ("p_sigacts", ctypes.c_void_p),
        ("p_flag", ctypes.c_int),
        ("p_stat", ctypes.c_char),
        ("p_pid", pid_t),
        ("p_oppid", pid_t),
        ("p_dupfd", ctypes.c_int),
        ("user_stack", caddr_t),
        ("exit_thread", ctypes.c_void_p),
        ("p_debugger", ctypes.c_int),
        ("sigwait", ctypes.c_bool),
        ("p_estcpu", ctypes.c_uint),
        ("p_cpticks", ctypes.c_int),
        ("p_pctcpu", fixpt_t),
        ("p_wchan", ctypes.c_void_p),
        ("p_wmesg", ctypes.c_char_p),
        ("p_swtime", ctypes.c_uint),
        ("p_slptime", ctypes.c_uint),
        ("p_realtimer", ITimerval),
        ("p_rtime", Timeval),
        ("p_uticks", u_quad_t),
        ("p_sticks", u_quad_t),
        ("p_iticks", u_quad_t),
        ("p_traceflag", ctypes.c_int),
        ("p_tracep", ctypes.c_void_p),
        ("p_siglist", ctypes.c_int),
        ("p_textvp", ctypes.c_void_p),
        ("p_holdcnt", ctypes.c_int),
        ("p_sigmask", sigset_t),
        ("p_sigignore", sigset_t),
        ("p_sigcatch", sigset_t),
        ("p_priority", ctypes.c_ubyte),
        ("p_usrpri", ctypes.c_ubyte),
        ("p_nice", ctypes.c_char),
        ("p_comm", (ctypes.c_char * (MAXCOMLEN + 1))),
        ("p_pgrp", ctypes.c_void_p),
        ("p_addr", ctypes.c_void_p),
        ("p_xstat", ctypes.c_ushort),
        ("p_acflag", ctypes.c_ushort),
        ("p_ru", ctypes.c_void_p),
    ]


class Pcred(ctypes.Structure):
    _fields_ = [
        ("pc_lock", (ctypes.c_char * 72)),
        ("pc_ucred", ctypes.c_void_p),
        ("p_ruid", uid_t),
        ("p_svuid", uid_t),
        ("p_rgid", gid_t),
        ("p_svgid", gid_t),
        ("p_refcnt", ctypes.c_int),
    ]


class Ucred(ctypes.Structure):
    _fields_ = [
        ("cr_ref", ctypes.c_int32),
        ("cr_uid", uid_t),
        ("cr_ngroups", ctypes.c_short),
        ("cr_groups", (gid_t * NGROUPS)),
    ]


class Vmspace(ctypes.Structure):
    _fields_ = [
        ("vm_refcnt", ctypes.c_int),
        ("vm_shm", caddr_t),
        ("vm_rssize", segsz_t),
        ("vm_swrss", segsz_t),
        ("vm_tsize", segsz_t),
        ("vm_dsize", segsz_t),
        ("vm_ssize", segsz_t),
        ("vm_taddr", caddr_t),
        ("vm_daddr", caddr_t),
        ("vm_maxsaddr", caddr_t),
    ]


class Eproc(ctypes.Structure):
    _fields_ = [
        ("e_paddr", ctypes.c_void_p),
        ("e_sess", ctypes.c_void_p),
        ("e_pcred", Pcred),
        ("e_ucred", Ucred),
        ("e_vm", Vmspace),
        ("e_ppid", pid_t),
        ("e_pgid", pid_t),
        ("e_jobc", ctypes.c_short),
        ("e_tdev", dev_t),
        ("e_tpgid", pid_t),
        ("e_tsess", ctypes.c_void_p),
        ("e_wmesg", (ctypes.c_char * (WMESGLEN + 1))),
        ("e_xsize", segsz_t),
        ("e_xrssize", ctypes.c_short),
        ("e_xccount", ctypes.c_short),
        ("e_xswrss", ctypes.c_short),
        ("e_flag", ctypes.c_int32),
        ("e_login", (ctypes.c_char * COMPAT_MAXLOGNAME)),
        ("e_spare", (ctypes.c_int32 * 4)),
    ]


class KinfoProc(ctypes.Structure):
    _fields_ = [
        ("kp_proc", ExternProc),
        ("kp_eproc", Eproc),
    ]

    def get_groups(self) -> List[int]:
        return list(self.kp_eproc.e_ucred.cr_groups[: self.kp_eproc.e_ucred.cr_ngroups])


class VinfoStat(ctypes.Structure):
    _fields_ = [
        ("vst_dev", ctypes.c_uint32),
        ("vst_mode", ctypes.c_uint16),
        ("vst_nlink", ctypes.c_uint16),
        ("vst_ino", ctypes.c_uint64),
        ("vst_uid", uid_t),
        ("vst_gid", gid_t),
        ("vst_atime", ctypes.c_int64),
        ("vst_atimensec", ctypes.c_int64),
        ("vst_mtime", ctypes.c_int64),
        ("vst_mtimensec", ctypes.c_int64),
        ("vst_ctime", ctypes.c_int64),
        ("vst_ctimensec", ctypes.c_int64),
        ("vst_birthtime", ctypes.c_int64),
        ("vst_birthtimensec", ctypes.c_int64),
        ("vst_size", off_t),
        ("vst_blocks", ctypes.c_int64),
        ("vst_blksize", ctypes.c_int32),
        ("vst_flags", ctypes.c_uint32),
        ("vst_gen", ctypes.c_uint32),
        ("vst_rdev", ctypes.c_uint32),
        ("vst_qspare", (ctypes.c_int64 * 2)),
    ]


class VnodeInfo(ctypes.Structure):
    _fields_ = [
        ("vi_stat", VinfoStat),
        ("vi_type", ctypes.c_int),
        ("vi_pad", ctypes.c_int),
        ("vi_fsid", fsid_t),
    ]


class VnodeInfoPath(ctypes.Structure):
    _fields_ = [
        ("vip_vi", VnodeInfo),
        ("vip_path", (ctypes.c_char * MAXPATHLEN)),
    ]


class ProcVnodePathInfo(ctypes.Structure):
    _fields_ = [
        ("pvi_cdir", VnodeInfoPath),
        ("pvi_rdir", VnodeInfoPath),
    ]


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


def _proc_pidinfo(
    pid: int, flavor: int, arg: int, buf: Union[ctypes.Array, ctypes.Structure]  # type: ignore
) -> int:
    res = libc.proc_pidinfo(pid, flavor, arg, buf, ctypes.sizeof(buf))
    if res < 0:
        raise _ffi.build_oserror(ctypes.get_errno())

    return cast(int, res)


@_cache.CachedByProcess
def _get_proc_vnode_info(proc: "Process") -> ProcVnodePathInfo:
    info = ProcVnodePathInfo()
    _proc_pidinfo(proc.pid, PROC_PIDVNODEPATHINFO, 0, info)
    return info


def iter_pid_create_time() -> Iterator[Tuple[int, float]]:
    for kinfo in _list_kinfo_procs():
        yield kinfo.kp_proc.p_pid, kinfo.kp_proc.p_un.p_starttime.to_float()


def iter_pids() -> Iterator[int]:
    for kinfo in _list_kinfo_procs():
        yield kinfo.kp_proc.p_pid


def pid_create_time(pid: int) -> float:
    return cast(float, _get_kinfo_proc_pid(pid).kp_proc.p_un.p_starttime.to_float())


def proc_uids(proc: "Process") -> Tuple[int, int, int]:
    kinfo = _get_kinfo_proc(proc)
    return (
        kinfo.kp_eproc.e_pcred.p_ruid,
        kinfo.kp_eproc.e_ucred.cr_uid,
        kinfo.kp_eproc.e_pcred.p_svuid,
    )


def proc_gids(proc: "Process") -> Tuple[int, int, int]:
    kinfo = _get_kinfo_proc(proc)
    return (
        kinfo.kp_eproc.e_pcred.p_rgid,
        kinfo.kp_eproc.e_ucred.cr_groups[0],
        kinfo.kp_eproc.e_pcred.p_svgid,
    )


def proc_getgroups(proc: "Process") -> List[int]:
    return _get_kinfo_proc(proc).get_groups()


def proc_cwd(proc: "Process") -> str:
    return cast(str, _get_proc_vnode_info(proc).pvi_cdir.vip_path.value.decode())


def proc_root(proc: "Process") -> str:
    return cast(str, _get_proc_vnode_info(proc).pvi_rdir.vip_path.value.decode())


@_cache.CachedByProcess
def _proc_cmdline_environ(proc: "Process") -> Tuple[List[str], Dict[str, str]]:
    if proc.pid == 0:
        raise ProcessLookupError

    data = _bsd.sysctl_bytes_retry([CTL_KERN, KERN_PROCARGS2, proc.pid], None)
    argc = struct.unpack("i", data[: ctypes.sizeof(ctypes.c_int)])[0]
    data = data[ctypes.sizeof(ctypes.c_int):]
    if data.endswith(b"\0"):
        data = data[:-1]

    items = data.split(b"\0")

    environ = {}
    for env_item in items[argc:]:
        try:
            key, value = env_item.split(b"=", 1)
        except ValueError:
            pass
        else:
            environ[key.decode()] = value.decode()

    return [arg.decode() for arg in items[:argc]], environ


def proc_cmdline(proc: "Process") -> List[str]:
    return _proc_cmdline_environ(proc)[0]


def proc_environ(proc: "Process") -> Dict[str, str]:
    return _proc_cmdline_environ(proc)[1]


def proc_exe(proc: "Process") -> str:
    buf = (ctypes.c_char * PROC_PIDPATHINFO_MAXSIZE)()
    _proc_pidinfo(proc.pid, PROC_PIDPATHINFO, 0, buf)
    return buf.value.decode()


def proc_get_sigmasks(proc: "Process") -> ProcessSignalMasks:
    kinfo = _get_kinfo_proc(proc)

    return ProcessSignalMasks(
        ignored=_util.expand_sig_bitmask(kinfo.kp_proc.p_sigignore),
        caught=_util.expand_sig_bitmask(kinfo.kp_proc.p_sigcatch),
    )


def proc_ppid(proc: "Process") -> int:
    return cast(int, _get_kinfo_proc(proc).kp_eproc.e_ppid)


def proc_pgid(proc: "Process") -> int:
    if proc.pid == 0 or proc._is_cache_enabled():  # pylint: disable=protected-access
        # Either a) pid=0, so we can't use getpgid() (because for that function
        # pid=0 means the current process) or b) we're in a oneshot() and
        # we should retrieve extra information.
        return cast(int, _get_kinfo_proc(proc).kp_eproc.e_pgid)
    else:
        return _psposix.proc_pgid(proc)


proc_sid = _psposix.proc_sid


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
