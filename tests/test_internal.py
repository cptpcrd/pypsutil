# pylint: disable=protected-access
import ctypes

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