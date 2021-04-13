# pylint: disable=invalid-name,too-few-public-methods,too-many-lines,fixme
import contextlib
import ctypes
import dataclasses
import errno
import os
import signal
import socket
import struct
import time
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Set, Tuple, Union, cast

from . import _bsd, _cache, _ffi, _psposix, _util
from ._ffi import gid_t, pid_t, uid_t
from ._util import ProcessCPUTimes, ProcessFd, ProcessFdType, ProcessStatus

if TYPE_CHECKING:  # pragma: no cover
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

libc.proc_pidfdinfo.argtypes = (
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.c_int,
)
libc.proc_pidfdinfo.restype = ctypes.c_int

libc.proc_pidpath.argtypes = (
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.c_uint32,
)
libc.proc_pidpath.restype = ctypes.c_int

WMESGLEN = 7
NGROUPS = 16
COMPAT_MAXLOGNAME = 12
MAXCOMLEN = 16

MAXPATHLEN = 1024

MAXTHREADNAMESIZE = 64

CTL_KERN = 1
KERN_ARGMAX = 8
KERN_PROCARGS2 = 49
KERN_BOOTTIME = 21
KERN_PROC = 14
KERN_PROC_ALL = 0
KERN_PROC_PID = 1

CTL_HW = 6
HW_MEMSIZE = 24

CTL_VM = 2
VM_SWAPUSAGE = 5

PROC_PIDVNODEPATHINFO = 9
PROC_PIDPATHINFO_MAXSIZE = 4 * MAXPATHLEN
PROC_PIDTASKINFO = 4
PROC_PIDTHREADID64INFO = 15
PROC_PIDLISTTHREADIDS = 28

PROC_PIDLISTFDS = 1
PROX_FDTYPE_VNODE = 1
PROX_FDTYPE_SOCKET = 2
PROX_FDTYPE_KQUEUE = 5
PROX_FDTYPE_PIPE = 6

PROC_FP_CLEXEC = 2

PROC_PIDFDVNODEPATHINFO = 2
PROC_PIDFDSOCKETINFO = 3
PROC_PIDFDPIPEINFO = 6
PROC_PIDFDKQUEUEINFO = 7

VREG = 1
VFIFO = 7

HOST_VM_INFO64 = 4

KERN_SUCCESS = 0
KERN_INVALID_ADDRESS = 1
KERN_PROTECTION_FAILURE = 2
KERN_NO_SPACE = 3
KERN_INVALID_ARGUMENT = 4
KERN_FAILURE = 5
KERN_RESOURCE_SHORTAGE = 6
KERN_NOT_RECEIVER = 7
KERN_NO_ACCESS = 8
KERN_ALREADY_IN_SET = 11
KERN_NOT_IN_SET = 12
KERN_NAME_EXISTS = 13
KERN_ABORTED = 14
KERN_INVALID_NAME = 15
KERN_INVALID_TASK = 16
KERN_INVALID_RIGHT = 17
KERN_INVALID_VALUE = 18
KERN_UREFS_OVERFLOW = 19
KERN_INVALID_CAPABILITY = 20
KERN_RIGHT_EXISTS = 21
KERN_INVALID_HOST = 22
KERN_TERMINATED = 37
KERN_DENIED = 53

SOCK_MAXADDRLEN = 255

CLOCK_UPTIME_RAW = 8

HOST_CPU_LOAD_INFO = 3
PROCESSOR_CPU_LOAD_INFO = 2

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
sa_family_t = ctypes.c_uint8

natural_t = ctypes.c_uint
kern_return_t = ctypes.c_int
host_flavor_t = ctypes.c_int
mach_vm_address_t = ctypes.c_uint64
processor_flavor_t = ctypes.c_int
mach_msg_type_number_t = natural_t
mach_port_t = natural_t
mach_port_name_t = natural_t
mach_vm_size_t = ctypes.c_uint64

MACH_PORT_NULL = mach_port_name_t()
MACH_PORT_DEAD = mach_port_name_t(_ffi.ctypes_int_max(mach_port_name_t))

libc.host_statistics64.argtypes = (
    kern_return_t,
    host_flavor_t,
    ctypes.c_void_p,
    ctypes.POINTER(mach_msg_type_number_t),
)
libc.host_statistics64.restype = kern_return_t

libc.mach_host_self.argtypes = ()
libc.mach_host_self.restype = mach_port_t

libc.host_processor_info.argtypes = (
    kern_return_t,
    processor_flavor_t,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.POINTER(mach_msg_type_number_t),
)
libc.host_processor_info.restype = kern_return_t

