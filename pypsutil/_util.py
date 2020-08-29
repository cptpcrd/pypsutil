import dataclasses
import functools
import resource
import signal
import sys
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Set, Union

from ._errors import AccessDenied, NoSuchProcess

if TYPE_CHECKING:
    from ._process import Process

RESOURCE_NUMS = set()
for name in dir(resource):
    if name.startswith("RLIMIT_"):
        RESOURCE_NUMS.add(getattr(resource, name))


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


def get_procfs_path() -> str:
    return sys.modules[__package__].PROCFS_PATH  # type: ignore


def check_rlimit_resource(res: int) -> None:
    if res not in RESOURCE_NUMS:
        raise ValueError("invalid resource specified")


def expand_sig_bitmask(mask: int) -> Set[Union[signal.Signals, int]]:  # pylint: disable=no-member
    # It seems that every OS uses the same binary representation
    # for signal sets. Only the size varies.

    res = set()
    sig = 1  # Bit 0 in the mask corresponds to signal 1

    while mask:
        if mask & 1:
            sig_val: Union[signal.Signals, int]  # pylint: disable=no-member
            try:
                sig_val = signal.Signals(sig)  # pylint: disable=no-member
            except ValueError:
                sig_val = sig
            res.add(sig_val)

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


def translate_proc_errors(func: Callable[..., Any]) -> Callable[..., Any]:
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

    return wrapper


def read_file(fname: str) -> str:
    with open(fname) as file:
        return file.read()
