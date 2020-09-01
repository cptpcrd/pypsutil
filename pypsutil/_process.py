# Type checkers don't like the wrapper names not existing.
# mypy: ignore-errors
# pytype: disable=module-attr
import collections
import contextlib
import os
import pwd
import resource
import shutil
import signal
import subprocess
import threading
import time
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple, Union, cast

from ._detect import _psimpl
from ._errors import AccessDenied, NoSuchProcess, TimeoutExpired
from ._util import translate_proc_errors

ProcessStatus = _psimpl.ProcessStatus
ProcessSignalMasks = _psimpl.ProcessSignalMasks
ProcessCPUTimes = _psimpl.ProcessCPUTimes
Uids = collections.namedtuple("Uids", ["real", "effective", "saved"])
Gids = collections.namedtuple("Gids", ["real", "effective", "saved"])


class Process:
    _create_time: Optional[float] = None

    def __init__(self, pid: Optional[int] = None) -> None:
        if pid is None:
            pid = os.getpid()

        if pid < 0:
            raise NoSuchProcess(pid=pid)

        self._pid = pid
        self._dead = False
        self._cache: Optional[Dict[str, Any]] = None
        self._lock = threading.RLock()

        # Code that retrieves self._exitcode must hold both self._lock and self._exitcode_lock.
        # Code that performs a *non-blocking* operation and then may assign to self._exitcode
        # must hold self._lock.
        # Code that performs a *blocking* operation and then may assign to self._exitcode must hold
        # self._exitcode_lock.
        self._exitcode: Optional[int] = None
        self._exitcode_lock = threading.RLock()

        self.create_time()

    @classmethod
    def _create(cls, pid: int, create_time: float) -> "Process":
        proc = object.__new__(cls)
        proc._create_time = create_time  # pylint: disable=protected-access
        proc.__init__(pid)
        return cast(Process, proc)

    def _get_cache(self, name: str) -> Any:
        with self._lock:
            if self._cache is None:
                raise KeyError

            return self._cache[name]

    def _set_cache(self, name: str, value: Any) -> None:
        with self._lock:
            if self._cache is not None:
                self._cache[name] = value

    def _is_cache_enabled(self) -> bool:
        with self._lock:
            return self._cache is not None

    @property
    def pid(self) -> int:
        return self._pid

    @translate_proc_errors
    def ppid(self) -> int:
        return _psimpl.proc_ppid(self)

    def _parent_unchecked(self) -> Optional["Process"]:
        ppid = self.ppid()
        if ppid <= 0:
            return None

        try:
            return Process(ppid)
        except NoSuchProcess:
            return None

    def parent(self) -> Optional["Process"]:
        self._check_running()
        return self._parent_unchecked()

    def parents(self) -> List["Process"]:
        self._check_running()

        proc = self
        parents: List[Process] = []

        while True:
            proc = proc._parent_unchecked()  # type: ignore  # pylint: disable=protected-access
            if proc is None:
                return parents

            parents.append(proc)

    def children(self, *, recursive: bool = False) -> List["Process"]:
        self._check_running()

        if recursive:
            search_parents = {self}
            children = []
            children_set = set()

            while True:
                new_search_parents = set()

                # Loop through every process
                for proc in process_iter():
                    try:
                        # We can skip the is_running() check because we literally just got this
                        # PID/create time from the OS
                        proc_parent = proc._parent_unchecked()  # pylint: disable=protected-access
                    except NoSuchProcess:
                        pass
                    else:
                        if proc_parent in search_parents and proc not in children_set:
                            # Its parent is one of the processes we were looking for
                            children.append(proc)
                            children_set.add(proc)
                            # Look for its children next round
                            new_search_parents.add(proc)

                search_parents = new_search_parents
                if not search_parents:
                    break

        else:
            children = []

            for proc in process_iter():
                try:
                    proc_ppid = proc.ppid()
                except NoSuchProcess:
                    pass
                else:
                    if proc_ppid == self.pid:
                        children.append(proc)

        return children

    @translate_proc_errors
    def create_time(self) -> float:
        if self._create_time is None:
            self._create_time = _psimpl.pid_create_time(self._pid)

        return self._create_time

    @translate_proc_errors
    def pgid(self) -> int:
        return _psimpl.proc_pgid(self)

    @translate_proc_errors
    def sid(self) -> int:
        return _psimpl.proc_sid(self)

    @translate_proc_errors
    def status(self) -> ProcessStatus:
        return _psimpl.proc_status(self)

    @translate_proc_errors
    def name(self) -> str:
        return _psimpl.proc_name(self)

    @translate_proc_errors
    def exe(self, *, fallback_cmdline: bool = True) -> str:
        if hasattr(_psimpl, "proc_exe"):
            return _psimpl.proc_exe(self)
        elif fallback_cmdline:
            cmdline = self.cmdline()

            if cmdline:
                lookup_path: Optional[str]
                try:
                    lookup_path = self.environ()["PATH"]
                except (OSError, KeyError):
                    lookup_path = os.environ.get("PATH")

                exe = shutil.which(cmdline[0], path=lookup_path)
                if exe:
                    return exe

        return ""

    @translate_proc_errors
    def cmdline(self) -> List[str]:
        return _psimpl.proc_cmdline(self)

    @translate_proc_errors
    def cwd(self) -> str:
        return _psimpl.proc_cwd(self)

    if hasattr(_psimpl, "proc_root"):

        @translate_proc_errors
        def root(self) -> str:
            return _psimpl.proc_root(self)

    @translate_proc_errors
    def environ(self) -> Dict[str, str]:
        return _psimpl.proc_environ(self)

    @translate_proc_errors
    def uids(self) -> Uids:
        return Uids(*_psimpl.proc_uids(self))

    @translate_proc_errors
    def gids(self) -> Gids:
        return Gids(*_psimpl.proc_gids(self))

    @translate_proc_errors
    def getgroups(self) -> List[int]:
        return _psimpl.proc_getgroups(self)

    def username(self) -> str:
        ruid = self.uids()[0]

        try:
            return pwd.getpwuid(ruid).pw_name
        except KeyError:
            return str(ruid)

    if hasattr(_psimpl, "proc_umask"):

        @translate_proc_errors
        def umask(self) -> Optional[int]:
            return _psimpl.proc_umask(self)

    if hasattr(_psimpl, "proc_sigmasks"):

        @translate_proc_errors
        def sigmasks(self, *, include_internal: bool = False) -> ProcessSignalMasks:
            return _psimpl.proc_sigmasks(self, include_internal=include_internal)

    if hasattr(_psimpl, "proc_rlimit"):

        @translate_proc_errors
        def rlimit(self, res: int, new_limits: Optional[Tuple[int, int]] = None) -> Tuple[int, int]:
            if new_limits is not None:
                self._check_running()

                soft, hard = new_limits

                if soft < 0:
                    soft = resource.RLIM_INFINITY
                if hard < 0:
                    hard = resource.RLIM_INFINITY

                if hard != resource.RLIM_INFINITY and (
                    soft > hard or soft == resource.RLIM_INFINITY
                ):
                    raise ValueError("current limit exceeds maximum limit")

                new_limits = (soft, hard)

            return _psimpl.proc_rlimit(self, res, new_limits)

    if hasattr(_psimpl, "proc_getrlimit"):

        @translate_proc_errors
        def getrlimit(self, res: int) -> Tuple[int, int]:
            return _psimpl.proc_getrlimit(self, res)

    if hasattr(_psimpl, "proc_num_fds"):

        @translate_proc_errors
        def num_fds(self) -> int:
            return _psimpl.proc_num_fds(self)

    if hasattr(_psimpl, "proc_num_threads"):

        @translate_proc_errors
        def num_threads(self) -> int:
            return _psimpl.proc_num_threads(self)

    @translate_proc_errors
    def terminal(self) -> Optional[str]:
        tty_rdev = _psimpl.proc_tty_rdev(self)

        if tty_rdev is not None:
            try:
                with os.scandir("/dev/pts") as pts_names:
                    for entry in pts_names:
                        try:
                            if entry.stat().st_rdev == tty_rdev:
                                return entry.path
                        except OSError:
                            pass
            except FileNotFoundError:
                pass

            with os.scandir("/dev") as dev_names:
                for entry in dev_names:
                    if entry.name.startswith("tty") and len(entry.name) > 3:
                        try:
                            if entry.stat().st_rdev == tty_rdev:
                                return entry.path
                        except OSError:
                            pass

        return None

    @translate_proc_errors
    def cpu_times(self) -> ProcessCPUTimes:
        return _psimpl.proc_cpu_times(self)

    @translate_proc_errors
    def getpriority(self) -> int:
        return _psimpl.proc_getpriority(self)

    @translate_proc_errors
    def setpriority(self, prio: int) -> None:
        if self._pid == 0:
            # Can't change the kernel's priority
            raise PermissionError

        self._check_running()
        os.setpriority(os.PRIO_PROCESS, self._pid, prio)

    @translate_proc_errors
    def send_signal(self, sig: int) -> None:
        if self._pid == 0:
            # Can't send signals to the kernel
            raise PermissionError

        self._check_running()
        os.kill(self._pid, sig)

    def suspend(self) -> None:
        self.send_signal(signal.SIGSTOP)

    def resume(self) -> None:
        self.send_signal(signal.SIGCONT)

    def terminate(self) -> None:
        self.send_signal(signal.SIGTERM)

    def kill(self) -> None:
        self.send_signal(signal.SIGKILL)

    def wait(self, *, timeout: Union[int, float, None] = None) -> Optional[int]:
        if not self.is_running():
            # Simple case
            # Also, checking is_running() up front means we can be sure that self.pid refers to the
            # correct process, so we can call waitpid() with creating potential bugs
            with self._lock, self._exitcode_lock:
                return self._exitcode

        start_time = time.monotonic()

        if timeout is None:
            # Wait with no timeout

            # We don't lock on self._lock because this is blocking
            with self._exitcode_lock:
                try:
                    wstatus = os.waitpid(self.pid, 0)[1]
                except ChildProcessError:
                    # Not a child of the current process
                    # Fall through to the code that checks is_running()
                    pass
                else:
                    self._dead = True
                    self._exitcode = (
                        -os.WTERMSIG(wstatus)
                        if os.WIFSIGNALED(wstatus)
                        else os.WEXITSTATUS(wstatus)
                    )

                    return self._exitcode

        while True:
            with self._lock:
                try:
                    wpid, wstatus = os.waitpid(self.pid, os.WNOHANG)
                except ChildProcessError:
                    # Not a child of the current process
                    # Check is_running()
                    if not self.is_running():
                        with self._exitcode_lock:
                            return self._exitcode
                else:
                    if wpid != 0:
                        self._dead = True
                        self._exitcode = (
                            -os.WTERMSIG(wstatus)
                            if os.WIFSIGNALED(wstatus)
                            else os.WEXITSTATUS(wstatus)
                        )

                        return self._exitcode

            interval = 0.01
            if timeout is not None:
                remaining_time = (start_time + timeout) - time.monotonic() if timeout > 0 else 0
                if remaining_time <= 0:
                    raise TimeoutExpired(timeout, pid=self.pid)

                interval = min(interval, remaining_time / 2)

            time.sleep(interval)

    @contextlib.contextmanager
    def oneshot(self) -> Iterator[None]:
        with self._lock:
            if self._cache is None:
                self._cache = {}
                yield
                self._cache = None
            else:
                yield

    @translate_proc_errors
    def _check_running(self) -> None:
        if not self.is_running():
            raise ProcessLookupError

    def is_running(self) -> bool:
        with self._lock:
            if self._dead:
                return False

            try:
                self._dead = self != Process(self._pid)
            except NoSuchProcess:
                self._dead = True

            return not self._dead

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Process):
            return self._pid == other._pid and self._create_time == other._create_time

        return NotImplemented

    def __hash__(self) -> int:
        return hash((self._pid, self._create_time))

    def __repr__(self) -> str:
        return "{}(pid={})".format(self.__class__.__name__, self._pid)