libc.mach_port_deallocate.argtypes = (
    mach_port_t,
    mach_port_name_t,
)
libc.mach_port_deallocate.restype = kern_return_t

libc.vm_deallocate.argtypes = (
    mach_port_name_t,
    mach_vm_address_t,
    mach_vm_size_t,
)
libc.vm_deallocate.restype = kern_return_t


@dataclasses.dataclass
class CPUTimes:
    # The order must match the CPU_STATE_* order in
    # https://github.com/apple/darwin-xnu/blob/main/osfmk/mach/machine.h#L76
    user: float
    system: float
    idle: float
    nice: float


@dataclasses.dataclass
class ProcessSignalMasks:
    ignored: Set[Union[signal.Signals, int]]  # pylint: disable=no-member
    caught: Set[Union[signal.Signals, int]]  # pylint: disable=no-member


@dataclasses.dataclass
class ProcessMemoryInfo:
    rss: int
    vms: int
    pfaults: int
    pageins: int


@dataclasses.dataclass
class VirtualMemoryInfo:  # pylint: disable=too-many-instance-attributes
    total: int
    available: int
    used: int
    free: int
    active: int
    inactive: int
    wired: int

    @property
    def percent(self) -> float:
        return 100 - self.available * 100.0 / self.total


ProcessOpenFile = _util.ProcessOpenFile
ThreadInfo = _util.ThreadInfo

SwapInfo = _util.SwapInfo


class Timeval(ctypes.Structure):
    _fields_ = [
        ("tv_sec", time_t),
        ("tv_usec", suseconds_t),
    ]

    def to_float(self) -> float:
        return cast(float, self.tv_sec + (self.tv_usec / 1000000.0))


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


class SockaddrUn(ctypes.Structure):
    _fields_ = [
        ("sun_len", ctypes.c_uint8),
        ("sun_family", sa_family_t),
        ("sun_path", (ctypes.c_char * 104)),
    ]


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
        ("p_ru", ctypes.POINTER(Rusage)),
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
        ("vst_dev", ctypes.c_int32),
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
        ("vst_rdev", ctypes.c_int32),
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


class PipeInfo(ctypes.Structure):
    _fields_ = [
        ("pipe_stat", VinfoStat),
        ("pipe_handle", ctypes.c_uint64),
        ("pipe_peerhandle", ctypes.c_uint64),
        ("pipe_status", ctypes.c_int),
        ("rfu_1", ctypes.c_int),
    ]


class KqueueInfo(ctypes.Structure):
    _fields_ = [
        ("kq_stat", VinfoStat),
        ("kq_state", ctypes.c_uint32),
        ("rfu_1", ctypes.c_uint32),
    ]


class InSockinfo(ctypes.Structure):
    _fields_ = [
        ("insi_fport", ctypes.c_int),
        ("insi_lport", ctypes.c_int),
        # TODO: Add missing fields
    ]


class UnSockinfoAddr(ctypes.Structure):
    _fields_ = [
        ("ua_sun", SockaddrUn),
        ("ua_dummy", (ctypes.c_char * SOCK_MAXADDRLEN)),
    ]


class UnSockinfo(ctypes.Structure):
    _fields_ = [
        ("unsi_conn_so", ctypes.c_uint64),
        ("unsi_conn_pcb", ctypes.c_uint64),
        ("unsi_addr", UnSockinfoAddr),
        ("unsi_caddr", UnSockinfoAddr),
    ]


class SockInfoProto(ctypes.Union):
    _fields_ = [
        # TODO: Fill out missing structures
        # (UnSockinfo is the largest field, so this should still be long enough)
        ("pri_in", InSockinfo),
        # ("pri_tcp", TcpSockinfo),
        ("pri_un", UnSockinfo),
        # ("pri_ndrv", NdrvInfo),
        # ("pri_kern_event", KernEventInfo),
        # ("pri_kern_ctl", KernCtlInfo),
        # ("pri_vsock", VsockSockinfo),
    ]


class SocketInfo(ctypes.Structure):
    _fields_ = [
        ("soi_stat", VinfoStat),
        ("soi_so", ctypes.c_uint64),
        ("soi_pcb", ctypes.c_uint64),
        ("soi_type", ctypes.c_int),
        ("soi_protocol", ctypes.c_int),
        ("soi_family", ctypes.c_int),
        ("soi_options", ctypes.c_short),
        ("soi_linger", ctypes.c_short),
        ("soi_state", ctypes.c_short),
        ("soi_qlen", ctypes.c_short),
        ("soi_incqlen", ctypes.c_short),
        ("soi_qlimit", ctypes.c_short),
        ("soi_timeo", ctypes.c_short),
        ("soi_error", ctypes.c_ushort),
        ("soi_oobmark", ctypes.c_uint32),
        ("rfu_1", ctypes.c_uint32),
        ("soi_proto", SockInfoProto),
    ]


