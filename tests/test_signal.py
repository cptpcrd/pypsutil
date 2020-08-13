import os
import signal
import sys

import pytest

import pypsutil

from .util import fork_proc


def test_send_signal() -> None:
    pypsutil.Process().send_signal(0)


def test_send_signal_no_proc() -> None:
    proc = fork_proc(lambda: sys.exit(0))
    os.waitpid(proc.pid, 0)

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.send_signal(0)


def test_priority_pid_0() -> None:
    try:
        proc = pypsutil.Process(0)
    except pypsutil.NoSuchProcess:
        # PID 0 doesn't show up
        return

    # If it does, we shouldn't be able to send it signals

    with pytest.raises(PermissionError):
        proc.send_signal(signal.SIGINT)
