import os
import sys

import pytest

import pypsutil

from .util import fork_proc


def test_send_signal() -> None:
    pypsutil.Process().send_signal(0)


def test_send_signal_no_proc() -> None:
    proc = fork_proc(lambda: sys.exit(0))
    os.waitpid(proc.pid, 0)

    with pytest.raises(ProcessLookupError):
        proc.send_signal(0)