class ProcVnodePathInfo(ctypes.Structure):
    _fields_ = [
        ("pvi_cdir", VnodeInfoPath),
        ("pvi_rdir", VnodeInfoPath),
    ]


class ProcTaskInfo(ctypes.Structure):
    _fields_ = [
        ("pti_virtual_size", ctypes.c_uint64),
        ("pti_resident_size", ctypes.c_uint64),
        ("pti_total_user", ctypes.c_uint64),
        ("pti_total_system", ctypes.c_uint64),
        ("pti_threads_user", ctypes.c_uint64),
        ("pti_threads_system", ctypes.c_uint64),
        ("pti_policy", ctypes.c_int32),
        ("pti_faults", ctypes.c_int32),
        ("pti_pageins", ctypes.c_int32),
        ("pti_cow_faults", ctypes.c_int32),
        ("pti_messages_sent", ctypes.c_int32),
        ("pti_messages_received", ctypes.c_int32),
        ("pti_syscalls_mach", ctypes.c_int32),
        ("pti_syscalls_unix", ctypes.c_int32),
        ("pti_csw", ctypes.c_int32),
        ("pti_threadnum", ctypes.c_int32),
        ("pti_numrunning", ctypes.c_int32),
        ("pti_priority", ctypes.c_int32),
    ]


class ProcThreadInfo(ctypes.Structure):
    _fields_ = [
        ("pth_user_time", ctypes.c_uint64),
        ("pth_system_time", ctypes.c_uint64),
        ("pth_policy", ctypes.c_int32),
        ("pth_policy", ctypes.c_int32),
        ("pth_run_state", ctypes.c_int32),
        ("pth_flags", ctypes.c_int32),
        ("pth_sleep_time", ctypes.c_int32),
        ("pth_curpri", ctypes.c_int32),
        ("pth_priority", ctypes.c_int32),
        ("pth_maxpriority", ctypes.c_int32),
        ("pth_name", (ctypes.c_char * MAXTHREADNAMESIZE)),
    ]


class ProcFdInfo(ctypes.Structure):
    _fields_ = [
        ("proc_fd", ctypes.c_int32),
        ("proc_fdtype", ctypes.c_uint32),
    ]


class ProcFileInfo(ctypes.Structure):
    _fields_ = [
        ("fi_openflags", ctypes.c_uint32),
        ("fi_status", ctypes.c_uint32),
        ("fi_offset", off_t),
        ("fi_type", ctypes.c_int32),
        ("fi_guardflags", ctypes.c_uint32),
    ]


class VnodeFdInfoWithPath(ctypes.Structure):
    _fields_ = [
        ("pfi", ProcFileInfo),
        ("pvip", VnodeInfoPath),
    ]


class PipeFdInfo(ctypes.Structure):
    _fields_ = [
        ("pfi", ProcFileInfo),
        ("pipeinfo", PipeInfo),
    ]


class KqueueFdInfo(ctypes.Structure):
    _fields_ = [
        ("pfi", ProcFileInfo),
        ("kqueueinfo", KqueueInfo),
    ]


class SocketFdInfo(ctypes.Structure):
    _fields_ = [
        ("pfi", ProcFileInfo),
        ("psi", SocketInfo),
    ]


class XswUsage(ctypes.Structure):
    _fields_ = [
        ("xsu_total", ctypes.c_uint64),
        ("xsu_avail", ctypes.c_uint64),
        ("xsu_used", ctypes.c_uint64),
        ("xsu_pagesize", ctypes.c_uint32),
        ("xsu_encrypted", ctypes.c_bool),
    ]


