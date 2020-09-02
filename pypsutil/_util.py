import dataclasses
import enum
import functools
import os
import resource
import signal
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    TypeVar,
    Union,
    cast,
)

from ._errors import AccessDenied, NoSuchProcess

if TYPE_CHECKING:
    from ._process import Process

RESOURCE_NUMS = set()
for name in dir(resource):
    if name.startswith("RLIMIT_"):
        RESOURCE_NUMS.add(getattr(resource, name))


CLK_TCK = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
PAGESIZE = os.sysconf(os.sysconf_names["SC_PAGESIZE"])


class ProcessStatus(enum.Enum):
    RUNNING = "running"
    SLEEPING = "sleeping"
    DISK_SLEEP = "disk-sleep"
    ZOMBIE = "zombie"
    STOPPED = "stopped"
    TRACING_STOP = "tracing-stop"
    DEAD = "dead"
    WAKE_KILL = "wake-kill"
    WAKING = "waking"
    PARKED = "parked"
    IDLE = "idle"
    LOCKED = "locked"
    WAITING = "waiting"


@dataclasses.dataclass
class ProcessOpenFile:
    path: str
    fd: int


@dataclasses.dataclass
class ProcessSignalMasks:
    pending: Set[Union[signal.Signals, int]]  # pylint: disable=no-member
    blocked: Set[Union[signal.Signals, int]]  # pylint: disable=no-member
    ignored: Set[Union[signal.Signals, int]]  # pylint: disable=no-member
    caught: Set[Union[signal.Signals, int]]  # pylint: disable=no-member


@dataclasses.dataclass
class ProcessCPUTimes:
    user: float
    system: float
    children_user: float
    children_system: float


@dataclasses.dataclass
class ThreadInfo:
    id: int  # pylint: disable=invalid-name
    user_time: float
    system_time: float


@dataclasses.dataclass
class SwapInfo:
    total: int
    used: int
    free: int
    sin: int
    sout: int

    @property
    def percent(self) -> float:
        return (self.total - self.free) * 100.0 / self.total if self.total else 0


@dataclasses.dataclass
class BatteryInfo:
    name: str
    percent: float
    secsleft: Optional[float]
    secsleft_full: Optional[float]
    power_plugged: Optional[bool]


@dataclasses.dataclass
class ACPowerInfo:
    name: str
    is_online: Optional[bool]


def get_procfs_path() -> str:
    return sys.modules[__package__].PROCFS_PATH  # type: ignore


def check_rlimit_resource(res: int) -> None:
    if res not in RESOURCE_NUMS:
        raise ValueError("invalid resource specified")


def expand_sig_bitmask(
    mask: int, *, include_internal: bool = False
) -> Set[Union[signal.Signals, int]]:  # pylint: disable=no-member
    # It seems that every OS uses the same binary representation
    # for signal sets. Only the size varies.

    res: Set[Union[signal.Signals, int]] = set()  # pylint: disable=no-member
    sig = 1  # Bit 0 in the mask corresponds to signal 1

    while mask:
        if mask & 1:
            try:
                res.add(signal.Signals(sig))  # pylint: disable=no-member
            except ValueError:
                if include_internal or getattr(signal, "SIGRTMIN", float("inf")) <= sig <= getattr(
                    signal, "SIGRTMAX", float("-inf")
                ):
                    res.add(sig)

        mask >>= 1
        sig += 1

    return res


def _iter_null_split_pre(data: bytes) -> Iterator[bytes]:
    i = 0
    while i < len(data):
        zero_index = data.find(b"\0", i)
        if zero_index < 0:
            break
        else:
            yield data[i:zero_index]
            i = zero_index + 1


def parse_cmdline_bytes(cmdline: bytes) -> List[str]:
    return [s.decode() for s in _iter_null_split_pre(cmdline)]


def parse_environ_bytes(env: bytes) -> Dict[str, str]:
    res = {}

    for chunk in _iter_null_split_pre(env):
        index = chunk.find(b"=")
        if index >= 0:
            key = chunk[:index].decode()
            value = chunk[index + 1:].decode()
            res[key] = value

    return res


# https://mypy.readthedocs.io/en/stable/generics.html#declaring-decorators
F = TypeVar("F", bound=Callable[..., Any])  # pylint: disable=invalid-name


def translate_proc_errors(func: F) -> F:
    @functools.wraps(func)
    def wrapper(proc: Union[int, "Process"], *args: Any, **kwargs: Any) -> Any:
        if isinstance(proc, int):
            pid = proc
        else:
            pid = proc.pid

        try:
            return func(proc, *args, **kwargs)
        except ProcessLookupError as ex:
            raise NoSuchProcess(pid=pid) from ex
        except PermissionError as ex:
            raise AccessDenied(pid=pid) from ex

    return cast(F, wrapper)  # pytype: disable=invalid-typevar


def read_file(fname: str) -> str:
    """Read the contents of the given file to a string"""
    with open(fname) as file:
        return file.read()


def read_file_first_line(fname: str) -> str:
    """Read the first line of the given file to a string (removing a single trailing newline if
    one is present)"""

    with open(fname) as file:
        line = file.readline()

    return line[:-1] if line.endswith("\n") else line
