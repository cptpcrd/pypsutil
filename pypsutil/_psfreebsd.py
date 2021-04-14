# pylint: disable=invalid-name,too-few-public-methods,too-many-lines
import ctypes
import dataclasses
import errno
import fcntl
import os
import resource
import sys
import time
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING, Dict, Iterator, List, Optional, Tuple, cast

from . import _bsd, _cache, _ffi, _psposix, _util
from ._util import ProcessCPUTimes, ProcessFd, ProcessFdType, ProcessSignalMasks, ProcessStatus

if TYPE_CHECKING:  # pragma: no cover
    from ._process import Process

CTL_KERN = 1
KERN_BOOTTIME = 21
KERN_PROC = 14
KERN_PROC_ALL = 0
KERN_PROC_PID = 1
KERN_PROC_INC_THREAD = 0x10
KERN_PROC_ARGS = 7
KERN_PROC_PATHNAME = 12
KERN_PROC_VMMAP = 32
KERN_PROC_FILEDESC = 33
KERN_PROC_GROUPS = 34
KERN_PROC_ENV = 35
KERN_PROC_RLIMIT = 37
KERN_PROC_UMASK = 39
KERN_PROC_CWD = 42

CTL_HW = 6
HW_PHYSMEM = 5

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

SIDL = 1
SRUN = 2
SSLEEP = 3
SSTOP = 4
SZOMB = 5
SWAIT = 6
SLOCK = 7

PATH_MAX = 1024

KI_CRF_GRP_OVERFLOW = 0x80000000

KF_TYPE_VNODE = 1
KF_TYPE_SOCKET = 2
KF_TYPE_PIPE = 3
KF_TYPE_FIFO = 4
KF_TYPE_KQUEUE = 5
KF_TYPE_PTS = 10
KF_TYPE_PROCDESC = 11
KF_TYPE_EVENTFD = 13
KF_VTYPE_VREG = 1
KF_FD_TYPE_ROOT = -2

KVME_TYPE_NONE = 0
KVME_TYPE_DEFAULT = 1
KVME_TYPE_VNODE = 2
KVME_TYPE_SWAP = 3
KVME_TYPE_DEVICE = 4
KVME_TYPE_PHYS = 5
KVME_TYPE_DEAD = 6
KVME_TYPE_SG = 7
KVME_TYPE_MGTDEVICE = 8
KVME_TYPE_GUARD = 9

KVME_PROT_READ = 0x00000001
KVME_PROT_WRITE = 0x00000002
KVME_PROT_EXEC = 0x00000004

XSWDEV_VERSION = 2

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

dev_t = ctypes.c_uint64

if os.uname().machine.startswith("x86") and sys.maxsize <= 2 ** 32:
    # x86, 32-bit
    time_t = ctypes.c_int32
else:
    time_t = ctypes.c_int64  # type: ignore

suseconds_t = ctypes.c_long

sa_family_t = ctypes.c_uint8

_SS_MAXSIZE = 128
_SS_ALIGNSIZE = ctypes.sizeof(ctypes.c_int64)
_SS_PAD1SIZE = _SS_ALIGNSIZE - ctypes.sizeof(ctypes.c_ubyte) - ctypes.sizeof(sa_family_t)
_SS_PAD2SIZE = (
    _SS_MAXSIZE
    - ctypes.sizeof(ctypes.c_ubyte)
    - ctypes.sizeof(sa_family_t)
    - _SS_PAD1SIZE
    - _SS_ALIGNSIZE
)

CAP_RIGHTS_VERSION = 0

rlimit_max_value = _ffi.ctypes_int_max(rlim_t)

# https://github.com/freebsd/freebsd/blob/master/sys/sys/ioccom.h#L43
IOCPARM_SHIFT = 13
IOCPARM_MASK = (1 << IOCPARM_SHIFT) - 1
IOC_OUT = 0x40000000
IOC_IN = 0x80000000
IOC_INOUT = IOC_IN | IOC_OUT


def _IOC(inout: int, group: int, num: int, length: int) -> int:
    return inout | ((length & IOCPARM_MASK) << 16) | (group << 8) | num


# https://github.com/freebsd/freebsd/blob/master/sys/dev/acpica/acpiio.h
ACPIIO_BATT_GET_UNITS = _IOC(IOC_OUT, ord("B"), 0x01, ctypes.sizeof(ctypes.c_int))

ACPI_CMBAT_MAXSTRLEN = 32

ACPI_BIF_UNITS_MA = 1

ACPI_BATT_STAT_DISCHARG = 0x0001
ACPI_BATT_STAT_CHARGING = 0x0002
ACPI_BATT_STAT_CRITICAL = 0x0004
ACPI_BATT_STAT_INVALID = ACPI_BATT_STAT_DISCHARG | ACPI_BATT_STAT_CHARGING
ACPI_BATT_STAT_BST_MASK = ACPI_BATT_STAT_INVALID | ACPI_BATT_STAT_CRITICAL
ACPI_BATT_STAT_NOT_PRESENT = ACPI_BATT_STAT_BST_MASK

ACPI_BATT_UNKNOWN = 0xFFFFFFFF

ACPIIO_ACAD_GET_STATUS = _IOC(IOC_OUT, ord("A"), 1, ctypes.sizeof(ctypes.c_int))