class VmStatistics64(ctypes.Structure):
    _fields_ = [
        ("free_count", natural_t),
        ("active_count", natural_t),
        ("inactive_count", natural_t),
        ("wire_count", natural_t),
        ("zero_fill_count", ctypes.c_uint64),
        ("reactivations", ctypes.c_uint64),
        ("pageins", ctypes.c_uint64),
        ("pageouts", ctypes.c_uint64),
        ("faults", ctypes.c_uint64),
        ("cow_faults", ctypes.c_uint64),
        ("lookups", ctypes.c_uint64),
        ("hits", ctypes.c_uint64),
        ("purges", ctypes.c_uint64),
        ("purgeable_count", natural_t),
        ("speculative_count", natural_t),
        ("decompressions", ctypes.c_uint64),
        ("compressions", ctypes.c_uint64),
        ("swapins", ctypes.c_uint64),
        ("swapouts", ctypes.c_uint64),
        ("compressor_page_count", natural_t),
        ("throttled_count", natural_t),
        ("external_page_count", natural_t),
        ("internal_page_count", natural_t),
        ("total_uncompressed_pages_in_compressor", ctypes.c_uint64),
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
    return list(
        (KinfoProc * nprocs).from_buffer_copy(kinfo_proc_data)  # pytype: disable=invalid-typevar
    )


def _proc_pidinfo(
    pid: int,
    flavor: int,
    arg: int,
    buf: Union[ctypes.Array, ctypes.Structure, None],  # type: ignore
    allow_zero: bool = False,
) -> int:
    res = libc.proc_pidinfo(
        pid,
        flavor,
        arg,
        ctypes.byref(buf) if buf is not None else None,
        ctypes.sizeof(buf) if buf is not None else 0,
    )
    if res < 0 or (res == 0 and not allow_zero):
        raise _ffi.build_oserror(ctypes.get_errno())

    return cast(int, res)


def _proc_pidfdinfo(
    pid: int,
    fd: int,
    flavor: int,
    buf: Union[ctypes.Array, ctypes.Structure, None],  # type: ignore
    allow_zero: bool = False,
) -> int:
    res = libc.proc_pidfdinfo(
        pid,
        fd,
        flavor,
        ctypes.byref(buf) if buf is not None else None,
        ctypes.sizeof(buf) if buf is not None else 0,
    )
    if res < 0 or (res == 0 and not allow_zero):
        raise _ffi.build_oserror(ctypes.get_errno())

    return cast(int, res)


@_cache.CachedByProcess
def _get_proc_vnode_info(proc: "Process") -> ProcVnodePathInfo:
    info = ProcVnodePathInfo()
    _proc_pidinfo(proc.pid, PROC_PIDVNODEPATHINFO, 0, info)
    return info


def _get_pid_task_info(pid: int) -> ProcTaskInfo:
    info = ProcTaskInfo()
    _proc_pidinfo(pid, PROC_PIDTASKINFO, 0, info)
    return info


@_cache.CachedByProcess
def _get_proc_task_info(proc: "Process") -> ProcTaskInfo:
    return _get_pid_task_info(proc.pid)


def _get_proc_thread_info(proc: "Process", tid: int) -> ProcThreadInfo:
    info = ProcThreadInfo()
    _proc_pidinfo(proc.pid, PROC_PIDTHREADID64INFO, tid, info)
    return info


def iter_pid_raw_create_time(
    *,
    skip_perm_error: bool = False,  # pylint: disable=unused-argument
) -> Iterator[Tuple[int, float]]:
    for kinfo in _list_kinfo_procs():
        yield kinfo.kp_proc.p_pid, kinfo.kp_proc.p_un.p_starttime.to_float()


def iter_pids() -> Iterator[int]:
    for kinfo in _list_kinfo_procs():
        yield kinfo.kp_proc.p_pid


def pid_raw_create_time(pid: int) -> float:
    return cast(float, _get_kinfo_proc_pid(pid).kp_proc.p_un.p_starttime.to_float())


def translate_create_time(raw_create_time: float) -> float:
    return raw_create_time


_PROC_STATUSES = {
    1: ProcessStatus.IDLE,
    2: ProcessStatus.RUNNING,
    3: ProcessStatus.SLEEPING,
    4: ProcessStatus.STOPPED,
    5: ProcessStatus.ZOMBIE,
}


def proc_status(proc: "Process") -> ProcessStatus:
    return _PROC_STATUSES[_get_kinfo_proc(proc).kp_proc.p_stat[0]]


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
    return os.fsdecode(_get_proc_vnode_info(proc).pvi_cdir.vip_path)


def proc_root(proc: "Process") -> str:
    root_vip = _get_proc_vnode_info(proc).pvi_rdir

    if root_vip.vip_vi.vi_type == 0:
        # This means the process isn't chroot()ed, so the kernel left pvi_rdir zeroed (0 is not a
        # valid vnode type)
        assert not root_vip.vip_path
        return "/"
    else:
        # This will return an empty string if the kernel couldn't get the path
        return cast(str, root_vip.vip_path.decode())


def proc_name(proc: "Process") -> str:
    return os.fsdecode(_get_kinfo_proc(proc).kp_proc.p_comm)


@_cache.CachedByProcess
def _proc_cmdline_environ(proc: "Process") -> Tuple[List[str], Dict[str, str]]:
    if proc.pid == 0:
        raise PermissionError

    argmax_arr = (ctypes.c_int * 1)()  # pytype: disable=not-callable
    _bsd.sysctl([CTL_KERN, KERN_ARGMAX], None, argmax_arr)

    buf = (ctypes.c_char * argmax_arr[0])()  # pytype: disable=not-callable

    try:
        nbytes = _bsd.sysctl([CTL_KERN, KERN_PROCARGS2, proc.pid], None, buf)
    except OSError as ex:
        if ex.errno == errno.EINVAL:
            raise ProcessLookupError from ex
        else:
            raise

    argc = struct.unpack("i", buf.raw[: ctypes.sizeof(ctypes.c_int)])[0]

    items = buf.raw[ctypes.sizeof(ctypes.c_int): nbytes].lstrip(b"\0").split(b"\0")

    # It appears the first item is the executable name.
    # Skip that and any empty strings following it.
    i = 1
    while not items[i]:
        i += 1

    del items[:i]

    cmdline = [arg.decode() for arg in items[:argc]]

    environ = {}
    for env_item in items[argc:]:
        try:
            key, value = env_item.split(b"=", 1)
        except ValueError:
            pass
        else:
            environ[key.decode()] = value.decode()

    return cmdline, environ


def proc_cmdline(proc: "Process") -> List[str]:
    return _proc_cmdline_environ(proc)[0]


def proc_environ(proc: "Process") -> Dict[str, str]:
    return _proc_cmdline_environ(proc)[1]


def proc_num_threads(proc: "Process") -> int:
    return cast(int, _get_proc_task_info(proc).pti_threadnum)


def _list_proc_thread_ids(proc: "Process") -> List[int]:
    # Similar strategy to _list_proc_fds() below: find the number of threads, allocate a buffer
    # (with a +1 for detecting truncation), then read into the buffer.

    # This may be cached by a oneshot(), so it *could* be inaccurate
    maxthreads = proc_num_threads(proc)

    while True:
        buf = (ctypes.c_uint64 * (maxthreads + 1))()

        nthreads = _proc_pidinfo(proc.pid, PROC_PIDLISTTHREADIDS, 0, buf) // ctypes.sizeof(
            ctypes.c_uint64
        )

        if nthreads <= maxthreads:
            return list(buf[:nthreads])

        # The cached value was incorrect; look up the real value this time around
        maxthreads = _get_pid_task_info(proc.pid).pti_threadnum


