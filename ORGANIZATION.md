# Organization

This page describes the internal organization of `pypsutil`.

## Main source

All the main source code is in `pypsutil/`.

- `__init__` imports appropriate items from `_process` and `_system`. It also defines `PROCFS_PATH`, `DEVFS_PATH`, and `SYSFS_PATH` (on Linux), which can be overridden by the user to change the paths used to access `/proc`, `/dev`, and `/sys`.

- `_errors`  defines the different error types.

- `_detect` detects the OS and imports the appropriate `_ps*` module (e.g. `_pslinux` or `_psmacosx`), which it re-exports under the name `_psimpl`. It also defines the OS detection constants (`LINUX`, `MACOS`, etc.).

    `_process` and `_system` import `_detect` to get the `_psimpl` re-export. `__init__` imports `_detect` to get the OS detection constants.

- `_process` defines the `Process` class, and some helper methods for working with `Process`es. It wraps interfaces defined in the appropriate `_ps*` module that work with process-specific information (not system-wide; that's in `_system`).

- `_system` wraps interfaces defined in the appropriate `_ps*` module that work with system-wide information (e.g. `cpu_times()`, `virtual_memory()`).

- `_cache` defines some basic caching code that's used in the `_ps*` modules to implement `oneshot()`.

- `_ffi` defines some basic, largely non-OS-specific functions/types that help with C FFI and use of `ctypes`.

- `_bsd` defines some wrappers around \*BSD/macOS-specific libc functions. It's used by the appropriate `_ps*` modules.

- `_util` defines "utility" code that is the same across all implementations.

- All of the modules named `_ps*` (`_pslinux`, `_psmacosx`, etc.) expose OS-specific interfaces. `_process` and `_system` call into these modules to perform the actual operations.

    The only exception is that `_psposix` exposes certain interfaces that should work on all UNIX/POSIX-like systems; it is imported and used by the other `_ps*` modules (sort of like `_bsd`).

Some of the functions, classes, etc. defined in certain modules (e.g. `_cache`, `_util`) would more "properly" belong in `_process` or `_system`. However, they also need to be used by the `_ps*` modules. Since `_process`/`_system` import the `_ps*` modules, placing them in `_process`/`_system` would create circular import problems. As a result, they need to be placed in separate modules so that they can be imported by both `_process`/`_system` and `_ps*`.

## Tests

All testing code is in `tests/`, generally named according to the "category" of APIs that each specific module tests. E.g. `test_threads` tests interfaces that expose information on threads.
