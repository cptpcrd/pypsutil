import contextlib
import os
import pathlib
import socket
from typing import Dict, Iterable, Iterator, Tuple, Union, cast

import pytest

import pypsutil

from .util import get_dead_process


@contextlib.contextmanager
def open_testing_sockets(
    tmp_path: pathlib.Path,
    *,
    families: Iterable[int] = (socket.AF_INET, socket.AF_INET6, socket.AF_UNIX),
    types: Iterable[int] = (socket.SOCK_STREAM, socket.SOCK_DGRAM, socket.SOCK_SEQPACKET),
) -> Iterator[Dict[int, Tuple[int, int, Union[Tuple[str, int], str], Union[Tuple[str, int], str]]]]:
    socks = []
    info: Dict[int, Tuple[int, int, Union[Tuple[str, int], str], Union[Tuple[str, int], str]]] = {}

    for family in families:
        for stype in types:
            if stype == socket.SOCK_SEQPACKET and family != socket.AF_UNIX:
                continue

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
                try:
                    os.remove(tmp_path / "sock")
                except FileNotFoundError:
                    pass
                sock.bind(str(tmp_path / "sock"))
                laddr = str(tmp_path / "sock")
            elif family == socket.AF_INET6:
                sock.bind(("::1", 0))
                laddr = cast(Tuple[str, int], tuple(sock.getsockname()[:2]))
            else:
                sock.bind(("127.0.0.1", 0))
                laddr = cast(Tuple[str, int], tuple(sock.getsockname()))

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
    for conn in conns:
        family, stype, laddr, raddr = test_socks[conn.fd]
        assert conn.family == family
        assert conn.type == stype
        assert conn.laddr == laddr or conn.laddr == ("" if family == socket.AF_UNIX else ("", 0))
        assert conn.raddr == raddr or conn.raddr == ("" if family == socket.AF_UNIX else ("", 0))


if hasattr(pypsutil.Process, "connections"):

    def test_proc_connections(tmp_path: pathlib.Path) -> None:
        with open_testing_sockets(tmp_path) as test_socks:
            conns = pypsutil.Process().connections("all")
            verify_connections(test_socks, conns)

        with open_testing_sockets(tmp_path, families=[socket.AF_INET]) as test_socks:
            conns = pypsutil.Process().connections("inet")
            verify_connections(test_socks, conns)

        with open_testing_sockets(
            tmp_path, families=[socket.AF_INET, socket.AF_INET6], types=[socket.SOCK_DGRAM]
        ) as test_socks:
            conns = pypsutil.Process().connections("udp")
            verify_connections(test_socks, conns)

        with open_testing_sockets(tmp_path, families=[socket.AF_UNIX]) as test_socks:
            conns = pypsutil.Process().connections("unix")
            verify_connections(test_socks, conns)

        conns = pypsutil.Process().connections("unix")
        verify_connections({}, conns)

    def test_proc_connections_no_proc() -> None:
        proc = get_dead_process()

        with pytest.raises(pypsutil.NoSuchProcess):
            proc.connections()


if hasattr(pypsutil, "net_connections"):

    def test_net_connections_all(tmp_path: pathlib.Path) -> None:
        # pylint: disable=no-member

        cur_pid = os.getpid()

        with open_testing_sockets(
            tmp_path,
        ) as test_socks:
            conns = [
                conn
                for conn in pypsutil.net_connections("all")  # type: ignore[attr-defined]
                if conn.pid == cur_pid
            ]

            verify_connections(test_socks, conns)

        with open_testing_sockets(tmp_path, families=[socket.AF_INET]) as test_socks:
            conns = [
                conn
                for conn in pypsutil.net_connections("inet")  # type: ignore[attr-defined]
                if conn.pid == cur_pid
            ]

            verify_connections(test_socks, conns)

        with open_testing_sockets(
            tmp_path, families=[socket.AF_INET, socket.AF_INET6], types=[socket.SOCK_DGRAM]
        ) as test_socks:
            conns = [
                conn
                for conn in pypsutil.net_connections("udp")  # type: ignore[attr-defined]
                if conn.pid == cur_pid
            ]

            verify_connections(test_socks, conns)

        with open_testing_sockets(tmp_path, families=[socket.AF_UNIX]) as test_socks:
            conns = [
                conn
                for conn in pypsutil.net_connections("unix")  # type: ignore[attr-defined]
                if conn.pid == cur_pid
            ]

            verify_connections(test_socks, conns)

        conns = [
            conn
            for conn in pypsutil.net_connections("unix")  # type: ignore[attr-defined]
            if conn.pid == cur_pid
        ]
        verify_connections({}, conns)