def proc_threads(proc: "Process") -> List[ThreadInfo]:
    threads = []

    for tid in _list_proc_thread_ids(proc):
        try:
            tinfo = _get_proc_thread_info(proc, tid)
        except ProcessLookupError:
            pass
        else:
            threads.append(
                ThreadInfo(
                    id=tid,
                    user_time=tinfo.pth_user_time / 1000000000,
                    system_time=tinfo.pth_system_time / 1000000000,
                )
            )

    return threads


def _list_proc_fds(proc: "Process") -> List[ProcFdInfo]:
    while True:
        maxfds = _proc_pidinfo(proc.pid, PROC_PIDLISTFDS, 0, None) // ctypes.sizeof(ProcFdInfo)

        # We add an extra 1 just in case
        buf = (ProcFdInfo * (maxfds + 1))()  # pytype: disable=not-callable

        nfds = _proc_pidinfo(proc.pid, PROC_PIDLISTFDS, 0, buf) // ctypes.sizeof(ProcFdInfo)

        # Because we added 1 when creating the buffer above, we may run into nfds == maxfds + 1.
        # That may mean truncation, and we want to try again.
        if nfds <= maxfds:
            return buf[:nfds]


def proc_num_fds(proc: "Process") -> int:
    return len(_list_proc_fds(proc))


def proc_open_files(proc: "Process") -> List[ProcessOpenFile]:
    results = []

    for fdinfo in _list_proc_fds(proc):
        if fdinfo.proc_fdtype != PROX_FDTYPE_VNODE:
            continue

        vinfo = VnodeFdInfoWithPath()
        try:
            _proc_pidfdinfo(proc.pid, fdinfo.proc_fd, PROC_PIDFDVNODEPATHINFO, vinfo)
        except OSError as ex:
            if ex.errno not in (errno.ENOENT, errno.EBADF):
                raise
        else:
            if vinfo.pvip.vip_vi.vi_type == VREG:
                results.append(
                    ProcessOpenFile(fd=fdinfo.proc_fd, path=os.fsdecode(vinfo.pvip.vip_path))
                )

    return results


