import contextlib as contextlib
import getpass as getpass
import io as io
import os as os
import shlex as shlex
import sys as sys
from collections.abc import Callable, Container as Container, Mapping, Sequence
from functools import partial as partial
from subprocess import list2cmdline as list2cmdline
from types import TracebackType
from typing import Protocol

from boltons.setutils import complement as complement

class _RunnableCommand(Protocol):
    def run(self, argv: Sequence[str]) -> object: ...

class RunResult:
    args: Sequence[str]
    input: str | None
    checker: CommandChecker | None
    stdout_bytes: bytes
    stderr_bytes: bytes | None
    exit_code: object
    exc_info: tuple[type[BaseException], BaseException, TracebackType] | None
    def __init__(
        self,
        args: Sequence[str],
        input: str | None,
        exit_code: object,
        stdout_bytes: bytes,
        stderr_bytes: bytes | None,
        exc_info: tuple[type[BaseException], BaseException, TracebackType] | None = None,
        checker: CommandChecker | None = None,
    ) -> None: ...
    @property
    def exception(self) -> BaseException | None: ...
    @property
    def returncode(self) -> object: ...
    @property
    def stdout(self) -> str: ...
    @property
    def stderr(self) -> str: ...

class CheckError(AssertionError):
    result: RunResult
    def __init__(self, result: RunResult, exit_codes: Container[int]) -> None: ...

class CommandChecker:
    cmd: _RunnableCommand
    base_env: dict[str, str | None]
    reraise: bool
    mix_stderr: bool
    encoding: str
    chdir: str | os.PathLike[str] | None
    def __init__(
        self,
        cmd: _RunnableCommand,
        env: Mapping[str, str | None] | None = None,
        chdir: str | os.PathLike[str] | None = None,
        mix_stderr: bool = False,
        reraise: bool = False,
    ) -> None: ...
    def fail(
        self,
        args: str | Sequence[str],
        input: str | bytes | Sequence[str] | None = None,
        env: Mapping[str, str | None] | None = None,
        chdir: str | os.PathLike[str] | None = None,
        exit_code: int | Container[int] | None = ...,
    ) -> RunResult: ...
    def __getattr__(self, name: str) -> Callable[..., RunResult]: ...
    def run(
        self,
        args: str | Sequence[str],
        input: str | bytes | Sequence[str] | None = None,
        env: Mapping[str, str | None] | None = None,
        chdir: str | os.PathLike[str] | None = None,
        exit_code: int | Container[int] | None = 0,
    ) -> RunResult: ...
