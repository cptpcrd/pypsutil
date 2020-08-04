import os
import sys

import pytest

import pypsutil

from .util import fork_proc


def test_same_process() -> None:
    pid = os.getpid()

    assert pypsutil.Process(pid) == pypsutil.Process(pid)
    assert pypsutil.Process(pid) == pypsutil.Process()
    assert pypsutil.Process() == pypsutil.Process()


def test_proc_exists() -> None:
    # Make sure all APIs report that the current process exists
    pid = os.getpid()

    assert pypsutil.pid_exists(pid)
    assert pid in pypsutil.pids()

    proc = pypsutil.Process(pid)
    assert proc.is_running()
    assert proc.is_running()

    for proc in pypsutil.process_iter():
        if proc.pid == pid:
            break
    else:
        raise ValueError("Current process not found")

    # Make sure that all interfaces report that PID 0 either
    # exists or doesn't exist.
    if pypsutil.pid_exists(0):
        # PID 0 shows up
        assert 0 in pypsutil.pids()
        pypsutil.Process(0)

        for proc in pypsutil.process_iter():
            if proc.pid == 0:
                break
        else:
            raise ValueError("PID 0 not found")
    else:
        # PID 0 doesn't show up
        assert 0 not in pypsutil.pids()
        with pytest.raises(ProcessLookupError):
            pypsutil.Process(0)

        for proc in pypsutil.process_iter():
            assert proc.pid != 0


def test_proc_not_exists() -> None:
    assert not pypsutil.pid_exists(-1)
    for pid in pypsutil.pids():
        assert pid >= 0

    proc = fork_proc(lambda: sys.exit(0))
    os.waitpid(proc.pid, 0)

    # Process just exited
    assert not proc.is_running()
    assert not proc.is_running()
    assert not pypsutil.pid_exists(proc.pid)

    assert proc.pid not in pypsutil.pids()
    for iter_proc in pypsutil.process_iter():
        assert iter_proc.pid != proc.pid