def proc_iter_fds(proc: "Process") -> Iterator[ProcessFd]:
    for fdinfo in _list_proc_fds(proc):
        path = ""
        dev = None
        ino = None
        rdev = None
        size = None
        mode = None
        extra_info = {}

        flags = -1
        offset = -1

        pfi = None
        vi_stat = None

        try:
            if fdinfo.proc_fdtype == PROX_FDTYPE_VNODE:
                vinfo = VnodeFdInfoWithPath()
                _proc_pidfdinfo(proc.pid, fdinfo.proc_fd, PROC_PIDFDVNODEPATHINFO, vinfo)
                fdtype = (
                    ProcessFdType.FIFO if vinfo.pvip.vip_vi.vi_type == VFIFO else ProcessFdType.FILE
                )

                path = os.fsdecode(vinfo.pvip.vip_path)
                pfi = vinfo.pfi
                vi_stat = vinfo.pvip.vip_vi.vi_stat

            elif fdinfo.proc_fdtype == PROX_FDTYPE_SOCKET:
                fdtype = ProcessFdType.SOCKET

                sinfo = SocketFdInfo()
                _proc_pidfdinfo(proc.pid, fdinfo.proc_fd, PROC_PIDFDSOCKETINFO, sinfo)

                pfi = sinfo.pfi

                extra_info["family"] = sinfo.psi.soi_family
                extra_info["protocol"] = sinfo.psi.soi_protocol
                extra_info["type"] = sinfo.psi.soi_type

                if sinfo.psi.soi_family == socket.AF_UNIX:
                    path = os.fsdecode(
                        sinfo.psi.soi_proto.pri_un.unsi_addr.ua_sun.sun_path
                        or sinfo.psi.soi_proto.pri_un.unsi_caddr.ua_sun.sun_path
                    )

                elif sinfo.psi.soi_family in (socket.AF_INET, socket.AF_INET6):
                    extra_info["local_port"] = sinfo.psi.soi_proto.pri_in.insi_lport
                    extra_info["foreign_port"] = sinfo.psi.soi_proto.pri_in.insi_fport

            elif fdinfo.proc_fdtype == PROX_FDTYPE_PIPE:
                fdtype = ProcessFdType.PIPE

                pinfo = PipeFdInfo()
                _proc_pidfdinfo(proc.pid, fdinfo.proc_fd, PROC_PIDFDPIPEINFO, pinfo)

                pfi = pinfo.pfi

                mode = pinfo.pipeinfo.pipe_stat.vst_mode
                size = pinfo.pipeinfo.pipe_stat.vst_size
                extra_info["buffer_max"] = pinfo.pipeinfo.pipe_stat.vst_blksize
                extra_info["buffer_cnt"] = size

            elif fdinfo.proc_fdtype == PROX_FDTYPE_KQUEUE:
                fdtype = ProcessFdType.KQUEUE

                kinfo = KqueueFdInfo()
                _proc_pidfdinfo(proc.pid, fdinfo.proc_fd, PROC_PIDFDKQUEUEINFO, kinfo)

                pfi = kinfo.pfi

                size = kinfo.kqueueinfo.kq_stat.vst_size
                mode = kinfo.kqueueinfo.kq_stat.vst_mode
                extra_info["kq_count"] = size

            else:
                fdtype = ProcessFdType.UNKNOWN

        except OSError as ex:
            if ex.errno in (errno.ENOENT, errno.EBADF):
                continue
            else:
                raise

        if pfi is not None:
            offset = pfi.fi_offset

            flags = pfi.fi_openflags
            if pfi.fi_status & PROC_FP_CLEXEC:
                flags |= os.O_CLOEXEC
            else:
                flags &= ~os.O_CLOEXEC

        if vi_stat is not None:
            dev = vi_stat.vst_dev or None
            ino = vi_stat.vst_ino
            rdev = vi_stat.vst_rdev
            size = vi_stat.vst_size
            mode = vi_stat.vst_mode
            extra_info["nlink"] = vi_stat.vst_nlink

        yield ProcessFd(
            path=path,
            fd=fdinfo.proc_fd,
            fdtype=fdtype,
            flags=flags,
            position=offset,
            dev=dev,
            rdev=rdev,
            ino=ino,
            size=size,
            mode=mode,
            extra_info=extra_info,
        )