@dataclasses.dataclass
class CPUTimes:
    # The order of these fields must match the order of the numbers returned by the kern.cp_time
    # sysctl
    user: float
    nice: float
    system: float
    irq: float
    idle: float


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
    wired: int

    @property
    def percent(self) -> float:
        return 100 - self.available * 100.0 / self.total


@dataclasses.dataclass
class ProcessMemoryInfo:
    rss: int
    vms: int
    text: int
    data: int
    stack: int


@dataclasses.dataclass
class ProcessMemoryMap:  # pylint: disable=too-many-instance-attributes
    path: str
    addr_start: int
    addr_end: int
    perms: str
    offset: int
    dev: int
    ino: int
    size: int
    rss: int
    private: int
    ref_count: int
    shadow_count: int


@dataclasses.dataclass
class ProcessMemoryMapGrouped:  # pylint: disable=too-many-instance-attributes
    path: str
    dev: int
    ino: int
    size: int
    rss: int
    private: int
    ref_count: int
    shadow_count: int


ProcessOpenFile = _util.ProcessOpenFile
ThreadInfo = _util.ThreadInfo

PowerSupplySensorInfo = _util.PowerSupplySensorInfo
BatteryStatus = _util.BatteryStatus
BatteryInfo = _util.BatteryInfo
ACPowerInfo = _util.ACPowerInfo


class Rlimit(ctypes.Structure):
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

    def get_tdev(self) -> Optional[int]:
        if self.ki_tdev:
            tdev = cast(int, self.ki_tdev)
            NODEV = 2 ** 64 - 1
        else:
            tdev = cast(int, self.ki_tdev_freebsd11)
            NODEV = 2 ** 32 - 1

        return tdev if tdev != NODEV else None


class SockaddrStorage(ctypes.Structure):
    _fields_ = [
        ("ss_len", ctypes.c_ubyte),
        ("ss_family", sa_family_t),
        ("ss_pad1", (ctypes.c_char * _SS_PAD1SIZE)),
        ("ss_align", ctypes.c_int64),
        ("ss_pad2", (ctypes.c_char * _SS_PAD2SIZE)),
    ]


class CapRights(ctypes.Structure):
    _fields_ = [
        ("cr_rights", (ctypes.c_uint64 * (CAP_RIGHTS_VERSION + 2))),
    ]


class KinfoFile11(ctypes.Structure):
    _fields_ = [
        ("kf_vnode_type", ctypes.c_int),
        ("kf_sock_domain", ctypes.c_int),
        ("kf_sock_type", ctypes.c_int),
        ("kf_sock_protocol", ctypes.c_int),
        ("kf_sa_local", SockaddrStorage),
        ("kf_sa_peer", SockaddrStorage),
    ]


class KinfoFileSock(ctypes.Structure):
    _fields_ = [
        ("kf_sock_sendq", ctypes.c_uint32),
        ("kf_sock_domain0", ctypes.c_int),
        ("kf_sock_type0", ctypes.c_int),
        ("kf_sock_protocol0", ctypes.c_int),
        ("kf_sa_local", SockaddrStorage),
        ("kf_sa_peer", SockaddrStorage),
        ("kf_sock_pcb", ctypes.c_uint64),
        ("kf_sock_inpcb", ctypes.c_uint64),
        ("kf_sock_unpconn", ctypes.c_uint64),
        ("kf_sock_snd_sb_state", ctypes.c_uint16),
        ("kf_sock_rcv_sb_state", ctypes.c_uint16),
        ("kf_sock_recvq", ctypes.c_uint32),
    ]


class KinfoFileFile(ctypes.Structure):
    _fields_ = [
        ("kf_file_type", ctypes.c_int),
        ("kf_spareint", (ctypes.c_int * 3)),
        ("kf_spareint64", (ctypes.c_uint64 * 30)),
        ("kf_file_fsid", ctypes.c_uint64),
        ("kf_file_rdev", ctypes.c_uint64),
        ("kf_file_fileid", ctypes.c_uint64),
        ("kf_file_size", ctypes.c_uint64),
        ("kf_file_fsid_freebsd11", ctypes.c_uint32),
        ("kf_file_rdev_freebsd11", ctypes.c_uint32),
        ("kf_file_mode", ctypes.c_uint16),
        ("kf_file_pad0", ctypes.c_uint16),
        ("kf_file_pad1", ctypes.c_uint32),
    ]


class KinfoFileSem(ctypes.Structure):
    _fields_ = [
        ("kf_spareint", (ctypes.c_uint32 * 4)),
        ("kf_spareint64", (ctypes.c_uint64 * 32)),
        ("kf_sem_value", ctypes.c_uint32),
        ("kf_sem_mode", ctypes.c_uint16),
    ]


class KinfoFilePipe(ctypes.Structure):
    _fields_ = [
        ("kf_spareint", (ctypes.c_uint32 * 4)),
        ("kf_spareint64", (ctypes.c_uint64 * 32)),
        ("kf_pipe_addr", ctypes.c_uint64),
        ("kf_pipe_peer", ctypes.c_uint64),
        ("kf_pipe_buffer_cnt", ctypes.c_uint32),
        ("kf_pts_pad0", (ctypes.c_uint32 * 3)),
    ]


