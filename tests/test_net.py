import contextlib
import os
import socket
import tempfile
from typing import Dict, Iterable, Iterator, Tuple, Union, cast

import pytest

import pypsutil

from .util import get_dead_process


@contextlib.contextmanager
def open_testing_sockets(
    *,
    families: Iterable[int] = (socket.AF_INET, socket.AF_INET6, socket.AF_UNIX),
    types: Iterable[int] = (socket.SOCK_STREAM, socket.SOCK_DGRAM, socket.SOCK_SEQPACKET),
) -> Iterator[Dict[int, Tuple[int, int, Union[Tuple[str, int], str], Union[Tuple[str, int], str]]]]:
    socks = []
    info: Dict[int, Tuple[int, int, Union[Tuple[str, int], str], Union[Tuple[str, int], str]]] = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        for family in families:
            for stype in types:
                if pypsutil.MACOS and stype == socket.SOCK_SEQPACKET:
                    # macOS doesn't support SOCK_SEQPACKET
                    continue

                if stype == socket.SOCK_SEQPACKET and family != socket.AF_UNIX:
                    continue

                if family == socket.AF_UNIX:
                    sock = socket.socket(family, stype)
                    socks.append(sock)
                    info[sock.fileno()] = (
                        family,
                        stype,
                        ("" if family == socket.AF_UNIX else ("", 0)),
                        ("" if family == socket.AF_UNIX else ("", 0)),
                    )

                sock = socket.socket(family, stype)
                laddr: Union[Tuple[str, int], str]
                if family == socket.AF_UNIX:
                    sock_path = os.path.join(tmpdir, "sock")
                    try:
                        os.remove(sock_path)
                    except FileNotFoundError:
                        pass
                    sock.bind(sock_path)
                    laddr = sock_path
                elif family == socket.AF_INET6:
                    sock.bind(("::1", 0))
                    laddr = cast(Tuple[str, int], tuple(sock.getsockname()[:2]))
                else:
                    sock.bind(("127.0.0.1", 0))
                    laddr = cast(Tuple[str, int], tuple(sock.getsockname()))

                if stype != socket.SOCK_DGRAM:
                    sock.listen(1)

                socks.append(sock)
                info[sock.fileno()] = (
                    family,
                    stype,
                    laddr,
                    ("" if family == socket.AF_UNIX else ("", 0)),
                )

        try:
            yield info
        finally:
            for sock in socks:
                sock.close()


def verify_connections(
    test_socks: Dict[
        int, Tuple[int, int, Union[Tuple[str, int], str], Union[Tuple[str, int], str]]
    ],
    conns: Iterable[pypsutil.Connection],
) -> None:
    test_socks = test_socks.copy()

    for conn in conns:
        family, stype, laddr, raddr = test_socks.pop(conn.fd)
        assert conn.family == family
        assert conn.type == stype
        assert conn.laddr == laddr or conn.laddr == ("" if family == socket.AF_UNIX else ("", 0))
        assert conn.raddr == raddr or conn.raddr == ("" if family == socket.AF_UNIX else ("", 0))

        if stype == socket.SOCK_STREAM and family != socket.AF_UNIX:
            assert conn.status is not None
        else:
            assert conn.status is None

    assert not test_socks


if hasattr(pypsutil.Process, "connections"):

    def test_proc_connections() -> None:
        existing_conn_fds = {conn.fd for conn in pypsutil.Process().connections("all")}

        with open_testing_sockets() as test_socks:
            conns = pypsutil.Process().connections("all")
            verify_connections(
                test_socks, [conn for conn in conns if conn.fd not in existing_conn_fds]
            )

        with open_testing_sockets(families=[socket.AF_INET]) as test_socks:
            conns = pypsutil.Process().connections("inet")
            verify_connections(
                test_socks, [conn for conn in conns if conn.fd not in existing_conn_fds]
            )

        with open_testing_sockets(
            families=[socket.AF_INET, socket.AF_INET6], types=[socket.SOCK_DGRAM]
        ) as test_socks:
            conns = pypsutil.Process().connections("udp")
            verify_connections(
                test_socks, [conn for conn in conns if conn.fd not in existing_conn_fds]
            )

        with open_testing_sockets(families=[socket.AF_UNIX]) as test_socks:
            conns = pypsutil.Process().connections("unix")
            verify_connections(
                test_socks, [conn for conn in conns if conn.fd not in existing_conn_fds]
            )

        conns = pypsutil.Process().connections("unix")
        verify_connections({}, [conn for conn in conns if conn.fd not in existing_conn_fds])

    def test_proc_connections_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.connections()

    def test_proc_connections_bad_kind() -> None:
        assert pypsutil.Process().connections("") == []


if hasattr(pypsutil, "net_connections"):

    def test_net_connections_all() -> None:
        # pylint: disable=no-member

        cur_pid = os.getpid()

        existing_conn_fds = {
            conn.fd
            for conn in pypsutil.net_connections("all")  # type: ignore[attr-defined]
            if conn.pid == cur_pid
        }

        with open_testing_sockets() as test_socks:
            conns = [
                conn
                for conn in pypsutil.net_connections("all")  # type: ignore[attr-defined]
                if conn.pid == cur_pid and conn.fd not in existing_conn_fds
            ]

            verify_connections(test_socks, conns)

        with open_testing_sockets(families=[socket.AF_INET]) as test_socks:
            conns = [
                conn
                for conn in pypsutil.net_connections("inet")  # type: ignore[attr-defined]
                if conn.pid == cur_pid and conn.fd not in existing_conn_fds
            ]

            verify_connections(test_socks, conns)

        with open_testing_sockets(
            families=[socket.AF_INET, socket.AF_INET6], types=[socket.SOCK_DGRAM]
        ) as test_socks:
            conns = [
                conn
                for conn in pypsutil.net_connections("udp")  # type: ignore[attr-defined]
                if conn.pid == cur_pid and conn.fd not in existing_conn_fds
            ]

            verify_connections(test_socks, conns)

        with open_testing_sockets(families=[socket.AF_UNIX]) as test_socks:
            conns = [
                conn
                for conn in pypsutil.net_connections("unix")  # type: ignore[attr-defined]
                if conn.pid == cur_pid and conn.fd not in existing_conn_fds
            ]

            verify_connections(test_socks, conns)

        conns = [
            conn
            for conn in pypsutil.net_connections("unix")  # type: ignore[attr-defined]
            if conn.pid == cur_pid and conn.fd not in existing_conn_fds
        ]
        verify_connections({}, conns)

    def test_net_connections_bad_kind() -> None:
        # pylint: disable=no-member
        assert pypsutil.net_connections("") == []  # type: ignore[attr-defined]
