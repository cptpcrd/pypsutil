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
    physical_cpu_count = _psimpl.physical_cpu_count
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

    cpu_times = _psimpl.cpu_times


if hasattr(_psimpl, "percpu_times"):
    percpu_times = _psimpl.percpu_times


if hasattr(_psimpl, "virtual_memory"):
    VirtualMemoryInfo = _psimpl.VirtualMemoryInfo

    virtual_memory = _psimpl.virtual_memory


if hasattr(_psimpl, "swap_memory"):
    SwapInfo = _util.SwapInfo

    swap_memory = _psimpl.swap_memory

if hasattr(_psimpl, "sensors_power"):
    ACPowerInfo = _psimpl.ACPowerInfo
    BatteryInfo = _psimpl.BatteryInfo
    BatteryStatus = _psimpl.BatteryStatus

    sensors_power = _psimpl.sensors_power
    sensors_battery = _psimpl.sensors_battery
    sensors_is_on_ac_power = _psimpl.sensors_is_on_ac_power

if hasattr(_psimpl, "sensors_battery_total"):
    sensors_battery_total = _psimpl.sensors_battery_total

if hasattr(_psimpl, "sensors_temperatures"):
    TempSensorInfo = _psimpl.TempSensorInfo

    sensors_temperatures = _psimpl.sensors_temperatures


boot_time = _psimpl.boot_time


time_since_boot = _psimpl.time_since_boot


if hasattr(_psimpl, "uptime"):
    uptime = _psimpl.uptime


DiskUsage = _psimpl.DiskUsage
disk_usage = _psimpl.disk_usage
