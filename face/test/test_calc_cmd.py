
import pytest

from face import (Command,
                  Parser,
                  PosArgSpec,
                  ArgumentParseError)


def get_vcs_cmd(as_parser=False):
    cmd = Command(None, 'calc')

    cmd.add(_add_cmd, name='add', posargs={'min_count': 2, 'parse_as': float})
    cmd.add(_add_cmd, name='add_two_ints', posargs={'count': 2, 'parse_as': int})

    if as_parser:
        cmd.__class__ = Parser

    return cmd


def _add_cmd(posargs_):
    "add files to the vcs"
    assert sum(posargs_)
    return


def test_calc_basic():
    prs = get_vcs_cmd(as_parser=True)

    res = prs.parse(['calc', 'add', '1.1', '2.2'])
    assert res

    with pytest.raises(ArgumentParseError):
        prs.parse(['calc', 'add-two-ints', 'not', 'numbers'])
    with pytest.raises(ArgumentParseError):
        prs.parse(['calc', 'add-two-ints', '1', '2', '3'])
    with pytest.raises(ArgumentParseError):
        prs.parse(['calc', 'add-two-ints', '1'])