class KinfoFilePts(ctypes.Structure):
    _fields_ = [
        ("kf_spareint", (ctypes.c_uint32 * 4)),
        ("kf_spareint64", (ctypes.c_uint64 * 32)),
        ("kf_pts_dev_freebsd11", ctypes.c_uint32),
        ("kf_pts_pad0", ctypes.c_uint32),
        ("kf_pts_dev", ctypes.c_uint64),
        ("kf_pts_pad1", (ctypes.c_uint32 * 4)),
    ]


class KinfoFileProc(ctypes.Structure):
    _fields_ = [
        ("kf_spareint", (ctypes.c_uint32 * 4)),
        ("kf_spareint64", (ctypes.c_uint64 * 32)),
        ("kf_pid", _ffi.pid_t),
    ]


class KinfoFileUn(ctypes.Union):
    _fields_ = [
        ("kf_freebsd11", KinfoFile11),
        ("kf_sock", KinfoFileSock),
        ("kf_file", KinfoFileFile),
        ("kf_sem", KinfoFileSem),
        ("kf_pipe", KinfoFilePipe),
        ("kf_pts", KinfoFilePts),
        ("kf_proc", KinfoFileProc),
    ]


class KinfoFile(ctypes.Structure):
    _fields_ = [
        ("kf_structsize", ctypes.c_int),
        ("kf_type", ctypes.c_int),
        ("kf_fd", ctypes.c_int),
        ("kf_ref_count", ctypes.c_int),
        ("kf_flags", ctypes.c_int),
        ("kf_pad0", ctypes.c_int),
        ("kf_offset", ctypes.c_int64),
        ("kf_un", KinfoFileUn),
        ("kf_status", ctypes.c_uint16),
        ("kf_pad1", ctypes.c_uint16),
        ("_kf_ispare0", ctypes.c_int),
        ("kf_cap_rights", CapRights),
        ("_kf_cap_spare", ctypes.c_uint64),
        ("kf_path", (ctypes.c_char * PATH_MAX)),
    ]


class KinfoVmentry(ctypes.Structure):
    _fields_ = [
        ("kve_structsize", ctypes.c_int),
        ("kve_type", ctypes.c_int),
        ("kve_start", ctypes.c_uint64),
        ("kve_end", ctypes.c_uint64),
        ("kve_offset", ctypes.c_uint64),
        ("kve_vn_fileid", ctypes.c_uint64),
        ("kve_vn_fsid_freebsd11", ctypes.c_uint32),
        ("kve_flags", ctypes.c_int),
        ("kve_resident", ctypes.c_int),
        ("kve_private_resident", ctypes.c_int),
        ("kve_protection", ctypes.c_int),
        ("kve_ref_count", ctypes.c_int),
        ("kve_shadow_count", ctypes.c_int),
        ("kve_vn_type", ctypes.c_int),
        ("kve_vn_size", ctypes.c_uint64),
        ("kve_vn_rdev_freebsd11", ctypes.c_uint32),
        ("kve_vn_mode", ctypes.c_uint16),
        ("kve_status", ctypes.c_uint16),
        ("kve_vn_fsid", ctypes.c_uint64),
        ("kve_vn_rdev", ctypes.c_uint64),
        ("_kve_ispare", (ctypes.c_int * 8)),
        ("kve_path", (ctypes.c_char * PATH_MAX)),
    ]


class XswDev(ctypes.Structure):
    _fields_ = [
        ("xsw_version", ctypes.c_uint),
        ("xsw_dev", dev_t),
        ("xsw_flags", ctypes.c_int),
        ("xsw_nblks", ctypes.c_int),
        ("xsw_used", ctypes.c_int),
    ]


class VmTotal(ctypes.Structure):
    _fields_ = [
        ("t_vm", ctypes.c_uint64),
        ("t_avm", ctypes.c_uint64),
        ("t_rm", ctypes.c_uint64),
        ("t_arm", ctypes.c_uint64),
        ("t_vmshr", ctypes.c_uint64),
        ("t_avmshr", ctypes.c_uint64),
        ("t_rmshr", ctypes.c_uint64),
        ("t_armshr", ctypes.c_uint64),
        ("t_free", ctypes.c_uint64),
        ("t_rq", ctypes.c_int16),
        ("t_dw", ctypes.c_int16),
        ("t_pw", ctypes.c_int16),
        ("t_sl", ctypes.c_int16),
        ("t_sw", ctypes.c_int16),
        ("t_pad", (ctypes.c_uint16 * 3)),
    ]


class ACPIBif(ctypes.Structure):
    _fields_ = [
        ("units", ctypes.c_uint32),
        ("dcap", ctypes.c_uint32),
        ("lfcap", ctypes.c_uint32),
        ("btech", ctypes.c_uint32),
        ("dvol", ctypes.c_uint32),
        ("wcap", ctypes.c_uint32),
        ("lcap", ctypes.c_uint32),
        ("gra1", ctypes.c_uint32),
        ("gra2", ctypes.c_uint32),
        ("model", (ctypes.c_char * ACPI_CMBAT_MAXSTRLEN)),
        ("serial", (ctypes.c_char * ACPI_CMBAT_MAXSTRLEN)),
        ("type", (ctypes.c_char * ACPI_CMBAT_MAXSTRLEN)),
        ("oeminfo", (ctypes.c_char * ACPI_CMBAT_MAXSTRLEN)),
    ]


