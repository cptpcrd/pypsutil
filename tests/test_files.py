# mypy: ignore-errors
import contextlib
import os
import pathlib
import select
import socket
import subprocess
import sys

import pytest

import pypsutil

from .util import (
    get_dead_process,
    linux_only,
    macos_bsd_only,
    managed_child_process2,
    managed_fd,
    managed_pipe,
    populate_directory,
    replace_info_directories,
)

# NetBSD opens an extra file descriptor
if not pypsutil.NETBSD:

    def test_num_fds() -> None:
        with managed_child_process2(
            [sys.executable, "-c", "import time; print('a', flush=True); time.sleep(10)"],
            close_fds=True,
            stdout=subprocess.PIPE,
            bufsize=0,
        ) as proc:
            assert proc.stdout is not None
            assert proc.stdout.read(1) == b"a"

            assert proc.num_fds() == 3


def test_num_fds_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.num_fds()


def test_open_files_empty() -> None:
    with managed_child_process2(
        [sys.executable, "-c", "import time; print('a', flush=True); time.sleep(10)"],
        close_fds=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    ) as proc:
        assert proc.stdout is not None
        assert proc.stdout.read(1) == b"a"

        assert proc.open_files() == []


def test_open_files_2(tmp_path: pathlib.Path) -> None:
    with open(tmp_path / "a", "w", encoding="utf8"):
        pass

    with managed_child_process2(
        [
            sys.executable,
            "-c",
            """
import os, sys, time
fd1 = os.open("/", os.O_RDONLY)
fd2 = os.open(sys.executable, os.O_RDONLY)
fd3 = os.open(sys.argv[1], os.O_RDWR | os.O_APPEND | os.O_CREAT)
print(fd1, fd2, fd3, flush=True)
time.sleep(10)
""",
            str(tmp_path / "a"),
        ],
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    ) as proc:
        assert proc.stdout is not None
        _, fd2, fd3 = map(int, proc.stdout.readline().split())

        open_files = proc.open_files()

        assert len(open_files) == 2

        assert open_files[0].fd == fd2
        if open_files[0].path:
            assert os.path.samefile(open_files[0].path, sys.executable)
        if hasattr(pypsutil.ProcessOpenFile, "flags"):
            assert open_files[0].flags == os.O_RDONLY

        assert open_files[1].fd == fd3
        if open_files[1].path:
            assert os.path.samefile(open_files[1].path, tmp_path / "a")
        if hasattr(pypsutil.ProcessOpenFile, "flags"):
            assert open_files[1].flags == os.O_RDWR | os.O_APPEND | os.O_CREAT


def test_open_files_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        proc.open_files()


