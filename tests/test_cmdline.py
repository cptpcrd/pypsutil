import pathlib
import sys

import pytest

import pypsutil

from .util import (
    get_dead_process,
    linux_only,
    macos_only,
    managed_child_process,
    populate_directory,
    replace_info_directories,
)


def test_cmdline() -> None:
    args = [sys.executable, "-c", "import time; time.sleep(10)", "", "a", ""]
    with managed_child_process(args) as proc:
        assert proc.cmdline() == args


def test_cmdline_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.cmdline()


@macos_only
def test_cmdline_pid_0() -> None:
    proc = pypsutil.Process(0)

    with pytest.raises(pypsutil.AccessDenied):
        proc.cmdline()


@linux_only
def test_cmdline_empty(tmp_path: pathlib.Path) -> None:
    populate_directory(
        str(tmp_path),
        {
            "2": {
                "stat": "2 (kthreadd) S 0 0 0 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 9 0 0 "
                "18446744073709551615 0 0 0 0 0 0 0 2147483647 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 "
                "0",
                "cmdline": "",
            },
        },
    )

    # Kernel processes have an empty command line. They are handled separately from zombie
    # processes, which also have an empty command line.
    with replace_info_directories(procfs=str(tmp_path)):
        assert pypsutil.Process(2).cmdline() == []