class ACPIBst(ctypes.Structure):
    _fields_ = [
        ("state", ctypes.c_uint32),
        ("rate", ctypes.c_uint32),
        ("cap", ctypes.c_uint32),
        ("volt", ctypes.c_uint32),
    ]


class ACPIBatteryIoctlArg(ctypes.Union):
    _fields_ = [
        ("unit", ctypes.c_int),
        ("bif", ACPIBif),
        ("bst", ACPIBst),
    ]


ACPIIO_BATT_GET_BIF = _IOC(IOC_INOUT, ord("B"), 0x10, ctypes.sizeof(ACPIBatteryIoctlArg))
ACPIIO_BATT_GET_BST = _IOC(IOC_INOUT, ord("B"), 0x11, ctypes.sizeof(ACPIBatteryIoctlArg))


def _get_kinfo_proc_pid(pid: int) -> KinfoProc:
    proc_info = KinfoProc()

    _bsd.sysctl([CTL_KERN, KERN_PROC, KERN_PROC_PID, pid], None, proc_info)

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


def _list_kinfo_threads(pid: int) -> List[KinfoProc]:
    kinfo_proc_data = _bsd.sysctl_bytes_retry(
        [CTL_KERN, KERN_PROC, KERN_PROC_PID | KERN_PROC_INC_THREAD, pid], None
    )
    nprocs = len(kinfo_proc_data) // ctypes.sizeof(KinfoProc)
    return list(
        (KinfoProc * nprocs).from_buffer_copy(kinfo_proc_data)  # pytype: disable=invalid-typevar
    )


def _iter_kinfo_files(proc: "Process") -> Iterator[KinfoFile]:
    kinfo_file_data = _bsd.sysctl_bytes_retry(
        [CTL_KERN, KERN_PROC, KERN_PROC_FILEDESC, proc.pid], None
    )

    return _util.iter_packed_structures(kinfo_file_data, KinfoFile, "kf_structsize")


def iter_pid_raw_create_time(
    *,
    skip_perm_error: bool = False,  # pylint: disable=unused-argument
) -> Iterator[Tuple[int, float]]:
    for kinfo in _list_kinfo_procs():
        yield kinfo.ki_pid, kinfo.ki_start.to_float()


def iter_pids() -> Iterator[int]:
    for kinfo in _list_kinfo_procs():
        yield kinfo.ki_pid


def pid_raw_create_time(pid: int) -> float:
    return cast(float, _get_kinfo_proc_pid(pid).ki_start.to_float())


def translate_create_time(raw_create_time: float) -> float:
    return raw_create_time


def proc_umask(proc: "Process") -> int:
    if proc.pid == 0:
        # Unlike the other FreeBSD functions, we can't accept pid=0, because the
        # KERN_PROC_UMASK sysctl uses that to mean the current process.
        # It won't produce the desired effect of actually operating on PID 0.
        raise PermissionError

    umask = ctypes.c_ushort()

    _bsd.sysctl(  # pytype: disable=wrong-arg-types
        [CTL_KERN, KERN_PROC, KERN_PROC_UMASK, proc.pid], None, umask  # type: ignore
    )

    return umask.value


def proc_num_fds(proc: "Process") -> int:
    return sum(kfile.kf_fd >= 0 for kfile in _iter_kinfo_files(proc))


def proc_open_files(proc: "Process") -> List[ProcessOpenFile]:
    return [
        ProcessOpenFile(
            fd=kfile.kf_fd,
            path=os.fsdecode(kfile.kf_path),
        )
        for kfile in _iter_kinfo_files(proc)
        if kfile.kf_fd >= 0
        and kfile.kf_type == KF_TYPE_VNODE
        and kfile.kf_un.kf_file.kf_file_type == KF_VTYPE_VREG
    ]


def proc_iter_fds(proc: "Process") -> Iterator[ProcessFd]:
    for kfile in _iter_kinfo_files(proc):
        if kfile.kf_fd < 0:
            continue

        dev = None
        ino = None
        rdev = None
        size = None
        mode = None
        extra_info = {}

        if kfile.kf_type == KF_TYPE_VNODE:
            fdtype = ProcessFdType.FILE
            dev = kfile.kf_un.kf_file.kf_file_fsid
            rdev = kfile.kf_un.kf_file.kf_file_rdev
            ino = kfile.kf_un.kf_file.kf_file_fileid
            size = kfile.kf_un.kf_file.kf_file_size
            mode = kfile.kf_un.kf_file.kf_file_mode

        elif kfile.kf_type == KF_TYPE_SOCKET:
            fdtype = ProcessFdType.SOCKET
            extra_info["sendq"] = kfile.kf_un.kf_sock.kf_sock_sendq
            extra_info["recvq"] = kfile.kf_un.kf_sock.kf_sock_recvq
            extra_info["domain"] = kfile.kf_un.kf_sock.kf_sock_domain0
            extra_info["type"] = kfile.kf_un.kf_sock.kf_sock_type0
            extra_info["protocol"] = kfile.kf_un.kf_sock.kf_sock_protocol0

        elif kfile.kf_type == KF_TYPE_PTS:
            fdtype = ProcessFdType.FILE
            rdev = kfile.kf_un.kf_pts.kf_pts_dev

        elif kfile.kf_type == KF_TYPE_PIPE:
            fdtype = ProcessFdType.PIPE
            extra_info["buffer_cnt"] = kfile.kf_un.kf_pipe.kf_pipe_buffer_cnt

        elif kfile.kf_type == KF_TYPE_FIFO:
            fdtype = ProcessFdType.FIFO

        elif kfile.kf_type == KF_TYPE_KQUEUE:
            fdtype = ProcessFdType.KQUEUE

        elif kfile.kf_type == KF_TYPE_EVENTFD:
            fdtype = ProcessFdType.EVENTFD
            extra_info["eventfd_value"] = kfile.kf_un.kf_eventfd.kf_eventfd_value
            extra_info["eventfd_flags"] = kfile.kf_un.kf_eventfd.kf_eventfd_flags

        elif kfile.kf_type == KF_TYPE_PROCDESC:
            fdtype = ProcessFdType.PROCDESC
            extra_info["pid"] = kfile.kf_un.kf_proc.kf_pid

        else:
            fdtype = ProcessFdType.UNKNOWN

        yield ProcessFd(
            path=(os.fsdecode(kfile.kf_path) if kfile.kf_path.startswith(b"/") else ""),
            fd=kfile.kf_fd,
            fdtype=fdtype,
            flags=kfile.kf_flags,
            position=kfile.kf_offset,
            dev=dev,
            rdev=rdev,
            ino=ino,
            size=size,
            mode=mode,
            extra_info=extra_info,
        )