def test_iter_fds(tmp_path: pathlib.Path) -> None:
    # pylint: disable=invalid-name

    proc = pypsutil.Process()

    os.mkfifo(tmp_path / "fifo")
    os.mkdir(tmp_path / "dir")

    expect_cloexec = 0 if pypsutil.FREEBSD else os.O_CLOEXEC

    with socket.socket(socket.AF_UNIX) as sock_un, socket.socket(
        socket.AF_INET
    ) as sock_in, managed_pipe() as (r, w), open(
        tmp_path / "fifo",
        "r",
        opener=lambda path, flags: os.open(path, flags | os.O_NONBLOCK),
        encoding="utf8",
    ) as fifo, open(
        tmp_path / "file",
        "w",
        encoding="utf8",
    ) as file, managed_fd(
        os.open(tmp_path / "dir", os.O_RDONLY | os.O_DIRECTORY)
    ) as dirfd:
        sock_un = sock_un.fileno()
        sock_in = sock_in.fileno()
        fifo = fifo.fileno()
        file = file.fileno()

        os.write(w, b"abc")

        pfds = {pfd.fd: pfd for pfd in proc.iter_fds()}

        for fd in [0, 1, 2, sock_un, sock_in, r, w, fifo, file, dirfd]:
            st = os.fstat(fd)
            assert pfds[fd].rdev in (st.st_rdev, None)
            assert pfds[fd].dev in (st.st_dev, None)
            assert pfds[fd].ino in (st.st_ino, None)
            assert pfds[fd].mode in (st.st_mode, None)

        for fd in [0, 1, 2]:
            if pfds[fd].path:
                try:
                    tty = os.ttyname(fd)
                except OSError:
                    pass
                else:
                    assert os.path.samefile(pfds[fd].path, tty)

            if not pypsutil.FREEBSD:
                assert pfds[fd].flags & os.O_CLOEXEC == 0

        for fd in [sock_un, sock_in, r, w, fifo, dirfd]:
            assert pfds[fd].position == 0

            if not pypsutil.FREEBSD:
                assert pfds[fd].flags & os.O_CLOEXEC == os.O_CLOEXEC

        for fd in [sock_un, sock_in, r, w]:
            assert not pfds[fd].path

        if pfds[fifo].path:
            assert os.path.samefile(pfds[fifo].path, tmp_path / "fifo")
        if pfds[file].path:
            assert os.path.samefile(pfds[file].path, tmp_path / "file")
        if pfds[dirfd].path:
            assert os.path.samefile(pfds[dirfd].path, tmp_path / "dir")

        assert pfds[sock_un].fdtype == pypsutil.ProcessFdType.SOCKET
        assert pfds[sock_in].fdtype == pypsutil.ProcessFdType.SOCKET
        assert pfds[r].fdtype == pypsutil.ProcessFdType.PIPE
        assert pfds[w].fdtype == pypsutil.ProcessFdType.PIPE
        assert pfds[fifo].fdtype == pypsutil.ProcessFdType.FIFO
        assert pfds[file].fdtype == pypsutil.ProcessFdType.FILE
        assert pfds[dirfd].fdtype == pypsutil.ProcessFdType.FILE

        assert pfds[file].flags == os.O_WRONLY | expect_cloexec
        assert pfds[fifo].flags == os.O_RDONLY | os.O_NONBLOCK | expect_cloexec
        assert (
            pfds[dirfd].flags
            == os.O_RDONLY
            | (0 if pypsutil.MACOS or pypsutil.BSD else os.O_DIRECTORY)
            | expect_cloexec
        )

        if pypsutil.FREEBSD or pypsutil.MACOS:
            assert pfds[r].extra_info["buffer_cnt"] == 3

        if pypsutil.FREEBSD:
            # FreeBSD looks at this end of the pipe (since they're bidirectional on FreeBSD)
            assert pfds[w].extra_info["buffer_cnt"] == 0
        elif pypsutil.MACOS:
            # macOS switches to the other end of the pipe
            assert pfds[w].extra_info["buffer_cnt"] == 3


@linux_only
def test_iter_fds_epoll(tmp_path: pathlib.Path) -> None:
    # pylint: disable=invalid-name,no-member

    proc = pypsutil.Process()

    os.mkfifo(tmp_path / "fifo")

    with select.epoll() as epoll, managed_pipe() as (r, w), open(
        tmp_path / "fifo",
        "r",
        opener=lambda path, flags: os.open(path, flags | os.O_NONBLOCK),
        encoding="utf8",
    ) as fifo:
        epoll.register(r, select.EPOLLIN)
        epoll.register(w, select.EPOLLOUT)
        epoll.register(fifo.fileno(), select.EPOLLIN)

        epoll = epoll.fileno()
        fifo = fifo.fileno()

        pfds = {pfd.fd: pfd for pfd in proc.iter_fds()}

        st = os.fstat(epoll)
        assert pfds[epoll].rdev in (st.st_rdev, None)
        assert pfds[epoll].dev in (st.st_dev, None)
        assert pfds[epoll].ino in (st.st_ino, None)

        assert pfds[epoll].position == 0
        assert pfds[epoll].flags & os.O_CLOEXEC == os.O_CLOEXEC

        assert not pfds[epoll].path

        assert pfds[epoll].fdtype == pypsutil.ProcessFdType.EPOLL
        assert pfds[r].fdtype == pypsutil.ProcessFdType.PIPE
        assert pfds[w].fdtype == pypsutil.ProcessFdType.PIPE

        tfds = pfds[epoll].extra_info["tfds"]

        assert tfds[r]["pos"] == 0
        assert tfds[r]["events"] == select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP
        assert tfds[r]["ino"] == pfds[r].ino

        assert tfds[w]["pos"] == 0
        assert tfds[w]["events"] == select.EPOLLOUT | select.EPOLLERR | select.EPOLLHUP
        assert tfds[w]["ino"] == pfds[w].ino

        assert tfds[fifo]["pos"] == 0
        assert tfds[fifo]["events"] == select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP
        assert tfds[fifo]["ino"] == pfds[fifo].ino


