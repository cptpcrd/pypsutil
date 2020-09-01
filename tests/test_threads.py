import contextlib
import subprocess
import sys
import threading
from typing import Iterator

import pytest

import pypsutil

from .util import get_dead_process


@contextlib.contextmanager
def managed_background_thread() -> Iterator[threading.Thread]:
    event = threading.Event()

    thread = threading.Thread(target=event.wait)
    thread.start()

    try:
        yield thread
    finally:
        event.set()
        thread.join()


if hasattr(pypsutil.Process, "num_threads"):

    def test_num_threads_cur() -> None:
        with managed_background_thread():
            nthreads = threading.active_count()
            assert nthreads >= 2

            assert pypsutil.Process().num_threads() == nthreads

    def test_num_threads_subproc() -> None:
        with pypsutil.Popen(
            [
                sys.executable,
                "-c",
                "import time, threading; threading.Thread(target=time.sleep, args=(10,)).start(); "
                "print('a', flush=True); time.sleep(10)",
            ],
            stdout=subprocess.PIPE,
        ) as proc:
            try:
                assert proc.stdout is not None
                assert proc.stdout.read(1) == b"a"

                assert proc.num_threads() == 2
            finally:
                proc.terminate()

    def test_num_threads_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.num_threads()


if hasattr(pypsutil.Process, "threads"):

    def test_threads_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.threads()


if (
    hasattr(pypsutil.Process, "num_threads")
    and hasattr(pypsutil.Process, "threads")
    and hasattr(threading, "get_native_id")
):

    def test_thread_ids_cur() -> None:
        proc = pypsutil.Process()

        with managed_background_thread():
            try:
                threads = proc.threads()
            except pypsutil.AccessDenied:
                pytest.skip("Cannot list threads")
            else:
                assert len(threads) >= 2
                assert len(threads) == proc.num_threads()
                assert len(threads) == threading.active_count()

                assert {thread.native_id for thread in threading.enumerate()} == {
                    thread.id for thread in threads
                }

    def test_thread_ids_subproc() -> None:
        with pypsutil.Popen(
            [
                sys.executable,
                "-c",
                "import time, threading; threading.Thread(target=time.sleep, args=(10,)).start(); "
                "print(*{thread.native_id for thread in threading.enumerate()}, flush=True); "
                "time.sleep(10)",
            ],
            stdout=subprocess.PIPE,
        ) as proc:
            try:
                assert proc.stdout is not None
                thread_ids = set(map(int, proc.stdout.readline().decode().split()))

                try:
                    threads = proc.threads()
                except pypsutil.AccessDenied:
                    pytest.skip("Cannot list threads")
                else:
                    assert len(threads) >= 2
                    assert len(threads) == len(thread_ids)
                    assert {thread.id for thread in threads} == thread_ids

            finally:
                proc.terminate()
