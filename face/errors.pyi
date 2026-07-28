from collections.abc import Callable, Iterable
from typing import TypeVar, overload

import face as face

_T = TypeVar("_T")

@overload
def unique(src: Iterable[_T], key: None = None) -> list[_T]: ...
@overload
def unique(src: Iterable[_T], key: Callable[[_T], object]) -> list[_T]: ...

class FaceException(Exception): ...

class ArgumentParseError(FaceException):
    prs_res: object

class ArgumentArityError(ArgumentParseError): ...

class InvalidSubcommand(ArgumentParseError):
    @classmethod
    def from_parse(cls, prs: object, subcmd_name: str) -> InvalidSubcommand: ...

class UnknownFlag(ArgumentParseError):
    @classmethod
    def from_parse(
        cls, cmd_flag_map: object, flag_name: str
    ) -> UnknownFlag: ...

class InvalidFlagArgument(ArgumentParseError):
    @classmethod
    def from_parse(
        cls,
        cmd_flag_map: object,
        flag: object,
        arg: str | None,
        exc: Exception | None = None,
    ) -> InvalidFlagArgument: ...

class InvalidPositionalArgument(ArgumentParseError):
    @classmethod
    def from_parse(
        cls, posargspec: object, arg: str, exc: Exception
    ) -> InvalidPositionalArgument: ...

class MissingRequiredFlags(ArgumentParseError):
    @classmethod
    def from_parse(
        cls,
        cmd_flag_map: object,
        parsed_flag_map: object,
        missing_flag_names: Iterable[str],
    ) -> MissingRequiredFlags: ...

class DuplicateFlag(ArgumentParseError):
    @classmethod
    def from_parse(
        cls, flag: object, arg_val_list: Iterable[object]
    ) -> DuplicateFlag: ...

class CommandLineError(FaceException, SystemExit):
    code: int
    def __init__(self, msg: str, code: int = 1) -> None: ...

class UsageError(CommandLineError):
    def format_message(self) -> str: ...
