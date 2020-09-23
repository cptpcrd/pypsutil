import contextlib
import os
import subprocess
import sys
import time
from typing import Any, Dict, Iterator, List, Optional

import pytest

import pypsutil

macos_only = pytest.mark.skipif(sys.platform != "darwin", reason="Tests Linux-specific behavior")
linux_only = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="Tests Linux-specific behavior"
)


def _rewrite_kwargs(kwargs: Dict[str, Any]) -> None:
    if kwargs.pop("disable_coverage_env", True):
        # Remove the environmental variables that enable subprocess coverage
        # Subprocess coverage measurement doesn't work when passing programs with
        # "python -c ...", and it leaves the data files around if the tests fail or the
        # programs get killed.

        env = kwargs.pop("env", None)
        if env is None:
            env = os.environ
        env = dict(env)

        env.pop("COV_CORE_DATAFILE", None)

        kwargs["env"] = env


@contextlib.contextmanager
def managed_child_process(args: List[str], **kwargs: Any) -> Iterator[pypsutil.Process]:
    _rewrite_kwargs(kwargs)

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
    _rewrite_kwargs(kwargs)

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


@contextlib.contextmanager
def replace_info_directories(
    *, procfs: Optional[str] = None, sysfs: Optional[str] = None
) -> Iterator[None]:
    old_procfs = pypsutil.PROCFS_PATH
    old_sysfs = getattr("pypsutil", "SYSFS_PATH", None)

    try:
        if procfs is not None:
            pypsutil.PROCFS_PATH = procfs

        if sysfs is not None:
            pypsutil.SYSFS_PATH = sysfs

        yield
    finally:
        pypsutil.PROCFS_PATH = old_procfs

        if old_sysfs is not None:
            pypsutil.SYSFS_PATH = old_sysfs


def populate_directory(root_dir: str, structure: Dict[str, Any]) -> None:
    for name, item in structure.items():
        path = os.path.join(root_dir, name)

        if isinstance(item, str):
            with open(path, "x") as file:
                file.write(item)
        elif isinstance(item, list):
            assert len(item) == 1
            os.symlink(item[0], path)
        else:
            os.mkdir(path)
            populate_directory(path, item)
