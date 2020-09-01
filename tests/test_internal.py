# pylint: disable=protected-access
import ctypes
import pathlib
import signal
from typing import Iterable

import pytest

import pypsutil
import pypsutil._ffi
import pypsutil._util


def test_ctypes_int_is_signed() -> None:
    assert pypsutil._ffi.ctypes_int_is_signed(ctypes.c_byte)
    assert pypsutil._ffi.ctypes_int_is_signed(ctypes.c_int32)
    assert pypsutil._ffi.ctypes_int_is_signed(ctypes.c_int)
    assert pypsutil._ffi.ctypes_int_is_signed(ctypes.c_long)

    assert not pypsutil._ffi.ctypes_int_is_signed(ctypes.c_ubyte)
    assert not pypsutil._ffi.ctypes_int_is_signed(ctypes.c_uint32)
    assert not pypsutil._ffi.ctypes_int_is_signed(ctypes.c_uint)
    assert not pypsutil._ffi.ctypes_int_is_signed(ctypes.c_ulong)


def test_ctypes_int_min() -> None:
    assert pypsutil._ffi.ctypes_int_min(ctypes.c_byte) == -128
    assert pypsutil._ffi.ctypes_int_min(ctypes.c_int32) == -(2 ** 31)
    assert pypsutil._ffi.ctypes_int_min(ctypes.c_int64) == -(2 ** 63)

    assert pypsutil._ffi.ctypes_int_min(ctypes.c_ubyte) == 0
    assert pypsutil._ffi.ctypes_int_min(ctypes.c_uint32) == 0
    assert pypsutil._ffi.ctypes_int_min(ctypes.c_uint64) == 0


def test_ctypes_int_max() -> None:
    assert pypsutil._ffi.ctypes_int_max(ctypes.c_byte) == 127
    assert pypsutil._ffi.ctypes_int_max(ctypes.c_int32) == 2 ** 31 - 1
    assert pypsutil._ffi.ctypes_int_max(ctypes.c_int64) == 2 ** 63 - 1

    assert pypsutil._ffi.ctypes_int_max(ctypes.c_ubyte) == 255
    assert pypsutil._ffi.ctypes_int_max(ctypes.c_uint32) == 2 ** 32 - 1
    assert pypsutil._ffi.ctypes_int_max(ctypes.c_uint64) == 2 ** 64 - 1


def test_translate_proc_errors() -> None:
    @pypsutil._util.translate_proc_errors
    def raise_helper(pid: int, ex: Exception) -> None:  # pylint: disable=unused-argument
        raise ex

    with pytest.raises(pypsutil.NoSuchProcess):
        raise_helper(1, ProcessLookupError)

    with pytest.raises(pypsutil.AccessDenied):
        raise_helper(1, PermissionError)


def test_parse_cmdline() -> None:
    assert pypsutil._util.parse_cmdline_bytes(b"\0") == [""]
    assert pypsutil._util.parse_cmdline_bytes(b"abc\0") == ["abc"]
    assert pypsutil._util.parse_cmdline_bytes(b"abc\0def\0") == ["abc", "def"]

    # If there isn't a trailing NUL, everything after it is ignored
    assert pypsutil._util.parse_cmdline_bytes(b"") == []
    assert pypsutil._util.parse_cmdline_bytes(b"abc") == []
    assert pypsutil._util.parse_cmdline_bytes(b"abc\0def") == ["abc"]


def test_parse_environ() -> None:
    assert pypsutil._util.parse_environ_bytes(b"\0") == {}
    assert pypsutil._util.parse_environ_bytes(b"abc=def\0") == {"abc": "def"}
    assert pypsutil._util.parse_environ_bytes(b"abc=def\0ghi=jkl\0") == {"abc": "def", "ghi": "jkl"}

    assert pypsutil._util.parse_environ_bytes(b"abc=def\0ghi\0") == {"abc": "def"}
    assert pypsutil._util.parse_environ_bytes(b"abc\0def=ghi\0") == {"def": "ghi"}

    # If there isn't a trailing NUL, everything after it is ignored
    assert pypsutil._util.parse_environ_bytes(b"") == {}
    assert pypsutil._util.parse_environ_bytes(b"abc=def") == {}
    assert pypsutil._util.parse_environ_bytes(b"abc=def\0ghi=jkl") == {"abc": "def"}

    assert pypsutil._util.parse_environ_bytes(b"abc") == {}
    assert pypsutil._util.parse_environ_bytes(b"abc=def\0ghi") == {"abc": "def"}
    assert pypsutil._util.parse_environ_bytes(b"abc\0def=ghi") == {}


def test_read_file(tmp_path: pathlib.Path) -> None:
    with open(tmp_path / "a.txt", "w") as file:
        file.write("abc\ndef")

    assert pypsutil._util.read_file(str(tmp_path / "a.txt")) == "abc\ndef"

    with pytest.raises(FileNotFoundError):
        pypsutil._util.read_file(str(tmp_path / "b.txt"))


def test_expand_sig_bitmask() -> None:
    def build_mask(signals: Iterable[int]) -> int:
        mask = 0
        for sig in signals:
            mask |= 1 << (sig - 1)

        return mask

    external_signals = {1, signal.SIGTERM, max(signal.Signals)}  # pylint: disable=no-member

    internal_signals = {
        max(signal.Signals) + 1,  # pylint: disable=no-member
        max(signal.Signals) + 2,  # pylint: disable=no-member
    }

    sigrtmin = getattr(signal, "SIGRTMIN", None)
    sigrtmax = getattr(signal, "SIGRTMAX", None)

    if sigrtmin is not None and sigrtmax is not None:
        try:
            signal.Signals(sigrtmin - 1)  # pylint: disable=no-member
        except ValueError:
            internal_signals.add(sigrtmin - 1)

        external_signals.update({sigrtmin, sigrtmin + 1, sigrtmax, sigrtmax - 1})

    internal_mask = build_mask(internal_signals)
    external_mask = build_mask(external_signals)
    combined_mask = build_mask(internal_signals | external_signals)

    assert pypsutil._util.expand_sig_bitmask(internal_mask) == set()
    assert (
        pypsutil._util.expand_sig_bitmask(internal_mask, include_internal=True) == internal_signals
    )

    assert pypsutil._util.expand_sig_bitmask(external_mask) == external_signals
    assert (
        pypsutil._util.expand_sig_bitmask(external_mask, include_internal=True) == external_signals
    )

    assert pypsutil._util.expand_sig_bitmask(combined_mask) == external_signals
    assert (
        pypsutil._util.expand_sig_bitmask(combined_mask, include_internal=True)
        == internal_signals | external_signals
    )
