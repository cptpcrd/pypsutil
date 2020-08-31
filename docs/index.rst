Welcome to pypsutil's documentation!
====================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:


About
=====

``pypsutil`` is a partial reimplementation of the popular ``psutil``. It is written in pure
Python (when necessary, it calls library functions using ``ctypes``).

``pypsutil`` vs. ``psutil``
===========================

Reasons to use ``pypsutil`` instead of ``psutil``:

- You do not want dependencies that require C extensions (for whatever reason)
- You need some of the extra features that ``pypsutil`` provides (such as
  :py:meth:`Process.getgroups()` and the increased availability of :py:meth:`Process.rlimit()`)
- You are using a type checker in your project (all of ``pypsutil``'s public interfaces have type
  annotations, unlike ``psutil``)

Reasons **not** to use ``pypsutil`` instead of ``psutil``:

- You need to support Windows, Solaris, and/or AIX (``pypsutil`` currently does not support these
  platforms)
- You need to support Python versions prior to 3.7 (``pypsutil`` is Python 3.7+ only)
- You are concerned about speed (no benchmarks have been conducted, but ``psutil`` is likely faster
  because it is partially written in C)
- You need professional support
- You need some of the features of ``psutil`` that ``pypsutil`` does not provide (check this
  documentation to see if the features you need are present)
- You want a drop-in replacement for ``psutil`` (see the note below)

``pypsutil`` aims to implement many of the features of ``psutil``; however, support is currently
incomplete.

.. important::
   ``pypsutil`` does **NOT** slavishly follow ``psutil``'s API. Specifically:

   - When possible, ``pypsutil`` avoids having a single function perform multiple different
     operations (mainly get vs. set) depending on the arguments it is passed. (Besides being better
     from a design perspective, this simplifies type annotations.)

     For example, ``Process.nice()`` (from ``psutil``) is split into two methods in ``pypsutil``:
     :py:meth:`Process.getpriority()` and :py:meth:`Process.setpriority()`. Similarly, ``psutil``'s
     ``cpu_times(percpu=True|False)`` is split into two functions: :py:func:`cpu_times()` and
     :py:func:`percpu_times()`.

   - If an interface has been added to the standard library that (at least partially) overlaps with
     an interface from ``psutil``, ``pypsutil`` may either a) remove the interface entirely or b)
     remove the portion that overlaps with the standard library, possibly renaming it in the
     process.

     For example, :py:func:`os.cpu_count()` was added in Python 3.4, and it retrieves the same
     information as ``psutil.cpu_count(logical=True)``. As a result, ``pypsutil`` does not offer a
     ``cpu_count()`` function; instead, it offers a :py:func:`physical_cpu_count()` function that
     covers the case of ``psutil.cpu_count(logical=False)``.

Platform Support
================

Currently, the following platforms are supported:

- Linux
- macOS
- FreeBSD
- OpenBSD
- NetBSD

Not all platforms support all interfaces. Availability of different functions on different
platforms is noted in the documentation.

Process information
===================

