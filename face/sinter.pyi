import hashlib as hashlib
import inspect as inspect
import linecache as linecache
import sys as sys
import types as types
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from typing import TypeVar

from boltons import iterutils as iterutils
from boltons.funcutils import FunctionBuilder as FunctionBuilder

_R = TypeVar("_R")

def camel2under(camel_string: str) -> str: ...
def get_fb(f: Callable[..., object], drop_self: bool = True) -> FunctionBuilder: ...
def get_arg_names(
    f: Callable[..., object], only_required: bool = False
) -> list[str]: ...
def inject(f: Callable[..., _R], injectables: Mapping[str, object]) -> _R: ...
def get_callable_labels(obj: Callable[..., object]) -> tuple[str, str, str]: ...
def chain_argspec(
    func_list: Iterable[Callable[..., object]],
    provides: Iterable[Collection[str]],
    inner_name: str,
) -> tuple[set[str], set[str]]: ...
def build_chain_str(
    funcs: Sequence[Callable[..., object]],
    params: Sequence[Collection[str]],
    inner_name: str,
    params_sofar: set[str] | None = None,
    level: int = 0,
    func_aliaser: object | None = None,
    func_names: object | None = None,
) -> str: ...
def compile_chain(
    funcs: Sequence[Callable[..., object]],
    params: Sequence[Collection[str]],
    inner_name: str,
    verbose: bool = False,
) -> Callable[..., object]: ...
def compile_code(
    code_str: str,
    name: str,
    env: dict[str, object] | None = None,
    verbose: bool = False,
) -> object: ...
def make_chain(
    funcs: Iterable[Callable[..., object]],
    provides: Iterable[Collection[str]],
    final_func: Callable[..., _R],
    preprovided: Collection[str],
    inner_name: str,
) -> tuple[Callable[..., _R], set[str], set[str]]: ...
