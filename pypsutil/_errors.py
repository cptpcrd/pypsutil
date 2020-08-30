from typing import Optional, Union


class Error(Exception):
    pass


class NoSuchProcess(Error):
    def __init__(self, pid: int) -> None:
        super().__init__()
        self.pid = pid

    def __repr__(self) -> str:
        return "pypsutil.NoSuchProcess(pid={!r})".format(self.pid)

    def __str__(self) -> str:
        return "pypsutil.NoSuchProcess: process does not exist (pid={})".format(self.pid)


class ZombieProcess(NoSuchProcess):
    def __repr__(self) -> str:
        return "pypsutil.ZombieProcess(pid={!r})".format(self.pid)

    def __str__(self) -> str:
        return "pypsutil.ZombieProcess: process exists but is a zombie (pid={})".format(self.pid)


class AccessDenied(Error):
    def __init__(self, pid: int) -> None:
        super().__init__()
        self.pid = pid

    def __repr__(self) -> str:
        return "pypsutil.AccessDenied(pid={!r})".format(self.pid)

    def __str__(self) -> str:
        return "pypsutil.AccessDenied{}".format(
            " (pid={})".format(self.pid) if self.pid is not None else ""
        )


class TimeoutExpired(Error):
    def __init__(self, seconds: Union[int, float], pid: Optional[int] = None) -> None:
        super().__init__()
        self.seconds = seconds
        self.pid = pid

    def __repr__(self) -> str:
        return "pypsutil.TimeoutExpired({}, pid={!r})".format(self.seconds, self.pid)

    def __str__(self) -> str:
        return "pypsutil.TimeoutExpired: timeout after {} seconds{}".format(
            self.seconds, " (pid={})".format(self.pid) if self.pid is not None else ""
        )
