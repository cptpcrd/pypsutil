# pylint: disable=no-member
import pypsutil

if hasattr(pypsutil, "virtual_memory") and hasattr(pypsutil, "swap_memory"):

    def test_memory_basic() -> None:
        proc = pypsutil.Process()

        proc_meminfo = proc.memory_info()
        sys_meminfo = pypsutil.virtual_memory()  # type: ignore
        swapinfo = pypsutil.swap_memory()  # type: ignore

        assert proc_meminfo.rss < sys_meminfo.total
        assert proc_meminfo.vms < sys_meminfo.total + swapinfo.total

        if hasattr(proc_meminfo, "text"):
            assert proc_meminfo.text < sys_meminfo.total + swapinfo.total
        if hasattr(proc_meminfo, "data"):
            assert proc_meminfo.data < sys_meminfo.total + swapinfo.total
        if hasattr(proc_meminfo, "stack"):
            assert proc_meminfo.stack < sys_meminfo.total + swapinfo.total  # type: ignore

        assert (
            sys_meminfo.used + sys_meminfo.free + sys_meminfo.buffers + sys_meminfo.cached
            == sys_meminfo.total
        )
