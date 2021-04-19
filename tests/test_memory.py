# mypy: ignore-errors
# pylint: disable=no-member
import os
import sys

import pytest

import pypsutil

from .util import get_dead_process

if hasattr(pypsutil, "virtual_memory") and hasattr(pypsutil, "swap_memory"):

    def test_memory_basic() -> None:
        proc = pypsutil.Process()

        proc_meminfo = proc.memory_info()
        sys_meminfo = pypsutil.virtual_memory()
        swapinfo = pypsutil.swap_memory()

        assert proc_meminfo.rss < sys_meminfo.total
        assert proc_meminfo.vms < sys_meminfo.total + swapinfo.total

        if hasattr(proc_meminfo, "text"):
            assert proc_meminfo.text < sys_meminfo.total + swapinfo.total
        if hasattr(proc_meminfo, "data"):
            assert proc_meminfo.data < sys_meminfo.total + swapinfo.total
        if hasattr(proc_meminfo, "stack"):
            assert proc_meminfo.stack < sys_meminfo.total + swapinfo.total

        assert (
            sys_meminfo.used
            + sys_meminfo.free
            + getattr(sys_meminfo, "buffers", 0)
            + getattr(sys_meminfo, "cached", 0)
            <= sys_meminfo.total
        )


def test_memory_info_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.memory_info()


if hasattr(pypsutil.Process, "memory_maps"):

    def test_memory_maps_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.memory_maps()


@linux_only
def test_memory_maps_grouped() -> None:
    # pylint: disable=no-member
    mmaps = {
        os.path.realpath(mmap.path): mmap for mmap in pypsutil.Process().memory_maps_grouped()
    }

    exe_mmap = mmaps[os.path.realpath(sys.executable)]
    exe_stat = os.stat(sys.executable)
    assert exe_stat.st_ino == exe_mmap.ino
    assert exe_stat.st_dev == exe_mmap.dev
