import contextlib
import subprocess
import sys
import time
from typing import Any, Iterator, List

import pypsutil


@contextlib.contextmanager
def managed_child_process(args: List[str], **kwargs: Any) -> Iterator[pypsutil.Process]:
    subproc = subprocess.Popen(args, **kwargs)

    psproc = pypsutil.Process(subproc.pid)

    try:
        yield psproc
    finally:
        if psproc.is_running():
            subproc.terminate()
            subproc.wait()


@contextlib.contextmanager
def managed_child_process2(args: List[str], **kwargs: Any) -> Iterator[pypsutil.Popen]:
    proc = pypsutil.Popen(args, **kwargs)  # type: ignore

    try:
        yield proc
    finally:
        if proc.is_running():
            proc.terminate()
            proc.wait()


@contextlib.contextmanager
def managed_zombie_process() -> Iterator[pypsutil.Process]:
    subproc = subprocess.Popen([sys.executable, "-c", "exit()"])

    psproc = pypsutil.Process(subproc.pid)

    while psproc.status() != pypsutil.ProcessStatus.ZOMBIE:
        time.sleep(0.01)

    try:
        yield psproc
    finally:
        subproc.wait()


def get_dead_process() -> pypsutil.Process:
    subproc = subprocess.Popen([sys.executable, "-c", "exit()"])

    try:
        proc = pypsutil.Process(subproc.pid)
    finally:
        subproc.wait()

    return proc
