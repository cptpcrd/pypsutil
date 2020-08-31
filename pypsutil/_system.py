# Type checkers don't like the wrapper names not existing.
# mypy: ignore-errors
# pytype: disable=module-attr
import dataclasses
from typing import List, Optional

from . import _util
from ._detect import _psimpl


@dataclasses.dataclass
class CPUFrequencies:
    current: float
    min: float
    max: float


@dataclasses.dataclass
class CPUStats:
    ctx_switches: int
    interrupts: int
    soft_interrupts: int
    syscalls: int


if hasattr(_psimpl, "physical_cpu_count"):

    def physical_cpu_count() -> Optional[int]:
        return _psimpl.physical_cpu_count()


else:

    def physical_cpu_count() -> Optional[int]:
        return None


if hasattr(_psimpl, "cpu_freq"):

    def cpu_freq() -> Optional[CPUFrequencies]:
        result = _psimpl.cpu_freq()

        if result is not None:
            return CPUFrequencies(current=result[0], min=result[1], max=result[2])
        else:
            return None


if hasattr(_psimpl, "cpu_stats"):

    def cpu_stats() -> CPUStats:
        ctx, intr, soft_intr, syscalls = _psimpl.cpu_stats()

        return CPUStats(
            ctx_switches=ctx, interrupts=intr, soft_interrupts=soft_intr, syscalls=syscalls
        )


if hasattr(_psimpl, "percpu_freq"):

    def percpu_freq() -> List[CPUFrequencies]:
        return [
            CPUFrequencies(f_cur, f_min, f_max) for f_cur, f_min, f_max in _psimpl.percpu_freq()
        ]


if hasattr(_psimpl, "cpu_times"):

    CPUTimes = _psimpl.CPUTimes

    def cpu_times() -> CPUTimes:
        return _psimpl.cpu_times()


if hasattr(_psimpl, "percpu_times"):

    def percpu_times() -> List[CPUTimes]:
        return _psimpl.percpu_times()


if hasattr(_psimpl, "virtual_memory"):
    VirtualMemoryInfo = _psimpl.VirtualMemoryInfo

    virtual_memory = _psimpl.virtual_memory


if hasattr(_psimpl, "swap_memory"):
    SwapInfo = _util.SwapInfo

    swap_memory = _psimpl.swap_memory


def boot_time() -> float:
    return _psimpl.boot_time()


def time_since_boot() -> float:
    return _psimpl.time_since_boot()


if hasattr(_psimpl, "uptime"):

    def uptime() -> float:
        return _psimpl.uptime()


DiskUsage = _psimpl.DiskUsage
disk_usage = _psimpl.disk_usage
