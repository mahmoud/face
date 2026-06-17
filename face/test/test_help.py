import pytest

from face import (Flag,
                  ERROR,
                  Command,
                  CommandGroup,
                  CommandChecker,
                  Parser,
                  PosArgSpec,
                  HelpHandler,
                  ArgumentParseError,
                  StoutHelpFormatter)
from face.utils import format_flag_post_doc


def get_subcmd_cmd():
    subcmd = Command(None, name='subcmd', doc='the subcmd help')
    subcmd.add(_subsubcmd, name='subsubcmd', posargs={'count': 2, 'name': 'posarg_item'})
    cmd = Command(None, 'halp', doc='halp help')
    cmd.add(subcmd)

    return cmd


def _subsubcmd():
    """the subsubcmd help

    another line
    """
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
     (['halp', 'subcmd', 'nonexistent-subsubcmd'], ['error', 'subsubcmd'], 1),
     # subcommand group invoked without specifying a subcommand
     (['halp'], ['error', 'expected a subcommand'], 1),
     (['halp', 'subcmd'], ['error', 'expected a subcommand'], 1),
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


def test_help_subcmd():
    hhandler = HelpHandler(flag=False, subcmd='help')
    cmd = Command(None, 'cmd', help=hhandler)

    try:
        cmd.run(['cmd', 'help'])
    except SystemExit as se:
        assert se.code == 0

    with pytest.raises(ValueError, match='requires a handler function or help handler'):
        Command(None, help=None)


def test_err_subcmd_prog_name():
    cmd = Command(lambda: print("foo"), "foo")
    subcmd = Command(lambda: print("bar"), "bar")
    subcmd.add(Command(lambda: print("baz"), "baz"))
    cmd.add(subcmd)

    cc = CommandChecker(cmd)
    res = cc.fail('fred.py bar ba')
    assert 'fred.py' in res.stderr
    assert 'foo' not in res.stderr


def test_stout_help():
    with pytest.raises(TypeError, match='unexpected formatter arguments'):
        StoutHelpFormatter(bad_kwarg=True)

    return


def test_handler():
    with pytest.raises(TypeError, match='expected help handler func to be callable'):
        HelpHandler(func=object())

    with pytest.raises(TypeError, match='expected Formatter type or instance'):
        HelpHandler(formatter=None)

    with pytest.raises(TypeError, match='only accepts extra formatter'):
        HelpHandler(usage_label='Fun: ', formatter=StoutHelpFormatter())

    with pytest.raises(TypeError, match='expected valid formatter'):
        HelpHandler(formatter=object())



# TODO: need to have commands reload their own subcommands if
# we're going to allow adding subcommands to subcommands after
# initial addition to the parent command


def test_flag_post_doc():
    assert format_flag_post_doc(Flag('flag')) == ''
    assert format_flag_post_doc(Flag('flag', missing=42)) == '(defaults to 42)'
    assert format_flag_post_doc(Flag('flag', missing=ERROR)) == '(required)'
    assert format_flag_post_doc(Flag('flag', display={'post_doc': '(fun)'})) == '(fun)'



def test_missing_subcmd_shows_help_and_errors(subcmd_cmd, capsys):
    """When a subcommand group is invoked without a subcommand,
    help is shown to stdout AND an error is printed to stderr."""
    with pytest.raises(SystemExit) as exc_info:
        subcmd_cmd.run(['halp', 'subcmd'])

    assert exc_info.value.code == 1

    out, err = capsys.readouterr()
    # Help text goes to stdout
    assert 'Usage' in out
    assert 'subsubcmd' in out
    # Error goes to stderr
    assert 'expected a subcommand' in err


def test_missing_subcmd_checker():
    cmd = get_subcmd_cmd()
    cc = CommandChecker(cmd)

    # Subcommand group without subcommand -> exit 1
    res = cc.fail('halp subcmd')
    assert 'Usage' in res.stdout
    assert 'expected a subcommand' in res.stderr

    # Explicit help -> exit 0
    res = cc.run('halp subcmd -h')
    assert 'Usage' in res.stdout


