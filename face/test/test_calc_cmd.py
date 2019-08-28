
import pytest

from face import (Command,
                  Parser,
                  PosArgSpec,
                  ArgumentParseError)


def get_calc_cmd(as_parser=False):
    cmd = Command(None, 'calc')

    cmd.add(_add_cmd, name='add', posargs={'min_count': 2, 'parse_as': float})
    cmd.add(_add_two_ints, name='add_two_ints', posargs={'count': 2, 'parse_as': int, 'provides': 'ints'})
    cmd.add(_is_odd, name='is_odd', posargs={'count': 1, 'parse_as': int, 'provides': 'target_int'})

    if as_parser:
        cmd.__class__ = Parser

    return cmd


def _add_cmd(posargs_):
    "add numbers together"
    assert posargs_
    return sum(posargs_)


def _add_two_ints(ints):
    assert ints
    return sum(ints)


def _is_odd(target_int):
    return bool(target_int % 2)


def test_calc_basic():
    prs = cmd = get_calc_cmd()

    res = prs.parse(['calc', 'add', '1.1', '2.2'])
    assert res

    with pytest.raises(ArgumentParseError):
        prs.parse(['calc', 'add-two-ints', 'not', 'numbers'])
    with pytest.raises(ArgumentParseError):
        prs.parse(['calc', 'add-two-ints', '1', '2', '3'])
    with pytest.raises(ArgumentParseError):
        prs.parse(['calc', 'add-two-ints', '1'])

    res = cmd.run(['calc', 'add-two-ints', '1', '2'])
    assert res == 3

    with pytest.raises(TypeError):
        prs.parse(['calc', 'is-odd', 3])  # fails bc 3 isn't a str

    res = cmd.run(['calc', 'is-odd', '3'])
    assert res == True
    res = cmd.run(['calc', 'is-odd', '4'])
    assert res == False
