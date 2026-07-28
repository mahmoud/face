from collections.abc import Callable, Hashable, Iterable, Mapping
from typing import Protocol, TypeVar, overload

import face as face

_T = TypeVar("_T")

class _Parser(Protocol):
    @property
    def subprs_map(self) -> Mapping[tuple[str, ...], object]: ...

class _FlagDisplay(Protocol):
    @property
    def hidden(self) -> bool: ...
    @property
    def label(self) -> str | None: ...
    @property
    def value_name(self) -> str: ...

class _Flag(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def char(self) -> str | None: ...
    @property
    def parse_as(self) -> object: ...
    @property
    def display(self) -> _FlagDisplay: ...

class _PosArgSpec(Protocol):
    @property
    def parse_as(self) -> object: ...

class _CommandParseResult(Protocol):
    parser: _Parser
    argv: tuple[str, ...]
    name: str | None
    subcmds: tuple[str, ...] | None
    flags: Mapping[str, object] | None
    posargs: Iterable[object] | None
    post_posargs: Iterable[object] | None
    def to_cmd_scope(self) -> dict[str, object]: ...

@overload
def unique(src: Iterable[_T], key: None = None) -> list[_T]: ...
@overload
def unique(
    src: Iterable[_T], key: Callable[[_T], Hashable] | str
) -> list[_T]: ...

class FaceException(Exception): ...

class ArgumentParseError(FaceException):
    prs_res: _CommandParseResult

class ArgumentArityError(ArgumentParseError): ...

class InvalidSubcommand(ArgumentParseError):
    @classmethod
    def from_parse(cls, prs: _Parser, subcmd_name: str) -> InvalidSubcommand: ...

class UnknownFlag(ArgumentParseError):
    @classmethod
    def from_parse(
        cls, cmd_flag_map: Mapping[str, _Flag], flag_name: str
    ) -> UnknownFlag: ...

class InvalidFlagArgument(ArgumentParseError):
    @classmethod
    def from_parse(
        cls,
        cmd_flag_map: object,
        flag: _Flag,
        arg: str | None,
        exc: Exception | None = None,
    ) -> InvalidFlagArgument: ...

class InvalidPositionalArgument(ArgumentParseError):
    @classmethod
    def from_parse(
        cls, posargspec: _PosArgSpec, arg: str, exc: Exception
    ) -> InvalidPositionalArgument: ...

class MissingRequiredFlags(ArgumentParseError):
    @classmethod
    def from_parse(
        cls,
        cmd_flag_map: Mapping[str, _Flag],
        parsed_flag_map: object,
        missing_flag_names: Iterable[str],
    ) -> MissingRequiredFlags: ...

class DuplicateFlag(ArgumentParseError):
    @classmethod
    def from_parse(
        cls, flag: _Flag, arg_val_list: Iterable[object]
    ) -> DuplicateFlag: ...

class CommandLineError(FaceException, SystemExit):
    code: int
    def __init__(self, msg: str, code: int = 1) -> None: ...

class UsageError(CommandLineError):
    def format_message(self) -> str: ...