def test_subcmd_group_named():
    cmd = Command(None, name='app')
    setup = CommandGroup('Setup')
    setup.add(lambda: None, name='create', doc='create a thing')
    setup.add(lambda: None, name='delete', doc='delete a thing')
    cmd.add(setup)
    info = CommandGroup('Info')
    info.add(lambda: None, name='list', doc='list things')
    cmd.add(info)

    cc = CommandChecker(cmd)
    res = cc.run('app -h')
    assert 'Setup:' in res.stdout
    assert 'Info:' in res.stdout
    assert 'create' in res.stdout
    assert 'delete' in res.stdout
    assert 'list' in res.stdout


def test_subcmd_group_ungrouped_first():
    cmd = Command(None, name='app')
    cmd.add(lambda: None, name='version', doc='show version')
    grp = CommandGroup('Ops')
    grp.add(lambda: None, name='deploy', doc='deploy it')
    cmd.add(grp)

    cc = CommandChecker(cmd)
    res = cc.run('app -h')
    # version appears before 'Ops:' heading
    vi = res.stdout.index('version')
    oi = res.stdout.index('Ops:')
    assert vi < oi


def test_subcmd_group_backward_compat():
    """Command with no groups produces same flat help output."""
    cmd = Command(None, name='app')
    cmd.add(lambda: None, name='alpha', doc='do alpha')
    cmd.add(lambda: None, name='beta', doc='do beta')

    cc = CommandChecker(cmd)
    res = cc.run('app -h')
    lines = res.stdout.splitlines()
    # No group headings anywhere
    assert not any(line.strip().endswith(':') and line.strip() != 'Subcommands:'
                   and line.strip() != 'Flags:' for line in lines)
    # Subcommands at normal indent, not double-indented
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('alpha') or stripped.startswith('beta'):
            indent = len(line) - len(stripped)
            assert indent == 2  # section_indent is '  '


def test_subcmd_group_kwarg():
    cmd = Command(None, name='app')
    cmd.add(lambda: None, name='foo', doc='do foo', group='Stuff')
    cmd.add(lambda: None, name='bar', doc='do bar', group='Stuff')

    cc = CommandChecker(cmd)
    res = cc.run('app -h')
    assert 'Stuff:' in res.stdout
    assert 'foo' in res.stdout
    assert 'bar' in res.stdout


def test_subcmd_group_dispatch():
    result = []
    cmd = Command(None, name='app')
    grp = CommandGroup('Ops')
    grp.add(lambda: result.append('ran'), name='do_it')
    cmd.add(grp)

    cmd.run(['app', 'do-it'])
    assert result == ['ran']


def test_command_group_constructor():
    with pytest.raises(ValueError):
        CommandGroup('')
    with pytest.raises(ValueError):
        CommandGroup(None)
    grp = CommandGroup('Valid')
    assert grp.name == 'Valid'
    assert grp._commands == []


def test_command_group_add_prebuilt():
    grp = CommandGroup('Ops')
    subcmd = Command(lambda: None, name='deploy', doc='deploy it')
    ret = grp.add(subcmd)
    assert ret is subcmd
    assert grp._commands == [subcmd]


def test_command_group_add_invalid():
    grp = CommandGroup('Ops')
    with pytest.raises(TypeError, match='expected callable or Command'):
        grp.add(42)


def test_command_group_repr():
    grp = CommandGroup('Ops')
    assert repr(grp) == "CommandGroup('Ops', commands=0)"
    grp.add(lambda: None, name='x')
    assert repr(grp) == "CommandGroup('Ops', commands=1)"


def test_add_command_group_invalid():
    cmd = Command(None, name='app')
    with pytest.raises(TypeError, match='expected CommandGroup instance'):
        cmd.add_command_group('not a group')