_KVME_TYPE_NAMES = {
    KVME_TYPE_NONE: "none",
    KVME_TYPE_DEFAULT: "default",
    KVME_TYPE_SWAP: "swap",
    KVME_TYPE_DEVICE: "device",
    KVME_TYPE_PHYS: "phys",
    KVME_TYPE_DEAD: "dead",
    KVME_TYPE_SG: "sg",
    KVME_TYPE_MGTDEVICE: "mgtdevice",
    KVME_TYPE_GUARD: "guard",
}


def proc_memory_maps(proc: "Process") -> Iterator[ProcessMemoryMap]:
    kinfo_vmentry_data = _bsd.sysctl_bytes_retry(
        [CTL_KERN, KERN_PROC, KERN_PROC_VMMAP, proc.pid], None
    )

    for kentry in _util.iter_packed_structures(kinfo_vmentry_data, KinfoVmentry, "kve_structsize"):
        perms = (
            ("r" if kentry.kve_protection & KVME_PROT_READ else "-")
            + ("w" if kentry.kve_protection & KVME_PROT_WRITE else "-")
            + ("x" if kentry.kve_protection & KVME_PROT_EXEC else "-")
        )

        if kentry.kve_type == KVME_TYPE_VNODE:
            path = os.fsdecode(kentry.kve_path)
        else:
            path = "[{}]".format(_KVME_TYPE_NAMES.get(kentry.kve_type, "unknown"))

        yield ProcessMemoryMap(
            path=path,
            addr_start=kentry.kve_start,
            addr_end=kentry.kve_end,
            perms=perms,
            offset=kentry.kve_offset,
            ino=kentry.kve_vn_fileid,
            dev=(kentry.kve_vn_fsid or kentry.kve_vn_fsid_freebsd11),
            size=(kentry.kve_end - kentry.kve_start),
            rss=kentry.kve_resident,
            private=kentry.kve_private_resident,
            ref_count=kentry.kve_ref_count,
            shadow_count=kentry.kve_shadow_count,
        )


def group_memory_maps(maps: List[ProcessMemoryMap]) -> ProcessMemoryMapGrouped:
    kwargs = {"path": maps[0].path, "dev": maps[0].dev, "ino": maps[0].ino}

    for name in [
        "size",
        "rss",
        "private",
        "ref_count",
        "shadow_count",
    ]:
        kwargs[name] = sum(getattr(mmap, name) for mmap in maps)

    return ProcessMemoryMapGrouped(**kwargs)  # type: ignore[arg-type]


def proc_num_threads(proc: "Process") -> int:
    return cast(int, _get_kinfo_proc(proc).ki_numthreads)


def proc_threads(proc: "Process") -> List[ThreadInfo]:
    return [
        ThreadInfo(
            id=kinfo.ki_tid,
            user_time=kinfo.ki_rusage.ru_utime.to_float(),
            system_time=kinfo.ki_rusage.ru_stime.to_float(),
        )
        for kinfo in _list_kinfo_threads(proc.pid)
    ]


def proc_name(proc: "Process") -> str:
    return cast(str, _get_kinfo_proc(proc).ki_comm.decode())


_PROC_STATUSES = {
    SIDL: ProcessStatus.IDLE,
    SRUN: ProcessStatus.RUNNING,
    SSLEEP: ProcessStatus.SLEEPING,
    SSTOP: ProcessStatus.STOPPED,
    SZOMB: ProcessStatus.ZOMBIE,
    SWAIT: ProcessStatus.WAITING,
    SLOCK: ProcessStatus.LOCKED,
}


