import os
import sys

import pytest

import pypsutil

from .util import get_dead_process, macos_only, managed_child_process


def test_environ() -> None:
    env = dict(os.environ)

    with managed_child_process(
        [sys.executable, "-c", "import time; time.sleep(10)", "", "a", ""],
        env=env,
        disable_coverage_env=False,
    ) as proc:
        proc_env = proc.environ()

    # Check that env is a subset of proc.environ()
    # On macOS, proc.environ() includes some extra ifnormation
    for name in env:  # pylint: disable=consider-using-dict-items
        assert env[name] == proc_env[name]


def test_environ_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.environ()


@macos_only
def test_environ_pid_0() -> None:
    proc = pypsutil.Process(0)

    with pytest.raises(pypsutil.AccessDenied):
        proc.environ()
