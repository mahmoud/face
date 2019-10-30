
import pytest

from face import (Command,
                  Parser,
                  PosArgSpec,
                  ArgumentParseError)


def get_subcmd_cmd():
    subcmd = Command(None, name='subcmd', doc='the subcmd help')
    subcmd.add(_subsubcmd, name='subsubcmd', posargs={'count': 2, 'name': 'posarg_item'})
    cmd = Command(None, 'halp', doc='halp help')
    cmd.add(subcmd)

    return cmd


def _subsubcmd():
    "the subsubcmd help"
    pass


@pytest.fixture
def subcmd_cmd():
    return get_subcmd_cmd()


@pytest.mark.parametrize(
    "argv, contains, exit_code",
    [(['halp', '-h'], ['Usage', 'halp help', 'subcmd'], 0),  # basic, explicit help
     (['halp', '--help'], ['Usage', 'halp help', 'subcmd'], 0),
     # explicit help on subcommands
     (['halp', 'subcmd', '-h'], ['Usage', 'the subcmd help', 'subsubcmd'], 0),
     (['halp', 'subcmd', 'subsubcmd', '-h'], ['Usage', 'the subsubcmd help', 'posarg_item'], 0),
     # invalid subcommands
     # TODO: the following should also include "nonexistent-subcmd" but instead it lists "nonexistent_subcmd"
     (['halp', 'nonexistent-subcmd'], ['error', 'subcmd'], 1),
     (['halp', 'subcmd', 'nonexistent-subsubcmd'], ['error', 'subsubcmd'], 1)
     ]
)
def test_help(subcmd_cmd, argv, contains, exit_code, capsys):
    if isinstance(contains, str):
        contains = [contains]

    try:
        subcmd_cmd.run(argv)
    except SystemExit as se:
        if exit_code is not None:
            assert se.code == exit_code

    out, err = capsys.readouterr()
    if exit_code == 0:
        output = out
    else:
        output = err

    for cont in contains:
        assert cont in output

    return



# TODO: need to have commands reload their own subcommands if
# we're going to allow adding subcommands to subcommands after
# initial addition to the parent command