def proc_exe(proc: "Process") -> str:
    buf = (ctypes.c_char * PROC_PIDPATHINFO_MAXSIZE)()  # pytype: disable=not-callable
    if libc.proc_pidpath(proc.pid, buf, ctypes.sizeof(buf)) <= 0:
        raise _ffi.build_oserror(ctypes.get_errno())

    return os.fsdecode(buf.value)


def proc_sigmasks(proc: "Process", *, include_internal: bool = False) -> ProcessSignalMasks:
    kinfo = _get_kinfo_proc(proc)

    return ProcessSignalMasks(
        ignored=_util.expand_sig_bitmask(
            kinfo.kp_proc.p_sigignore, include_internal=include_internal
        ),
        caught=_util.expand_sig_bitmask(
            kinfo.kp_proc.p_sigcatch, include_internal=include_internal
        ),
    )


def proc_cpu_times(proc: "Process") -> ProcessCPUTimes:
    task_info = _get_proc_task_info(proc)

    return ProcessCPUTimes(
        user=task_info.pti_total_user / 1000000000,
        system=task_info.pti_total_system / 1000000000,
        children_user=0,
        children_system=0,
    )


def proc_memory_info(proc: "Process") -> ProcessMemoryInfo:
    task_info = _get_proc_task_info(proc)

    return ProcessMemoryInfo(
        rss=task_info.pti_resident_size,
        vms=task_info.pti_virtual_size,
        pageins=task_info.pti_pageins,
        pfaults=task_info.pti_faults,
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


def proc_getpriority(proc: "Process") -> int:
    if proc.pid == 0:
        # We don't call _get_kinfo_proc() if pid != 0 and the cache is enabled because
        # Process.setpriority() can change the priority and make the cache invalid.
        return cast(int, _get_kinfo_proc(proc).kp_proc.p_nice)
    else:
        return _psposix.proc_getpriority(proc)


def proc_tty_rdev(proc: "Process") -> Optional[int]:
    tdev = _get_kinfo_proc(proc).kp_eproc.e_tdev
    return tdev if tdev != -1 else None


def physical_cpu_count() -> Optional[int]:
    count = ctypes.c_int()
    _bsd.sysctlbyname("hw.physicalcpu", None, count)  # type: ignore
    return count.value or None


def cpu_freq() -> Optional[Tuple[float, float, float]]:
    try:
        cur_freq = ctypes.c_ulonglong()
        _bsd.sysctlbyname_into("hw.cpufrequency", cur_freq)

        min_freq = ctypes.c_ulonglong(0)
        try:
            _bsd.sysctlbyname_into("hw.cpufrequency_min", min_freq)
        except OSError:
            pass

        max_freq = ctypes.c_ulonglong(0)
        try:
            _bsd.sysctlbyname_into("hw.cpufrequency_max", max_freq)
        except OSError:
            pass

        return (cur_freq.value / 1000000, min_freq.value / 1000000, max_freq.value / 1000000)

    except FileNotFoundError:
        return None


_KERN_ERRNO_MAP = {
    KERN_INVALID_ADDRESS: errno.EFAULT,
    KERN_PROTECTION_FAILURE: errno.EFAULT,
    KERN_NO_SPACE: errno.ENOMEM,
    KERN_INVALID_ARGUMENT: errno.EINVAL,
    KERN_FAILURE: errno.EIO,
    KERN_RESOURCE_SHORTAGE: errno.ENOSR,
    KERN_NOT_RECEIVER: errno.EPERM,
    KERN_NO_ACCESS: errno.EACCES,
    KERN_ALREADY_IN_SET: errno.EALREADY,
    KERN_NOT_IN_SET: errno.ENOENT,
    KERN_NAME_EXISTS: errno.EEXIST,
    KERN_ABORTED: errno.EINTR,
    KERN_INVALID_NAME: errno.ENOENT,
    KERN_INVALID_TASK: errno.ESRCH,
    KERN_INVALID_RIGHT: errno.EINVAL,
    KERN_INVALID_VALUE: errno.ERANGE,
    KERN_UREFS_OVERFLOW: errno.ERANGE,
    KERN_INVALID_CAPABILITY: errno.EINVAL,
    KERN_RIGHT_EXISTS: errno.EEXIST,
    KERN_INVALID_HOST: errno.ENOENT,
    KERN_TERMINATED: errno.ENOENT,
    KERN_DENIED: errno.EPERM,
}


def _check_kernerror(ret: int) -> None:
    if ret != KERN_SUCCESS:
        raise _ffi.build_oserror(_KERN_ERRNO_MAP.get(ret, errno.EINVAL))


def _mach_task_self() -> mach_port_t:
    return mach_port_t.in_dll(libc, "mach_task_self_")


@contextlib.contextmanager
def _managed_port(port: mach_port_t) -> Iterator[mach_port_t]:
    if port == MACH_PORT_NULL:
        raise _ffi.build_oserror(errno.EINVAL)
    elif port == MACH_PORT_DEAD:
        raise _ffi.build_oserror(errno.EINVAL)

    yield port

    _check_kernerror(libc.mach_port_deallocate(_mach_task_self(), port))


def _get_vmstats64() -> VmStatistics64:
    with _managed_port(libc.mach_host_self()) as host:
        count = mach_msg_type_number_t(ctypes.sizeof(VmStatistics64) // ctypes.sizeof(ctypes.c_int))

        vmstats = VmStatistics64()

        _check_kernerror(
            libc.host_statistics64(host, HOST_VM_INFO64, ctypes.byref(vmstats), ctypes.byref(count))
        )

    return vmstats


def cpu_times() -> CPUTimes:
    with _managed_port(libc.mach_host_self()) as host:
        count = mach_msg_type_number_t(ctypes.sizeof(natural_t) * 4 // ctypes.sizeof(ctypes.c_int))

        ticks = (natural_t * 4)()

        _check_kernerror(
            libc.host_statistics64(
                host, HOST_CPU_LOAD_INFO, ctypes.byref(ticks), ctypes.byref(count)
            )
        )

    return CPUTimes(*(int(item) / _util.CLK_TCK for item in ticks))


def percpu_times() -> List[CPUTimes]:
    with _managed_port(libc.mach_host_self()) as host:
        pcount = natural_t()

        ticks = ctypes.POINTER(ctypes.c_uint)()
        tickcount = mach_msg_type_number_t(0)  # pylint: disable=no-member

        _check_kernerror(
            libc.host_processor_info(
                host,
                PROCESSOR_CPU_LOAD_INFO,
                ctypes.byref(pcount),
                ctypes.byref(ticks),
                ctypes.byref(tickcount),
            )
        )

        times = [
            CPUTimes(
                *(
                    int(item) / _util.CLK_TCK  # type: ignore[call-overload]
                    for item in ticks[i * 4: i * 4 + 4]
                )
            )
            for i in range(pcount.value)
        ]

        libc.vm_deallocate(
            _mach_task_self(),
            ctypes.addressof(ticks.contents),
            tickcount.value * ctypes.sizeof(natural_t),
        )

    return times


def virtual_memory() -> VirtualMemoryInfo:
    total_mem = _bsd.sysctl_into([CTL_HW, HW_MEMSIZE], ctypes.c_int64()).value

    vmstats = _get_vmstats64()

    return VirtualMemoryInfo(
        total=total_mem,
        used=total_mem - (vmstats.free_count * _util.PAGESIZE),
        available=(vmstats.free_count + vmstats.inactive_count) * _util.PAGESIZE,
        free=(vmstats.free_count * _util.PAGESIZE),
        active=(vmstats.active_count * _util.PAGESIZE),
        inactive=(vmstats.inactive_count * _util.PAGESIZE),
        wired=(vmstats.wire_count * _util.PAGESIZE),
    )


def swap_memory() -> SwapInfo:
    xsw_usage = _bsd.sysctl_into([CTL_VM, VM_SWAPUSAGE], XswUsage())
    vmstats = _get_vmstats64()

    return SwapInfo(
        total=(xsw_usage.xsu_total * xsw_usage.xsu_pagesize),
        used=(xsw_usage.xsu_used * xsw_usage.xsu_pagesize),
        sin=vmstats.swapins,
        sout=vmstats.swapouts,
    )


def boot_time() -> float:
    btime = Timeval()
    _bsd.sysctl([CTL_KERN, KERN_BOOTTIME], None, btime)
    return btime.to_float()


def time_since_boot() -> float:
    # Round the result to reduce small variations
    return round(time.time() - boot_time(), 4)


def uptime() -> float:
    # CLOCK_UPTIME_RAW returns the system uptime, but we want a value that's affected by
    # frequency/time adjustments so that it's comparable to time_since_boot().
    # So we take the difference of the CLOCK_UPTIME_RAW and CLOCK_MONOTONIC_RAW clocks and add that
    # to time_since_boot(). That should give us an approximate value.

    return round(
        time_since_boot()
        + (time.clock_gettime(CLOCK_UPTIME_RAW) - time.clock_gettime(time.CLOCK_MONOTONIC_RAW)),
        3,
    )


DiskUsage = _psposix.DiskUsage
disk_usage = _psposix.disk_usage
