from typing import Optional, Union


class Error(Exception):
    def __repr__(self) -> str:
        return "pypsutil.Error()"


class NoSuchProcess(Error):
    def __init__(self, pid: Optional[int]) -> None:
        self.pid = pid

    def __repr__(self) -> str:
        return "pypsutil.NoSuchProcess(pid={!r})".format(self.pid)

    def __str__(self) -> str:
        return "pypsutil.NoSuchProcess: PID{} no longer exists".format(
            " " + str(self.pid) if self.pid is not None else ""
        )


class ZombieProcess(NoSuchProcess):
    def __init__(self, pid: Optional[int]) -> None:
        self.pid = pid

    def __repr__(self) -> str:
        return "pypsutil.ZombieProcess(pid={!r})".format(self.pid)

    def __str__(self) -> str:
        return "pypsutil.ZombieProcess: PID{} is a zombie process".format(
            " " + str(self.pid) if self.pid is not None else ""
        )


class AccessDenied(Error):
    def __init__(self, pid: Optional[int]) -> None:
        self.pid = pid

    def __repr__(self) -> str:
        return "pypsutil.AccessDenied(pid={!r})".format(self.pid)

    def __str__(self) -> str:
        return "pypsutil.AccessDenied{}".format(
            " (pid={})".format(self.pid) if self.pid is not None else ""
        )


class TimeoutExpired(Error):
    def __init__(self, seconds: Union[int, float], pid: Optional[int] = None) -> None:
        self.seconds = seconds
        self.pid = pid

    def __repr__(self) -> str:
        return "pypsutil.TimeoutExpired({}, pid={!r})".format(self.seconds, self.pid)

    def __str__(self) -> str:
        return "pypsutil.TimeoutExpired: timeout after {} seconds{}".format(
            self.seconds, " (pid={})".format(self.pid) if self.pid is not None else ""
        )
