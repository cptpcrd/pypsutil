import os
import sys

import pytest

import pypsutil

from .util import get_dead_process


def test_exe() -> None:
    proc = pypsutil.Process()

    exe = proc.exe()
    if exe:
        assert os.path.samefile(exe, sys.executable)


def test_exe_no_cmdline() -> None:
    proc = pypsutil.Process()

    exe = proc.exe(fallback_cmdline=False)
    if exe:
        assert os.path.samefile(exe, sys.executable)


def test_exe_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.exe()
