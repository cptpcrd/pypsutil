import os
import pathlib
import sys

import pytest

import pypsutil

from .util import get_dead_process, linux_only, populate_directory, replace_info_directories

sys_executable = sys.executable
if pypsutil.WINDOWS and "VIRTUAL_ENV" in os.environ:
    # On Windows, sys.executable points to python.exe inside the virtualenv. However, exe() returns
    # the system-wide (or user-wide) installation path.
    # sys._base_executable does what we want (i.e. original installation path), but it was added in
    # 3.7 (and is semi-private, so it may disappear in the future).
    # So we try to get sys._base_executable, but if that fails then we skip the exe() tests.
    sys_executable = getattr(sys, "_base_executable", "")


@pytest.mark.skipif(
    not sys_executable, reason="sys.executable behaves differently in venvs on Windows"
)
def test_exe() -> None:
    proc = pypsutil.Process()

    exe = proc.exe()
    if exe:
        assert os.path.samefile(exe, sys_executable)


@pytest.mark.skipif(
    not sys_executable, reason="sys.executable behaves differently in venvs on Windows"
)
def test_exe_no_cmdline() -> None:
    proc = pypsutil.Process()

    exe = proc.exe(fallback_cmdline=False)
    if exe:
        assert os.path.samefile(exe, sys_executable)


def test_exe_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.exe()


@linux_only
def test_exe_no_exist(tmp_path: pathlib.Path) -> None:
    populate_directory(
        str(tmp_path),
        {
            "2": {
                "stat": "2 (kthreadd) S 0 0 0 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 9 0 0 "
                "18446744073709551615 0 0 0 0 0 0 0 2147483647 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 "
                "0",
            },
        },
    )

    # Recover gracefully if readlink(/proc/<pid>/exe) fails with ENOENT
    with replace_info_directories(procfs=str(tmp_path)):
        assert pypsutil.Process(2).exe() == ""
