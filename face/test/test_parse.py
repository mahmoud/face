
from face import Command, Parser, ListParam, ArgumentParseError


def get_search_command(as_parser=False):
    """A command which provides various subcommands mimicking popular
    command-line text search tools to test power, compatiblity, and
    flexibility.

    """
    cmd = Command(None, 'search')
    cmd.add('--verbose', char='-V', parse_as=True)

    rg_subcmd = Command(None, 'rg')
    rg_subcmd.add('--glob', char='-g', multi=True, parse_as=str,
                   doc='Include or exclude files/directories for searching'
                   ' that match the given glob. Precede with ! to exclude.')
    rg_subcmd.add('--max-count', char='-m', parse_as=int,
                  doc='Limit the number of matching lines per file.')

    cmd.add(rg_subcmd)

    if as_parser:
        cmd.__class__ = Parser

    return cmd


def test_search_cmd_basic():
    prs = get_search_command(as_parser=True)

    res = prs.parse(['search', '--verbose'])

    assert res.name == 'search'
    assert res.flags['verbose'] is True

    res = prs.parse(['search', 'rg', '--glob', '*.py', '-g', '*.md', '--max-count', '5'])
    assert res.subcmds == ('rg',)
    assert res.flags['glob'] == ['*.py', '*.md']


def test_search_parse_errors():
    from pytest import raises
    cmd = get_search_command(as_parser=True)
    with raises(ArgumentParseError):
        cmd.parse(['splorch', 'splarch'])


def test_search_help():
    cmd = get_search_command()
