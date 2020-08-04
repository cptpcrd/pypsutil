import dataclasses
import resource
from typing import Dict, Iterator, List, Set

from . import _get_procfs_path as get_procfs_path  # noqa # pylint: disable=unused-import

RESOURCE_NUMS = set()
for name in dir(resource):
    if name.startswith("RLIMIT_"):
        RESOURCE_NUMS.add(getattr(resource, name))


@dataclasses.dataclass
class ProcessSignalMasks:
    pending: Set[int]
    blocked: Set[int]
    ignored: Set[int]
    caught: Set[int]


def check_rlimit_resource(res: int) -> None:
    if res not in RESOURCE_NUMS:
        raise ValueError("invalid resource specified")


def expand_sig_bitmask(mask: int) -> Set[int]:
    # It seems that every OS uses the same binary representation
    # for signal sets. Only the size varies.

    res = set()
    sig = 1  # Bit 0 in the mask corresponds to signal 1

    while mask:
        if mask & 1:
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
        elif zero_index == i:
            i += 1
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


def trim_after_nul(data: bytes) -> bytes:
    index = data.find(b"\0")
    return data if index < 0 else data[:index]
