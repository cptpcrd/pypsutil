import os
import sys

import pytest

import pypsutil

from .util import get_dead_process, managed_child_process


def test_cmdline() -> None:
    valid_names = {
        os.path.basename(sys.executable),
        os.path.basename(os.path.realpath(sys.executable)),
    }

    with managed_child_process([sys.executable, "-c", "import time; time.sleep(10)"]) as proc:
        assert proc.name() in valid_names


def test_name_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.name()
