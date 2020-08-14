import os
import sys

import pytest

import pypsutil

from .util import get_dead_process, managed_child_process


def test_environ() -> None:
    env = dict(os.environ)

    with managed_child_process(
        [sys.executable, "-c", "import time; time.sleep(10)", "", "a", ""], env=env
    ) as proc:
        proc_env = proc.environ()

    # Check that env is a subset of proc.environ()
    # On macOS, proc.environ() includes some extra ifnormation
    for name in env:
        assert env[name] == proc_env[name]


def test_environ_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.environ()
