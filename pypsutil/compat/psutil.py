import os
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    cast,
    overload,
)

import pypsutil


class Process:
    _proc: pypsutil.Process

    def __init__(self, pid: Optional[int] = None) -> None:
        self._proc = pypsutil.Process(pid)

    @classmethod
    def _wrap(cls, proc: pypsutil.Process) -> "Process":
        res = object.__new__(Process)
        res._proc = proc  # pylint: disable=protected-access
        return cast(Process, res)

    @property
    def pid(self) -> int:
        return self._proc.pid

    def ppid(self) -> int:
        return self._proc.ppid()

    def parent(self) -> Optional["Process"]:
        parent = self._proc.parent()
        return Process._wrap(parent) if parent is not None else None

    def parents(self) -> List["Process"]:
        return [Process._wrap(proc) for proc in self._proc.parents()]

    def children(self, recursive: bool = False) -> List["Process"]:
        return [Process._wrap(proc) for proc in self._proc.children(recursive=recursive)]

    def create_time(self) -> float:
        return self._proc.create_time()

    def pgid(self) -> int:
        return self._proc.pgid()

    def sid(self) -> int:
        return self._proc.sid()

    def status(self) -> pypsutil.ProcessStatus:
        return self._proc.status()

    def name(self) -> str:
        return self._proc.name()

    def exe(self) -> str:
        return self._proc.exe()

    def cmdline(self) -> List[str]:
        return self._proc.cmdline()

    def cwd(self) -> str:
        return self._proc.cwd()

    def environ(self) -> Dict[str, str]:
        return self._proc.environ()

    def uids(self) -> pypsutil.Uids:
        return self._proc.uids()

    def gids(self) -> pypsutil.Gids:
        return self._proc.gids()

    def username(self) -> str:
        return self._proc.username()

    def terminal(self) -> Optional[str]:
        return self._proc.terminal()

    @overload
    def nice(self, value: int) -> None:
        ...

    @overload
    def nice(self, value: None = None) -> int:
        ...

    def nice(self, value: Optional[int] = None) -> Optional[int]:
        if value is not None:
            self._proc.setpriority(value)
            return None
        else:
            return self._proc.getpriority()

    if pypsutil.LINUX:

        @overload
        def rlimit(self, resource: int, limits: Tuple[int, int]) -> None:
            ...

        @overload
        def rlimit(self, resource: int, limits: None = None) -> Tuple[int, int]:
            ...

        def rlimit(
            self, resource: int, limits: Optional[Tuple[int, int]] = None
        ) -> Optional[Tuple[int, int]]:
            res = self._proc.rlimit(resource, limits)

            return res if limits is None else None

    def cpu_times(self) -> pypsutil.ProcessCPUTimes:
        return self._proc.cpu_times()

    def is_running(self) -> bool:
        return self._proc.is_running()

    def send_signal(self, sig: int) -> None:
        self._proc.send_signal(sig)

    def suspend(self) -> None:
        self._proc.suspend()

    def resume(self) -> None:
        self._proc.resume()

    def terminate(self) -> None:
        self._proc.terminate()

    def kill(self) -> None:
        self._proc.kill()

    def wait(self, timeout: Union[int, float, None] = None) -> Optional[int]:
        return self._proc.wait(timeout=timeout)

    def __repr__(self) -> str:
        return "pypsutil.compat.psutil.{}(pid={})".format(self.__class__.__name__, self.pid)


class Popen(Process):
    _proc: pypsutil.Popen

    def __init__(  # pylint: disable=super-init-not-called
        self,
        args: Union[List[Union[str, bytes, "os.PathLike[str]", "os.PathLike[bytes]"]], str, bytes],
        **kwargs: Any
    ) -> None:
        self._proc = pypsutil.Popen(args, **kwargs)

        self.args = self._proc.args
        self.stdin = self._proc.stdin
        self.stdout = self._proc.stdout
        self.stderr = self._proc.stderr

    def poll(self) -> Optional[int]:
        return self._proc.poll()

    def wait(self, timeout: Union[int, float, None] = None) -> int:
        return self._proc.wait(timeout=timeout)

    def communicate(
        self,
        input: Union[str, bytes, None] = None,  # pylint: disable=redefined-builtin
        timeout: Union[int, float, None] = None,
    ) -> Tuple[Union[str, bytes, None], Union[str, bytes, None]]:
        return self._proc.communicate(input, timeout)

    @property
    def returncode(self) -> Optional[int]:
        return self._proc.returncode

    def __enter__(self) -> "Popen":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self._proc.__exit__(exc_type, exc_value, traceback)


pids = pypsutil.pids
pid_exists = pypsutil.pid_exists


def process_iter() -> Iterator[Process]:
    for proc in pypsutil.process_iter():
        yield Process._wrap(proc)  # pylint: disable=protected-access


def wait_procs(
    procs: Iterable[Process],
    timeout: Union[int, float, None] = None,
    callback: Optional[Callable[[Process], None]] = None,
) -> Tuple[List[Process], List[Process]]:
    proc_map: Dict[pypsutil.Process, Process] = {
        proc._proc: proc  # pylint: disable=protected-access  # type: ignore
        for proc in procs  # pytype: disable=annotation-type-mismatch
    }

    def inner_callback(inner_proc: pypsutil.Process) -> None:
        proc = proc_map[inner_proc]

        proc.returncode = inner_proc.returncode  # type: ignore

        if callback is not None:
            callback(proc)

    gone, alive = pypsutil.wait_procs(
        proc_map.keys(),
        timeout=timeout,
        callback=inner_callback,
    )

    return [proc_map[proc] for proc in gone], [proc_map[proc] for proc in alive]


boot_time = pypsutil.boot_time
time_since_boot = pypsutil.time_since_boot

if hasattr(pypsutil, "uptime"):
    uptime = pypsutil.uptime  # type: ignore  # pylint: disable=no-member


def cpu_count(logical: bool = True) -> Optional[int]:
    return os.cpu_count() if logical else pypsutil.physical_cpu_count()


if (
    hasattr(pypsutil, "cpu_times")
    and hasattr(pypsutil, "percpu_times")
    and hasattr(pypsutil, "CPUTimes")
):

    # pylint: disable=no-member

    @overload
    def cpu_times(percpu: False = False) -> pypsutil.CPUTimes:  # type: ignore
        ...

    @overload
    def cpu_times(percpu: True) -> List[pypsutil.CPUTimes]:  # type: ignore
        ...

    def cpu_times(
        percpu: bool = False,
    ) -> Union[pypsutil.CPUTimes, List[pypsutil.CPUTimes]]:  # type: ignore
        return pypsutil.percpu_times() if percpu else pypsutil.cpu_times()  # type: ignore