.. py:class:: Process(pid=None)

   Represents the process with the specified ``pid``. (If ``pid`` is None, the PID of the
   current process is used.)

   This class will retrieve the process's creation time and use the combination of
   PID + creation time to uniquely identify the process, helping to prevent bugs if the
   process exits and the PID is reused by the operating system.

   .. py:attribute:: pid

        The process's PID. This attribute is read-only.

        :type: int

   .. py:method:: ppid()

        Returns the parent process's PID.

        :return: The PID of this process's parent process
        :rtype: int

   .. py:method:: parent()

        Returns a a :py:class:`Process` object representing this process's parent process,
        or ``None`` if the parent process cannot be determined.

        Note: This method preemptively checks if this process's PID has been reused.

        :return:
            a :py:class:`Process` object representing this process's parent process,
            or ``None`` if the parent process cannot be determined
        :rtype: Process or None

   .. py:method:: parents()

        Returns a list of this process's parents. This is a helper that is effectively
        equivalent to calling :py:meth:`parent()` repeatedly until it returns None.

        Note: This method preemptively checks if this process's PID has been reused.

        :return:
            a list of :py:class:`Process` objects representing this process's parents
        :rtype: list[Process]

   .. py:method:: children(\*, recursive=False)

        Get a list of the children of this process. If ``recursive`` is ``True``, includes
        all descendants.

        :param bool recursive:
            If ``True``, include all descendants of this process's children
        :return:
            a list of :py:class:`Process` objects representing this process's children
        :rtype: list[Process]

   .. py:method:: create_time()

        Get the creation time of this process.

        :return: The creation time of this process, in seconds since the Unix epoch
        :rtype: float

   .. py:method:: pgid()

        Get the processs group ID of this process.

        :return: The process group ID of this process
        :rtype: int

   .. py:method:: sid()

        Get the session ID of this process.

        :return: The session ID of this process
        :rtype: int

   .. py:method:: status()

      Get the current process status as one of the members of the :py:class:`ProcessStatus` enum.

      :return: The current process status
      :rtype: ProcessStatus

   .. py:method:: name()

        Get the name of this process.

        :return: The name of this process
        :rtype: str

   .. py:method:: exe()

        Get the path to this process's executable. On some platforms (such as OpenBSD) this
        may return an empty string if it cannot be obtained.

        :return: The path to this process's executable
        :rtype: str

   .. py:method:: cmdline()

        A list of strings representing this process's command line.

        :return: This process's command line as a list of strings
        :rtype: list[str]

   .. py:method:: cwd()

        Get this process's current working directory.

        :return: This process's current working directory
        :rtype: str

   .. py:method:: root()

        Get this process's root directory.

        :return: This process's root directory
        :rtype: str

        Availability: Linux

   .. py:method:: environ()

        Return this process's environmenal variables as a dictionary of strings.

        Note: This may not reflect changes since the process was started.

        :return: This process's environment as a dict
        :rtype: dict[str, str]

   .. py:method:: uids()

        Get the real, effective, and saved UIDs of this process

        :return: A tuple containing the UIDs of this process
        :rtype: tuple[int, int, int]

   .. py:method:: gids()

        Get the real, effective, and saved GIDs of this process

        :return: A tuple containing the GIDs of this process.
        :rtype: tuple[int, int, int]

   .. py:method:: getgroups()

        Get the supplementary group list of this process.

        .. note::
            Currently, on Windows Subsystem for Linux 1 (not on WSL 2), this
            function succeeds but always returns an empty list.

        .. note::
            On macOS, this function's behavior differs from that of
            `os.getgroups() <https://docs.python.org/3/library/os.html#os.getgroups>`_.
            Effectively, it always behaves as if the deployment target is less than 10.5.

        :return: A list of this process's supplementary group IDs.
        :rtype: list[int]

   .. py:method:: username()

        Get the username of the user this process is running as.

        Currently, this just takes the real UID and uses ``pwd.getpwuid()`` to look up
        the username. If that fails, it converts the real UID to a string and returns that.

        :return: The username of the user this process is running as
        :rtype: str

   .. py:method:: umask()

        Get the umask of this process.

        Returns ``None`` if it is not possible to get the umask on the current version of the
        operating system.

        Note: On FreeBSD, this will raise :py:class:`AccessDenied` for PID 0.

        Availability: Linux (4.7+), FreeBSD

        :return: The umask of this process
        :rtype: int or None

   .. py:method:: sigmasks(\*, include_internal=False)

        Get the signal masks of this process.

        This returns a dataclass with several attributes:

        - ``pending`` (not on macOS): The signals that are pending for this process.
        - ``blocked`` (not on macOS): The signals that are blocked for this process (i.e. the
          signal mask set with ``pthread_sigmask()``).
        - ``ignored``: The signals that are ignored by this process (i.e. ``SIG_IGN``).
        - ``caught``: The signals for which this process has registered signal handlers.
        - ``process_pending`` (Linux-only): The signals that are pending for the process as a
          whole, not just this thread.

        All of these are ``set`` objects.

        .. note::
            Currently, on Windows Subsystem for Linux 1 (not on WSL 2), this
            function succeeds but always returns empty sets for all fields.

        :param bool include_internal:
            If this is ``True``, then implementation-internal signals may be included -- for
            example, on Linux this affects the two or three signals used by the glibc/musl POSIX
            threads implementations.
        :return: The signal masks of this process.
        :rtype: ProcessSignalMasks

   .. py:method:: cpu_times()

        Get the accumulated process times.

        This returns a dataclass with several attributes:

        - ``user``: Time spent in user mode
        - ``system``: Time spent in kernel mode
        - ``children_user``: Time spent in user mode by child processes (0 on macOS)
        - ``children_system``: Time spent in kernel mode (0 on macOS)

        Note: On OpenBSD and NetBSD, ``children_user`` and ``children_system`` are both set to the
        combined user + system time.

        :return: The accumulated process times
        :rtype: ProcessSignalMasks

   .. py:method:: rlimit(res, new_limits=None)

      Get/set the soft/hard resource limits of the process. Equivalent to
      ``resource.prlimit(proc.pid, res, new_limits)``, but may be implemented on more platforms.

      .. warning::
           On some platforms, this method may not be able to get/set the limits atomically,
           or to set the soft and hard resource limits together.

           Aside from the potential race conditions this creates, if this method raises
           an error, one or both of the limits may have been changed before the error
           occurred. In this case, no attempts are made to revert the changes.

      :param int res:
           The number of the resource to set (one of the :py:const:`resource.RLIMIT_*` constants)
      :param new_limits:
           The new ``(soft, hard)`` limits to set (or ``None`` to only get the old resource limits).
           Use :py:const:`resource.RLIM_INFINITY` for infinite limits.
      :type new_limits: tuple[int, int] or None
      :return: A tuple of the old ``(soft, hard)`` resource limits
      :rtype: tuple[int, int]

      Availability: Linux, FreeBSD, NetBSD

   .. py:method:: getrlimit(res)

      Get the current soft/hard resource limits of the process. Equivalent to
      ``resource.prlimit(proc.pid, res, None)``, but may be implemented on more platforms.

      Currently, the availability of this method is the same as for :py:meth:`rlimit()`. However, that
      may change if ``pypsutil`` adds supports for platforms that allow for getting, but not setting,
      resource limits for other processes.

      .. note::
            As with :py:meth:`rlimit()`, this method may not be able to get the soft and hard resource
            limits together. As a result, there is a race condition: If the process's resource limits
            are changed while this method is reading them, this method may return a combination such as
            ``(old soft, new hard)`` or ``(new soft, old hard)`` (where "old" means the values before
            the change and "new" means the values after the change).

      :param int res:
           The number of the resource to set (one of the :py:const:`resource.RLIMIT_*` constants)
      :return: A tuple of the current ``(soft, hard)`` resource limits
      :rtype: tuple[int, int]

      Availability: Linux, FreeBSD, NetBSD

   .. py:method:: terminal()

      Get the name of this process's controlling terminal. Returns ``None`` if the process has no
      controlling terminal, or if its name cannot be found.

      .. note::
          In most cases, the name returned by this function will be the same as with the ``tty``
          command or ``os.ttyname(0)``. However, this function returns the name of the process's
          *controlling terminal*; ``tty`` and ``os.ttyname(0)`` return the name of the terminal
          connected to standard input (if the process's standard input is a terminal).

          In most cases, these will be the same thing. However, they are not technically *required*
          to be, and in some edge cases they may be different.

      :return: The name of this process's controlling terminal
      :rtype: str or None

   .. py:method:: getpriority()

      Equivalent to ``os.getpriority(os.PRIO_PROCESS, proc.pid)`` in most cases. (However, on systems
      where the kernel appears as PID 0, ``Process(0).getpriority()`` will actually operate on PID 0.)

      :return: The process's scheduling priority (a.k.a. nice value)
      :rtype: int

   .. py:method:: setpriority(prio)

      Equivalent to ``os.setpriority(os.PRIO_PROCESS, proc.pid, prio)``, but preemptively checks for
      PID reuse.

      (Note: on systems where the kernel appears as PID 0, attempting to set the priority of PID 0
      will always fail with an :py:class:`AccessDenied` exception.)

      :param int prio: The new scheduling priority (a.k.a. nice value) for the process

   .. py:method:: send_signal(sig)

      Send the specified signal to this process, preemptively checking for PID reuse.

      Other than the PID reuse check, this is equivalent to ``os.kill(proc.pid, sig)``.

      :param int sig: The signal number (one of the ``signal.SIG*`` constants)

   .. py:method:: suspend()

      Suspends process execution, preemptively checking for PID reuse. Equivalent to
      ``proc.send_signal(signal.SIGSTOP)``.

   .. py:method:: resume()

      Resumes process execution, preemptively checking for PID reuse. Equivalent to
      ``proc.send_signal(signal.SIGSCONT)``.

   .. py:method:: terminate()

      Terminates the process, preemptively checking for PID reuse. Equivalent to
      ``proc.send_signal(signal.SIGTERM)``.

   .. py:method:: kill()

      Kills the process, preemptively checking for PID reuse. Equivalent to
      ``proc.send_signal(signal.SIGKELL)``.

   .. py:method:: is_running()

      Checks if the process is still running. Unlike ``pid_exists(proc.pid)``, this also checks for PID
      reuse.

      Note: The following methods preemptively check whether the process is still running and raise
      :py:class:`NoSuchProcess` if it has exited:

      - :py:meth:`parent()`
      - :py:meth:`parents()`
      - :py:meth:`children()`
      - :py:meth:`rlimit()` (when setting limits)
      - :py:meth:`setpriority()`
      - :py:meth:`send_signal()`
      - :py:meth:`suspend()`
      - :py:meth:`resume()`
      - :py:meth:`terminate()`
      - :py:meth:`kill()`

      :returns: Whether the process is still running
      :rtype: int

   .. py:method:: wait(\*, timeout=None)

      Wait for the process to exit. If this process was a child of the current process, its exit code is
      returned.

      Raises :py:class:`TimeoutExpired` if the timeout expires.

      :param timeout:
            The maximum amount of time to wait for the process to exit (``None`` signifies no limit).
      :type timeout: int or float or None
      :raises TimeoutExpired: If the timeout expires
      :returns: The exit code of the process if it can be determined; otherwise ``None``
      :rtype: int or None

   .. py:method:: oneshot()

      This is a context manager which enables caching pieces of information that can be obtained via the
      same method.

      Here is a table, in the same format as `psutil.Process.oneshot()'s table
      <https://psutil.readthedocs.io/en/latest/#psutil.Process.oneshot>`_, that shows which methods can
      be grouped together for greater efficiency:

      +---------------------------------+------------------------------------+---------------------------------------+
      | **Linux**                       | **macOS**                          | **FreeBSD**/**OpenBSD**/**NetBSD**    |
      +---------------------------------+------------------------------------+---------------------------------------+
      | :py:meth:`name()`               | :py:meth:`name()`                  | :py:meth:`name()`                     |
      +---------------------------------+------------------------------------+---------------------------------------+
      | :py:meth:`ppid()`               | :py:meth:`ppid()`                  | :py:meth:`ppid()`                     |
      +---------------------------------+------------------------------------+---------------------------------------+
      | :py:meth:`terminal()` [2]_      | :py:meth:`pgid()` [1]_             | :py:meth:`pgid()` [1]_                |
      +---------------------------------+------------------------------------+---------------------------------------+
      |                                 | :py:meth:`uids()`                  | :py:meth:`sid()` [1]_                 |
      +---------------------------------+------------------------------------+---------------------------------------+
      | :py:meth:`uids()`               | :py:meth:`gids()`                  | :py:meth:`uids()`                     |
      +---------------------------------+------------------------------------+---------------------------------------+
      | :py:meth:`gids()`               | :py:meth:`username()`              | :py:meth:`gids()`                     |
      +---------------------------------+------------------------------------+---------------------------------------+
      | :py:meth:`username()`           | :py:meth:`getgroups()`             | :py:meth:`username()`                 |
      +---------------------------------+------------------------------------+---------------------------------------+
      | :py:meth:`getgroups()`          | :py:meth:`terminal()` [2]_         | :py:meth:`getgroups()` [3]_           |
      +---------------------------------+------------------------------------+---------------------------------------+
      | :py:meth:`umask()`              | :py:meth:`sigmasks()`              | :py:meth:`terminal()` [2]_            |
      +---------------------------------+------------------------------------+---------------------------------------+
      | :py:meth:`sigmasks()`           |                                    | :py:meth:`sigmasks()`                 |
      +---------------------------------+------------------------------------+---------------------------------------+

      .. [1] These functions, when called inside a :py:meth:`oneshot()` context manager, will retrieve the
         requested information in a different way that collects as much extra information as possible about
         the process for later use.

      .. [2] Because of implementation details, :py:meth:`terminal()` will likely only see a minor speedup.

      .. [3] On FreeBSD, calling :py:meth:`getgroups()` inside a :py:meth:`oneshot()` will first attempt to retrieve
         the group list via a method that collects as much extra information as possible. However, this method may
         truncate the returned group list. In this case, :py:meth:`getgroups()` will fall back on the normal method,
         which avoids truncation.


.. py:class:: ProcessStatus

   An enum representing a process's status.

   .. py:data:: RUNNING
   .. py:data:: SLEEPING
   .. py:data:: DISK_SLEEP
   .. py:data:: ZOMBIE
   .. py:data:: STOPPED
   .. py:data:: TRACING_STOP
   .. py:data:: DEAD
   .. py:data:: WAKE_KILL
   .. py:data:: WAKING
   .. py:data:: PARKED
   .. py:data:: IDLE
   .. py:data:: LOCKED
   .. py:data:: WAITING


.. py:function:: pids()

   Get a list of the PIDs of running processes.

   :return: A list of the PIDs of running processes.
   :rtype: list[int]


.. py:function:: process_iter()

   Return an iterator over the running processes.

   Note: On Linux, if ``/proc`` is mounted with ``hidepid=1``, it is not possible to get the process
   creation time (or indeed, any information except the PID/UID/GID of the process) of other users'
   processes when running an unprivileged user. This function will raise a :py:class:`AccessDenied` if that
   occurs; if you wish to simply skip these processes then use :py:func:`process_iter_available()`
   instead.

   :rtype: iterator[Process]


.. py:function:: process_iter_available()

   Return an iterator over the running processes, except that a process will be skipped if a
   permission error is encountered while trying to retrieve its creation time. (This can happen, for
   example, on Linux if ``/proc`` is mounted with ``hidepid=1``.)

   :rtype: iterator[Process]


.. py:function:: pid_exists(pid)

   Checks whether a process with the given PID exists. This function will use the most efficient
   method possible to perform this check.

   Note: Use :py:meth:`Process.is_running()` if you want to check whether a :py:class:`Process`
   has exited.

   :param int pid: The PID to check for existence
   :return: Whether the process with the given PID exists
   :rtype: bool


.. py:function:: wait_procs(procs, timeout=None, callback=None)

   Wait for several :py:class:`Process` instances to terminate, and returns ``(gone, alive)`` tuple
   indicating which have terminated and which are still alive.

   If the ``timeout`` expires, this function will not raise :py:class:`TimeoutExpired`.

   :param procs: The processes that should be waited for
   :type procs: iterable[int]
   :param timeout: The maximum amount of time to wait for the processes to terminate
   :type timeout: int or float or None
   :param callback:
        A function which will be called with the :py:class:`Process` as an argument when one of the
        processes exits.
   :rtype: tuple[list[Process], list[Process]]


System information
==================

.. py:function:: boot_time()

   Get the system boot time as a number of seconds since the Unix epoch.

   :return: The system boot time as a number of seconds since the Unix epoch
   :rtype: float

.. py:function:: time_since_boot()

   Get the number of seconds elapsed since the system booted.

   Usually, this is approximately the same as ``time.time() - pypsutil.boot_time()``. However, it
   may be more efficient. (On some systems, :py:func:`boot_time()` may just return ``time.time() -
   pypsutil.time_since_boot()``!)

   :return: The number of seconds elapsed since the system booted
   :rtype: float

.. py:function:: uptime()

   Get the system uptime. This is similar to ``time_since_boot()``, but it does not count time
   the system was suspended.

   :return: The system uptime
   :rtype: float

   Availability: Linux, macOS, FreeBSD, OpenBSD

.. py:function:: disk_usage(path)

   Return disk usage statistics about the filesystem which contains the given ``path``.

   Current attributes:

   - ``total``: Total disk space in bytes
   - ``used``: Total used disk space in bytes
   - ``free``: Disk space in bytes that is free and available for use by unprivileged users
   - ``percent``: Percentage of disk space used (out of the space available to unprivileged users)

   :return:
        A dataclass containing disk usage statistics about the filesystem which contains the given
        ``path``
   :rtype: DiskUsage

.. py:function:: physical_cpu_count()

   Get the number of physical CPUs in the system (i.e. excluding Hyper Threading cores) or``None``
   if that cannot be determined.

   Currently, this always returns ``None`` on OpenBSD and NetBSD.

   :return: The number of physical CPUs in the system (or ``None`` if unable to determine)
   :rtype: int or None

.. py:function:: cpu_freq()

   Returns an instance of a dataclass with ``current``, ``min`, and ``max`` attributes, representing
   the current, minimum, and maximum CPU frequencies.

   :return: An instance of a dataclass containing the current, minimum, and maximum CPU frequencies.
   :rtype: CPUFrequencies

   Availability: Linux


.. py:function:: percpu_freq()

   Identical to :py:func:`cpu_freq()`, but returns a list representing the frequency for each CPU.

   :return: A list of the frequencies of each CPU.
   :rtype: CPUFrequencies

   Availability: Linux


.. py:function:: cpu_times()

   Returns a dataclass containing information about system CPU times. Each attribute represents the
   time in seconds that the CPU has spent in the corresponding mode (since boot):

   - ``user``: Time spent in user mode (includes `guest` time on Linux)
   - ``system``: Time spent in kernel mode
   - ``idle``: Time spent doing nothing

   Extra platform-specific fields:

   - ``nice`` (Linux/BSDs/macOS): Time spent by prioritized processes in user mode (includes
     ``guest_nice`` time on Linux)
   - ``iowait`` (Linux): Time spent waiting for I/O to complete
   - ``irq`` (Linux/BSDs): Time spent servicing hardware interrupts
   - ``softirq`` (Linux): Time spent servicing software interrupts
   - ``lock_spin`` (OpenBSD): Time spent "spinning" on a lock
   - ``steal`` (Linux): Time spent running other operating systems in a virtualize environment
   - ``guest`` (Linux): Time spent running a virtual CPU for a guest operating system
   - ``guest_nice`` (Linux): Time spent running a niced guest

   :returns: A dataclass containing information about system CPU times.
   :rtype: CPUTimes

   Availability: Linux, FreeBSD, OpenBSD, NetBSD


.. py:function:: percpu_times()

   Identical to :py:func:`cpu_times()`, but returns a list representing the times for each CPU.

   :return: A list of the times of each CPU.
   :rtype: CPUTimes

   Availability: Linux, FreeBSD, OpenBSD, NetBSD


.. py:function:: cpu_stats()

   Return a dataclass containing various statistics:

   - ``ctx_switches``: The number of context switches since boot.
   - ``interrupts``: The number of interrupts since boot.
   - ``soft_interrupts``: The number of software interrupts since boot.
   - ``syscalls``: The number of system calls since boot (always 0 on Linux)

   :returns: A dataclass containing some CPU statistics.
   :rtype: CPUStats

   Availablity: Linux


Exceptions
==========

.. py:class:: Error

   Base exception class


.. py:class:: NoSuchProcess(pid)

   Raised by methods of :py:class:`Process` when no process with the given PID is found.


.. py:class:: ZombieProcess(pid)

   Raised by methods of :py:class:`Process` if 1) the process has become a zombie process
   and 2) it is not possible to retrieve the requested information for zombie processes.

   This is a subclass of :py:class:`NoSuchProcess`.


.. py:class:: AccessDenied(pid)

   Raised by methods of :py:class:`Process` when permission to perform an action is denied.


.. py:class:: TimeoutExpired(seconds, pid=None)

   Raised if a timeout expires.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. vim: ts=4 expandtab
