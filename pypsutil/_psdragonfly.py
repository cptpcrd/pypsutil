# Type checkers don't like the resource names not existing.
# mypy: ignore-errors
# pytype: disable=module-attr
# pylint: disable=no-member
import os
import resource
from typing import Dict, List, Tuple

from . import _cache, _psposix, _util

RESOURCE_VALUES = {
    "cpu": resource.RLIMIT_CPU,
    "fsize": resource.RLIMIT_FSIZE,
    "data": resource.RLIMIT_DATA,
    "stack": resource.RLIMIT_STACK,
    "core": resource.RLIMIT_CORE,
    "rss": resource.RLIMIT_RSS,
    "memlock": resource.RLIMIT_MEMLOCK,
    "nproc": resource.RLIMIT_NPROC,
    "nofile": resource.RLIMIT_NOFILE,
    "sbsize": resource.RLIMIT_SBSIZE,
    "vmem": resource.RLIMIT_AS,
    "posixlock": resource.RLIMIT_POSIXLOCKS,
}


@_cache.CachedByPid
def _get_proc_status_fields(pid: int) -> List[str]:
    try:
        with open(os.path.join(_util.get_procfs_path(), str(pid), "status")) as file:
            return file.read().rstrip("\n").split(" ")
    except FileNotFoundError:
        raise ProcessLookupError


@_cache.CachedByPid
def _get_proc_rlimits(pid: int) -> Dict[int, Tuple[int, int]]:
    try:
        limits = {}

        with open(os.path.join(_util.get_procfs_path(), str(pid), "rlimit")) as file:
            for line in file:
                name, lim_cur_str, lim_max_str = line.split()

                try:
                    res = RESOURCE_VALUES[name]
                except KeyError:
                    continue

                lim_cur = int(lim_cur_str)
                if lim_cur == -1:
                    lim_cur = resource.RLIM_INFINITY

                lim_max = int(lim_max_str)
                if lim_max == -1:
                    lim_max = resource.RLIM_INFINITY

                limits[res] = (lim_cur, lim_max)

        return limits
    except FileNotFoundError:
        raise ProcessLookupError


def proc_getgroups(pid: int) -> List[int]:
    return list(map(int, _get_proc_status_fields(pid)[13].split(",")[1:]))


def proc_getrlimit(pid: int, res: int) -> Tuple[int, int]:
    limits = _get_proc_rlimits(pid)

    try:
        return limits[res]
    except KeyError:
        raise ValueError("invalid resource specified")


def proc_getpgid(pid: int) -> int:
    if _cache.is_enabled(pid):
        # We're in a oneshot(); retrieve extra information
        return int(_get_proc_status_fields(pid)[3])
    else:
        return _psposix.proc_getpgid(pid)


def proc_getsid(pid: int) -> int:
    if _cache.is_enabled(pid):
        # We're in a oneshot(); retrieve extra information
        return int(_get_proc_status_fields(pid)[4])
    else:
        return _psposix.proc_getsid(pid)
