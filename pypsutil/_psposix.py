import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._process import Process


def proc_pgid(proc: "Process") -> int:
    pid = proc.pid

    if pid <= 0:
        raise ProcessLookupError

    return os.getpgid(pid)


def proc_sid(proc: "Process") -> int:
    pid = proc.pid

    if pid <= 0:
        raise ProcessLookupError

    return os.getsid(pid)