class Popen(Process):
    def __init__(
        self,
        args: Union[List[Union[str, bytes, "os.PathLike[str]", "os.PathLike[bytes]"]], str, bytes],
        **kwargs: Any
    ) -> None:
        proc = subprocess.Popen(args, **kwargs)
        super().__init__(proc.pid)

        self._proc = proc

        self.args = proc.args
        self.stdin = proc.stdin
        self.stdout = proc.stdout
        self.stderr = proc.stdout

    def poll(self) -> Optional[int]:
        res = self._proc.poll()
        if res is not None:
            self._dead = True
        return res

    def wait(  # pylint: disable=arguments-differ
        self, timeout: Union[int, float, None] = None
    ) -> int:
        try:
            res = self._proc.wait(timeout)
        except subprocess.TimeoutExpired as ex:
            raise TimeoutExpired(timeout, self.pid) from ex
        else:
            self._dead = True
            return res

    def communicate(
        self,
        input: Union[str, bytes, None] = None,  # pylint: disable=redefined-builtin
        timeout: Union[int, float, None] = None,
    ) -> Tuple[Union[str, bytes, None], Union[str, bytes, None]]:
        try:
            res = self._proc.communicate(input, timeout)
        except subprocess.TimeoutExpired as ex:
            raise TimeoutExpired(timeout, self.pid) from ex
        else:
            self._dead = True
            return res

    @property
    def returncode(self) -> Optional[int]:
        return self._proc.returncode

    def __enter__(self) -> "Popen":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if self.stdin is not None:
            self.stdin.close()

        if self.stdout is not None:
            self.stdout.close()

        if self.stderr is not None:
            self.stderr.close()

        self.wait()