def proc_status(proc: "Process") -> ProcessStatus:
    return _PROC_STATUSES[_get_kinfo_proc(proc).ki_stat[0]]


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
        groups = (gid_t * ngroups)()  # pytype: disable=not-callable

        try:
            # Get the actual group list
            groupsize = _bsd.sysctl([CTL_KERN, KERN_PROC, KERN_PROC_GROUPS, proc.pid], None, groups)
        except OSError as ex:
            # ENOMEM means a range error; retry
            if ex.errno != errno.ENOMEM:
                raise
        else:
            # Return the group list
            ngroups = groupsize // ctypes.sizeof(gid_t)
            return groups[:ngroups]


def proc_cwd(proc: "Process") -> str:
    cwd_info = KinfoFile()
    _bsd.sysctl([CTL_KERN, KERN_PROC, KERN_PROC_CWD, proc.pid], None, cwd_info)
    return os.fsdecode(cwd_info.kf_path)


def proc_root(proc: "Process") -> str:
    for kfile in _iter_kinfo_files(proc):
        if kfile.kf_fd == KF_FD_TYPE_ROOT:
            return os.fsdecode(kfile.kf_path)

    # Something is wrong
    raise PermissionError


def proc_exe(proc: "Process") -> str:
    return os.fsdecode(
        _bsd.sysctl_bytes_retry(
            [CTL_KERN, KERN_PROC, KERN_PROC_PATHNAME, proc.pid], None, trim_nul=True
        )
    )


def proc_cmdline(proc: "Process") -> List[str]:
    cmdline_nul = _bsd.sysctl_bytes_retry([CTL_KERN, KERN_PROC, KERN_PROC_ARGS, proc.pid], None)
    return _util.parse_cmdline_bytes(cmdline_nul)


def proc_environ(proc: "Process") -> Dict[str, str]:
    env_data = _bsd.sysctl_bytes_retry([CTL_KERN, KERN_PROC, KERN_PROC_ENV, proc.pid], None)
    return _util.parse_environ_bytes(env_data)


def proc_rlimit(
    proc: "Process", res: int, new_limits: Optional[Tuple[int, int]] = None
) -> Tuple[int, int]:
    _util.check_rlimit_resource(res)

    new_limits_raw = Rlimit.construct_opt(new_limits)

    old_limits = Rlimit(rlim_cur=resource.RLIM_INFINITY, rlim_max=resource.RLIM_INFINITY)

    _bsd.sysctl([CTL_KERN, KERN_PROC, KERN_PROC_RLIMIT, proc.pid, res], new_limits_raw, old_limits)

    return old_limits.rlim_cur, old_limits.rlim_max


proc_rlimit.is_atomic = True  # type: ignore

proc_getrlimit = proc_rlimit


def proc_sigmasks(proc: "Process", *, include_internal: bool = False) -> ProcessSignalMasks:
    kinfo = _get_kinfo_proc(proc)

    return ProcessSignalMasks(
        pending=_util.expand_sig_bitmask(
            kinfo.ki_siglist.pack(), include_internal=include_internal
        ),
        blocked=_util.expand_sig_bitmask(
            kinfo.ki_sigmask.pack(), include_internal=include_internal
        ),
        ignored=_util.expand_sig_bitmask(
            kinfo.ki_sigignore.pack(), include_internal=include_internal
        ),
        caught=_util.expand_sig_bitmask(
            kinfo.ki_sigcatch.pack(), include_internal=include_internal
        ),
    )


def proc_cpu_times(proc: "Process") -> ProcessCPUTimes:
    kinfo = _get_kinfo_proc(proc)

    return ProcessCPUTimes(
        user=kinfo.ki_rusage.ru_utime.to_float(),
        system=kinfo.ki_rusage.ru_stime.to_float(),
        children_user=kinfo.ki_rusage_ch.ru_utime.to_float(),
        children_system=kinfo.ki_rusage_ch.ru_stime.to_float(),
    )


