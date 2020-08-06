import dataclasses
import os
import resource
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Set, Tuple, no_type_check

from . import _cache, _psposix, _util
from ._errors import ZombieProcess

if TYPE_CHECKING:
    from ._process import Process


@dataclasses.dataclass
class ProcessSignalMasks(_util.ProcessSignalMasks):
    process_pending: Set[int]


def parse_sigmask(raw_mask: str) -> Set[int]:
    return _util.expand_sig_bitmask(int(raw_mask, 16))


@_cache.CachedByProcess
def _get_proc_stat_fields(proc: "Process") -> List[str]:
    try:
        with open(os.path.join(_util.get_procfs_path(), str(proc.pid), "stat")) as file:
            line = file.readline().strip()

        lparen = line.index("(")
        rparen = line.rindex(")")

        items = line[:lparen].split()
        items.append(line[lparen + 1: rparen])
        items.extend(line[rparen + 1:].split())

        return items
    except FileNotFoundError:
        raise ProcessLookupError


@_cache.CachedByProcess
def _get_proc_status_dict(proc: "Process") -> Dict[str, str]:
    try:
        res = {}

        with open(os.path.join(_util.get_procfs_path(), str(proc.pid), "status")) as file:
            for line in file:
                name, value = line.split(":\t", maxsplit=1)
                res[name] = value.rstrip("\n")

        return res
    except FileNotFoundError:
        raise ProcessLookupError


def pid_create_time(pid: int) -> float:
    try:
        return os.stat(os.path.join(_util.get_procfs_path(), str(pid))).st_ctime
    except FileNotFoundError:
        raise ProcessLookupError


def proc_cwd(proc: "Process") -> str:
    try:
        return os.readlink(os.path.join(_util.get_procfs_path(), str(proc.pid), "cwd"))
    except FileNotFoundError:
        raise ProcessLookupError


def proc_exe(proc: "Process") -> str:
    try:
        return os.readlink(os.path.join(_util.get_procfs_path(), str(proc.pid), "exe"))
    except FileNotFoundError:
        raise ProcessLookupError


def proc_root(proc: "Process") -> str:
    try:
        return os.readlink(os.path.join(_util.get_procfs_path(), str(proc.pid), "root"))
    except FileNotFoundError:
        raise ProcessLookupError


def proc_cmdline(proc: "Process") -> List[str]:
    try:
        with open(os.path.join(_util.get_procfs_path(), str(proc.pid), "cmdline"), "rb") as file:
            cmdline = file.read()
    except FileNotFoundError:
        raise ProcessLookupError

    if not cmdline:
        raise ZombieProcess

    return _util.parse_cmdline_bytes(cmdline)


def proc_environ(proc: "Process") -> Dict[str, str]:
    try:
        with open(os.path.join(_util.get_procfs_path(), str(proc.pid), "environ"), "rb") as file:
            env_data = file.read()
    except FileNotFoundError:
        raise ProcessLookupError

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
    try:
        umask_str = _get_proc_status_dict(proc)["Umask"]
    except KeyError:
        return None
    else:
        return int(umask_str, 8)


def proc_sigmasks(proc: "Process") -> ProcessSignalMasks:
    proc_status = _get_proc_status_dict(proc)

    return ProcessSignalMasks(  # pytype: disable=wrong-keyword-args
        process_pending=parse_sigmask(proc_status["ShdPnd"]),
        pending=parse_sigmask(proc_status["SigPnd"]),
        blocked=parse_sigmask(proc_status["SigBlk"]),
        ignored=parse_sigmask(proc_status["SigIgn"]),
        caught=parse_sigmask(proc_status["SigCgt"]),
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


def iter_pids() -> Iterable[int]:
    for name in os.listdir(_util.get_procfs_path()):
        try:
            yield int(name)
        except ValueError:
            pass


def iter_pid_create_time() -> Iterable[Tuple[int, float]]:
    for name in os.listdir(_util.get_procfs_path()):
        try:
            pid = int(name)
        except ValueError:
            continue

        try:
            ctime = pid_create_time(pid)
        except ProcessLookupError:
            continue

        yield (pid, ctime)


def boot_time() -> float:
    with open(os.path.join(_util.get_procfs_path(), "stat")) as file:
        for line in file:
            if line.startswith("btime "):
                return float(line[6:].strip())

    raise ValueError


def pid_0_exists() -> bool:
    return False


proc_pgid = _psposix.proc_pgid
proc_sid = _psposix.proc_sid

proc_getpriority = _psposix.proc_getpriority