def pids() -> List[int]:
    return list(_psimpl.iter_pids())


def process_iter() -> Iterator[Process]:
    return _process_iter_impl(skip_perm_error=False)


def process_iter_available() -> Iterator[Process]:
    return _process_iter_impl(skip_perm_error=True)


_process_iter_cache: Dict[int, Process] = {}
_process_iter_cache_lock = threading.RLock()


def _process_iter_impl(*, skip_perm_error: bool = False) -> Iterator[Process]:
    seen_pids = set()

    for (pid, create_time) in _psimpl.iter_pid_create_time(skip_perm_error=skip_perm_error):
        seen_pids.add(pid)

        try:
            # Check the cache
            with _process_iter_cache_lock:
                proc = _process_iter_cache[pid]
        except KeyError:
            # Cache failure
            pass
        else:
            # Cache hit
            if proc.create_time() == create_time:
                # It's the same process
                yield proc
                continue
            else:
                # Different process
                with _process_iter_cache_lock:
                    # There's a potential race condition here.
                    # Between the time when we first checked the cache and now,
                    # another thread might have also checked the cache, found
                    # this process doesn't exist, and removed it.
                    # We handle that by using pop() instead of 'del' to remove
                    # the entry, so we don't get an error if it's not present.
                    _process_iter_cache.pop(pid, None)

        proc = Process._create(pid, create_time)  # pylint: disable=protected-access
        with _process_iter_cache_lock:
            # There's also a potential race condition here.
            # Another thread might have already populated the cache entry, and we
            # may be overwriting it.
            # However, the only cost is a small increase in memory because we're
            # keeping track of an extra Process object. That's not enough
            # to be concerned about.
            _process_iter_cache[pid] = proc

        yield proc

    # If we got to the end, clean up the cache

    # List the cached PIDs
    with _process_iter_cache_lock:
        cached_pids = list(_process_iter_cache.keys())

    # Find all of the ones that don't exist anymore
    bad_pids = set(cached_pids) - seen_pids

    # Remove them
    with _process_iter_cache_lock:
        for bad_pid in bad_pids:
            # Potential race condition (similar to the ones described above)
            _process_iter_cache.pop(bad_pid, None)


def pid_exists(pid: int) -> bool:
    if pid < 0:
        return False

    try:
        if pid > 0:
            os.kill(pid, 0)
        else:
            _psimpl.pid_create_time(pid)
    except (ProcessLookupError, NoSuchProcess):
        return False
    except (PermissionError, AccessDenied):
        return True
    else:
        return True


def wait_procs(
    procs: Iterable[Process],
    timeout: Union[int, float, None] = None,
    callback: Optional[Callable[[Process], None]] = None,
) -> Tuple[List[Process], List[Process]]:
    start_time = time.monotonic()

    gone = list()
    alive = list(procs)

    while alive:
        for proc in list(alive):
            try:
                res = proc.wait(timeout=0)
            except TimeoutExpired:
                pass
            else:
                proc.returncode = res

                if callback is not None:
                    callback(proc)

                alive.remove(proc)
                gone.append(proc)

        interval = 0.01
        if timeout is not None:
            remaining_time = (start_time + timeout) - time.monotonic() if timeout > 0 else 0
            if remaining_time <= 0:
                break

            interval = min(interval, remaining_time / 2)

        time.sleep(interval)

    return gone, alive
