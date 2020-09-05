import sys

import pytest

import pypsutil

from .util import get_dead_process, macos_only, managed_child_process


def test_cmdline() -> None:
    args = [sys.executable, "-c", "import time; time.sleep(10)", "", "a", ""]
    with managed_child_process(args) as proc:
        assert proc.cmdline() == args


def test_cmdline_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.cmdline()


@macos_only  # type: ignore
def test_cmdline_pid_0() -> None:
    proc = pypsutil.Process(0)

    with pytest.raises(pypsutil.AccessDenied):
        proc.cmdline()
