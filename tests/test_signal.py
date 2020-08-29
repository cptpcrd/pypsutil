import signal

import pytest

import pypsutil

from .util import get_dead_process


def test_send_signal() -> None:
    pypsutil.Process().send_signal(0)


def test_send_signal_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.send_signal(0)


def test_priority_pid_0() -> None:
    try:
        proc = pypsutil.Process(0)
    except pypsutil.NoSuchProcess:
        pytest.skip("PID 0 does not appear")

    # If it does, we shouldn't be able to send it signals

    with pytest.raises(pypsutil.AccessDenied):
        proc.send_signal(signal.SIGINT)
