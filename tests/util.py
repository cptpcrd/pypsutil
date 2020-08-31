import contextlib
import subprocess
import sys
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


def get_dead_process() -> pypsutil.Process:
    subproc = subprocess.Popen([sys.executable, "-c", "exit()"])

    try:
        proc = pypsutil.Process(subproc.pid)
    finally:
        subproc.wait()

    return proc