@macos_bsd_only
def test_iter_fds_kqueue(tmp_path: pathlib.Path) -> None:
    # pylint: disable=invalid-name,no-member

    proc = pypsutil.Process()

    os.mkfifo(tmp_path / "fifo")

    with contextlib.closing(select.kqueue()) as kqueue, managed_pipe() as (r, w), open(
        tmp_path / "fifo",
        "r",
        opener=lambda path, flags: os.open(path, flags | os.O_NONBLOCK),
        encoding="utf8",
    ) as fifo:
        kqueue.control([select.kevent(r, select.KQ_FILTER_READ)], 0)
        kqueue.control([select.kevent(w, select.KQ_FILTER_WRITE)], 0)
        kqueue.control([select.kevent(fifo.fileno(), select.KQ_FILTER_READ)], 0)

        kqueue = kqueue.fileno()
        fifo = fifo.fileno()

        os.write(w, b"abc")

        pfds = {pfd.fd: pfd for pfd in proc.iter_fds()}

        st = os.fstat(kqueue)
        assert pfds[kqueue].rdev in (st.st_rdev, None)
        assert pfds[kqueue].dev in (st.st_dev, None)
        assert pfds[kqueue].ino in (st.st_ino, None)

        assert pfds[kqueue].position == 0

        if not pypsutil.FREEBSD:
            assert pfds[kqueue].flags & os.O_CLOEXEC == os.O_CLOEXEC

        assert not pfds[kqueue].path

        assert pfds[kqueue].fdtype == pypsutil.ProcessFdType.KQUEUE
        assert pfds[r].fdtype == pypsutil.ProcessFdType.PIPE
        assert pfds[w].fdtype == pypsutil.ProcessFdType.PIPE

        if pypsutil.OPENBSD or pypsutil.MACOS:
            assert pfds[kqueue].extra_info["kq_count"] == 2


def test_iter_fds_no_proc() -> None:
    proc = get_dead_process()

    with pytest.raises(pypsutil.NoSuchProcess):
        next(proc.iter_fds())


@linux_only
def test_open_file_mode() -> None:
    assert pypsutil.ProcessOpenFile(path="", fd=3, position=0, flags=os.O_RDONLY).mode == "r"

    assert pypsutil.ProcessOpenFile(path="", fd=3, position=0, flags=os.O_WRONLY).mode == "w"
    assert (
        pypsutil.ProcessOpenFile(path="", fd=3, position=0, flags=os.O_WRONLY | os.O_APPEND).mode
        == "a"
    )

    assert pypsutil.ProcessOpenFile(path="", fd=3, position=0, flags=os.O_RDWR).mode == "r+"
    assert (
        pypsutil.ProcessOpenFile(path="", fd=3, position=0, flags=os.O_RDWR | os.O_APPEND).mode
        == "a+"
    )


@linux_only
def test_open_files_bad_fdinfo(tmp_path: pathlib.Path) -> None:
    populate_directory(
        str(tmp_path),
        {
            "2": {
                "stat": "2 (kthreadd) S 0 0 0 0 -1 0 0 0 0 0 0 0 0 0 20 0 1 0 9 0 0 "
                "18446744073709551615 0 0 0 0 0 0 0 2147483647 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 "
                "0",
                "fd": {
                    "0": ["/bin/sh"],
                    "1": ["/bin/ls"],
                    "2": ["/bin/cat"],
                },
                "fdinfo": {
                    "0": "pos: 10\nmnt_id: 33\nflags: 02\n",
                    "1": "pos: 10\nmnt_id: 33\n",
                },
            },
        },
    )

    # Only file 0 shows up because 1 and 2 have bad fdinfo entries
    with replace_info_directories(procfs=str(tmp_path)):
        assert pypsutil.Process(2).open_files() == [
            pypsutil.ProcessOpenFile(path="/bin/sh", fd=0, position=10, flags=os.O_RDWR)
        ]
