import os
import sys

import pytest

import pypsutil

from .util import fork_proc


def test_priority() -> None:
    proc = pypsutil.Process()

    assert proc.getpriority() == proc.getpriority()

    # Should succeed
    proc.setpriority(proc.getpriority())


def test_priority_no_proc() -> None:
    proc = fork_proc(lambda: sys.exit(0))
    os.waitpid(proc.pid, 0)

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.getpriority()


def test_priority_pid_0() -> None:
    try:
        proc = pypsutil.Process(0)
    except pypsutil.NoSuchProcess:
        # PID 0 doesn't show up
        pass
    else:
        # If it does, we should be able to get its priority
        prio = proc.getpriority()

        # But not set it
        with pytest.raises(PermissionError):
            proc.setpriority(prio)