def proc_memory_info(proc: "Process") -> ProcessMemoryInfo:
    kinfo = _get_kinfo_proc(proc)

    return ProcessMemoryInfo(
        rss=kinfo.ki_rssize * _util.PAGESIZE,
        vms=kinfo.ki_size,
        text=kinfo.ki_tsize * _util.PAGESIZE,
        data=kinfo.ki_dsize * _util.PAGESIZE,
        stack=kinfo.ki_ssize * _util.PAGESIZE,
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


def proc_getpriority(proc: "Process") -> int:
    if proc.pid == 0:
        # We don't call _get_kinfo_proc() if pid != 0 and the cache is enabled because
        # Process.setpriority() can change the priority and make the cache invalid.
        return cast(int, _get_kinfo_proc(proc).ki_nice)
    else:
        return _psposix.proc_getpriority(proc)


def proc_tty_rdev(proc: "Process") -> Optional[int]:
    return _get_kinfo_proc(proc).get_tdev()


def proc_cpu_num(proc: "Process") -> int:
    kinfo = _get_kinfo_proc(proc)
    return cast(int, kinfo.ki_lastcpu if kinfo.ki_oncpu == -1 else kinfo.ki_oncpu)


def physical_cpu_count() -> Optional[int]:
    # https://manpages.ubuntu.com/manpages/precise/man4/smp.4freebsd.html

    topology_spec_dat = (
        _bsd.sysctlbyname_bytes_retry("kern.sched.topology_spec", None, trim_nul=True)
        .decode()
        .strip()
    )

    root = ET.fromstring(topology_spec_dat)

    return len(root.findall("group/children/group")) or None


def percpu_freq() -> List[Tuple[float, float, float]]:
    results = []

    try:
        i = 0
        while True:
            cur_freq = ctypes.c_int()
            _bsd.sysctlbyname_into("dev.cpu.{}.freq".format(i), cur_freq)

            try:
                levels = _bsd.sysctlbyname_bytes_retry(
                    "dev.cpu.{}.freq_levels".format(i), None, trim_nul=True
                )
            except OSError:
                min_freq = 0
                max_freq = 0
            else:
                all_freqs = [int(chunk.split(b"/", 1)[0]) for chunk in levels.split()]
                min_freq = min(all_freqs, default=0)
                max_freq = max(all_freqs, default=0)

            results.append((float(cur_freq.value), float(min_freq), float(max_freq)))
            i += 1

    except FileNotFoundError:
        pass

    return results


def cpu_times() -> CPUTimes:
    cptimes = (ctypes.c_long * 5)()  # pytype: disable=not-callable

    _bsd.sysctlbyname("kern.cp_time", None, cptimes)

    return CPUTimes(*(int(item) / _util.CLK_TCK for item in cptimes))


def percpu_times() -> List[CPUTimes]:
    cptimes_len = _bsd.sysctlbyname("kern.cp_times", None, None) // ctypes.sizeof(ctypes.c_long)

    cptimes = (ctypes.c_long * cptimes_len)()  # pytype: disable=not-callable

    _bsd.sysctlbyname("kern.cp_times", None, cptimes)

    return [
        CPUTimes(*(int(item) / _util.CLK_TCK for item in cptimes[i * 5: i * 5 + 5]))
        for i in range(len(cptimes) // 5)
    ]


def cpu_stats() -> Tuple[int, int, int, int]:
    return (
        _bsd.sysctlbyname_into("vm.stats.sys.v_switch", ctypes.c_uint64()).value,
        _bsd.sysctlbyname_into("vm.stats.sys.v_intr", ctypes.c_uint64()).value,
        _bsd.sysctlbyname_into("vm.stats.sys.v_soft", ctypes.c_uint64()).value,
        _bsd.sysctlbyname_into("vm.stats.sys.v_syscall", ctypes.c_uint64()).value,
    )


def virtual_memory() -> VirtualMemoryInfo:
    total = _bsd.sysctl_into([CTL_HW, HW_PHYSMEM], ctypes.c_ulong()).value

    free_pages = _bsd.sysctlbyname_into("vm.stats.vm.v_free_count", ctypes.c_uint()).value
    active_pages = _bsd.sysctlbyname_into("vm.stats.vm.v_active_count", ctypes.c_uint32()).value
    inactive_pages = _bsd.sysctlbyname_into("vm.stats.vm.v_inactive_count", ctypes.c_uint32()).value
    wired_pages = _bsd.sysctlbyname_into("vm.stats.vm.v_wire_count", ctypes.c_uint32()).value

    bufspace = _bsd.sysctlbyname_into("vfs.bufspace", ctypes.c_ulong()).value

    vmtotal = _bsd.sysctlbyname_into("vm.vmtotal", VmTotal())

    return VirtualMemoryInfo(
        total=total,
        available=(inactive_pages + free_pages) * _util.PAGESIZE,
        used=(active_pages + wired_pages) * _util.PAGESIZE,
        free=free_pages * _util.PAGESIZE,
        active=active_pages * _util.PAGESIZE,
        inactive=inactive_pages * _util.PAGESIZE,
        buffers=bufspace,
        cached=0,
        shared=(vmtotal.t_vmshr + vmtotal.t_rmshr) * _util.PAGESIZE,
        wired=wired_pages * _util.PAGESIZE,
    )


def swap_memory() -> _util.SwapInfo:
    dmmax = _bsd.sysctlbyname_into("vm.dmmax", ctypes.c_uint32()).value

    swap_total_pages = 0
    swap_used_pages = 0

    swapdev = XswDev()

    mib_prefix = _bsd.sysctlnametomib("vm.swap_info", maxlen=2)

    i = 0
    while True:
        try:
            _bsd.sysctl([*mib_prefix, i], None, swapdev)
        except FileNotFoundError:
            break

        if swapdev.xsw_version != XSWDEV_VERSION:
            raise _ffi.build_oserror(errno.EINVAL)

        swap_total_pages += swapdev.xsw_nblks - dmmax
        swap_used_pages += swapdev.xsw_used

        i += 1

    swapin = _bsd.sysctlbyname_into("vm.stats.vm.v_swapin", ctypes.c_uint32()).value
    swapout = _bsd.sysctlbyname_into("vm.stats.vm.v_swapout", ctypes.c_uint32()).value

    vnodein = _bsd.sysctlbyname_into("vm.stats.vm.v_vnodein", ctypes.c_uint32()).value
    vnodeout = _bsd.sysctlbyname_into("vm.stats.vm.v_vnodeout", ctypes.c_uint32()).value

    return _util.SwapInfo(
        total=swap_total_pages * _util.PAGESIZE,
        used=swap_used_pages * _util.PAGESIZE,
        sin=swapin + vnodein,
        sout=swapout + vnodeout,
    )


def _list_batteries_raw() -> List[Tuple[ACPIBif, ACPIBst]]:
    batteries = []

    try:
        with open(os.path.join(_util.get_devfs_path(), "acpi")) as acpi_file:
            # Get the number of batteries
            c_bat_count = ctypes.c_int()
            try:
                fcntl.ioctl(acpi_file, ACPIIO_BATT_GET_UNITS, c_bat_count)  # type: ignore
            except PermissionError:
                bat_count = 0
            else:
                bat_count = c_bat_count.value

            arg = ACPIBatteryIoctlArg()

            # Get individual battery statistics
            for i in range(bat_count):
                try:
                    arg.unit = i  # pylint: disable=attribute-defined-outside-init
                    fcntl.ioctl(acpi_file, ACPIIO_BATT_GET_BIF, arg)  # type: ignore
                    bif = ACPIBif.from_buffer_copy(arg.bif)

                    arg.unit = i  # pylint: disable=attribute-defined-outside-init
                    fcntl.ioctl(acpi_file, ACPIIO_BATT_GET_BST, arg)  # type: ignore
                    bst = ACPIBst.from_buffer_copy(arg.bst)
                except PermissionError:
                    pass
                else:
                    batteries.append((bif, bst))

    except FileNotFoundError:
        pass

    return batteries


def _extract_battery_status(state: int, is_full: bool) -> BatteryStatus:
    if state & ACPI_BATT_STAT_NOT_PRESENT == ACPI_BATT_STAT_NOT_PRESENT:
        return BatteryStatus.UNKNOWN
    elif state & ACPI_BATT_STAT_INVALID == ACPI_BATT_STAT_INVALID:
        return BatteryStatus.UNKNOWN
    elif state & ACPI_BATT_STAT_CHARGING == ACPI_BATT_STAT_CHARGING:
        return BatteryStatus.CHARGING
    elif state & ACPI_BATT_STAT_DISCHARG == ACPI_BATT_STAT_DISCHARG:
        return BatteryStatus.DISCHARGING
    elif is_full:
        return BatteryStatus.FULL
    else:
        return BatteryStatus.UNKNOWN


def sensors_power() -> PowerSupplySensorInfo:
    batteries = []
    ac_adapters = []

    for i, (bif, bst) in enumerate(_list_batteries_raw()):
        if bif.lfcap == 0 or bif.lfcap == ACPI_BATT_UNKNOWN or bst.cap == ACPI_BATT_UNKNOWN:
            continue

        name = "BAT{}".format(i)
        percent = bst.cap * 100 / bif.lfcap

        # Extract the current energy
        # Multiply it by 1000 to get uW/uA instead of mW/mA
        energy_full = bif.lfcap * 1000
        energy_now = bst.cap * 1000
        power_now = bst.rate * 1000 if bst.rate != ACPI_BATT_UNKNOWN else None

        if bif.units == ACPI_BIF_UNITS_MA:
            if bif.dvol in (0, ACPI_BATT_UNKNOWN):
                continue

            # Measurements are in current; convert to power
            energy_full = int(energy_full * bif.dvol / 1000)
            energy_now = int(energy_now * bif.dvol / 1000)
            if power_now is not None:
                power_now = int(power_now * bif.dvol / 1000)

        status = _extract_battery_status(bst.state, bst.cap == bif.lfcap)

        batteries.append(
            BatteryInfo(
                name=name,
                power_now=power_now,
                energy_now=energy_now,
                energy_full=energy_full,
                percent=percent,
                status=status,
            )
        )

    has_ac_power = sensors_is_on_ac_power()
    if has_ac_power is not None:
        ac_adapters.append(ACPowerInfo(name="ACAD", is_online=has_ac_power))

    return PowerSupplySensorInfo(batteries=batteries, ac_supplies=ac_adapters)


def sensors_battery_total_alt(power_plugged: Optional[bool]) -> Optional[BatteryInfo]:
    try:
        percent = float(_bsd.sysctlbyname_into("hw.acpi.battery.life", ctypes.c_int()).value)
        state = _bsd.sysctlbyname_into("hw.acpi.battery.state", ctypes.c_int()).value
    except FileNotFoundError:
        # The system just doesn't have a battery
        return None

    status = _extract_battery_status(state, percent == 100)

    secsleft = None

    if status == BatteryStatus.DISCHARGING:
        minutes_remaining = _bsd.sysctlbyname_into("hw.acpi.battery.time", ctypes.c_int()).value
        if minutes_remaining > 0:
            secsleft = minutes_remaining * 60.0

    return BatteryInfo(
        name="Combined",
        percent=percent,
        status=status,
        energy_full=None,
        energy_now=None,
        power_now=None,
        _power_plugged=power_plugged,
        _secsleft=secsleft,
    )


def sensors_is_on_ac_power() -> Optional[bool]:
    try:
        return bool(_bsd.sysctlbyname_into("hw.acpi.acline", ctypes.c_int()).value)
    except FileNotFoundError:
        return None


def boot_time() -> float:
    btime = Timeval()
    _bsd.sysctl([CTL_KERN, KERN_BOOTTIME], None, btime)
    return btime.to_float()


def time_since_boot() -> float:
    # Round the result to reduce small variations
    return round(time.time() - boot_time(), 4)


def uptime() -> float:
    return time.clock_gettime(time.CLOCK_UPTIME)  # pylint: disable=no-member


DiskUsage = _psposix.DiskUsage
disk_usage = _psposix.disk_usage
