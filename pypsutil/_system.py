# Type checkers don't like the wrapper names not existing.
# mypy: ignore-errors
# pytype: disable=module-attr
import dataclasses
from typing import List, Optional

from . import _util
from ._detect import _psimpl

SwapInfo = _util.SwapInfo

PowerSupplySensorInfo = _util.PowerSupplySensorInfo
ACPowerInfo = _util.ACPowerInfo
BatteryInfo = _util.BatteryInfo
BatteryStatus = _util.BatteryStatus


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
    swap_memory = _psimpl.swap_memory

if hasattr(_psimpl, "sensors_power"):
    sensors_power = _psimpl.sensors_power
    sensors_is_on_ac_power = _psimpl.sensors_is_on_ac_power

    def sensors_battery() -> Optional[BatteryInfo]:
        psinfo = sensors_power()
        if not psinfo.batteries:
            return None

        battery = psinfo.batteries[0]

        if battery.power_plugged is None:
            battery._power_plugged = psinfo.is_on_ac_power  # pylint: disable=protected-access

        return battery

    def sensors_battery_total() -> Optional[BatteryInfo]:
        psinfo = sensors_power()
        if not psinfo.batteries:
            if hasattr(_psimpl, "sensors_battery_total_alt"):
                return _psimpl.sensors_battery_total_alt(psinfo.is_on_ac_power)
            else:
                return None

        total_energy_full = 0
        total_energy_now = 0

        total_discharge_rate = 0
        total_charge_rate = 0

        for battery in psinfo.batteries:
            total_energy_full += battery.energy_full or 0
            total_energy_now += battery.energy_now or 0

            if battery.status == BatteryStatus.CHARGING:
                total_charge_rate += battery.power_now or 0
            elif battery.status == BatteryStatus.DISCHARGING:
                total_discharge_rate += battery.power_now or 0

        if total_energy_full == 0:
            return None
        percent = total_energy_now * 100 / total_energy_full

        power_now = None

        if any(battery.status == BatteryStatus.CHARGING for battery in psinfo.batteries) and all(
            battery.status in (BatteryStatus.CHARGING, BatteryStatus.FULL)
            for battery in psinfo.batteries
        ):
            # At least one battery charging, all either charging or full
            status = BatteryStatus.CHARGING
            power_now = total_charge_rate
        elif any(
            battery.status == BatteryStatus.DISCHARGING for battery in psinfo.batteries
        ) and all(
            battery.status in (BatteryStatus.DISCHARGING, BatteryStatus.FULL)
            for battery in psinfo.batteries
        ):
            # At least one battery discharging, all either discharging or full
            status = BatteryStatus.DISCHARGING
            power_now = total_discharge_rate
        elif all(battery.status == BatteryStatus.FULL for battery in psinfo.batteries):
            # All full
            status = BatteryStatus.FULL
        else:
            status = BatteryStatus.UNKNOWN

        return BatteryInfo(
            name="Combined",
            percent=percent,
            energy_full=total_energy_full,
            energy_now=total_energy_now,
            power_now=power_now,
            _power_plugged=psinfo.is_on_ac_power,
            status=status,
        )


if hasattr(_psimpl, "sensors_temperatures"):
    TempSensorInfo = _psimpl.TempSensorInfo

    sensors_temperatures = _psimpl.sensors_temperatures


boot_time = _psimpl.boot_time


time_since_boot = _psimpl.time_since_boot


if hasattr(_psimpl, "uptime"):
    uptime = _psimpl.uptime


DiskUsage = _psimpl.DiskUsage
disk_usage = _psimpl.disk_usage
