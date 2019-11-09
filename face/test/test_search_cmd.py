
import os
import datetime

from pytest import raises

from face import (Command,
                  Parser,
                  ListParam,
                  face_middleware,
                  ArgumentParseError,
                  InvalidFlagArgument,
                  DuplicateFlag,
                  InvalidSubcommand,
                  UnknownFlag,
                  ChoicesParam)

CUR_PATH = os.path.dirname(os.path.abspath(__file__))


def _rg(glob, max_count):
    "Great stuff from the regrep"
    print('regrepping', glob, max_count)
    return


def _ls(file_paths):
    print(file_paths)
    return file_paths


@face_middleware(provides=['timestamp'])
def _timestamp_mw(next_):
    return next_(timestamp=datetime.datetime.now())


def get_search_command(as_parser=False):
    """A command which provides various subcommands mimicking popular
    command-line text search tools to test power, compatiblity, and
    flexibility.

    """
    cmd = Command(None, 'search')
    cmd.add('--verbose', char='-V', parse_as=True)

    rg_subcmd = Command(_rg, 'rg')
    rg_subcmd.add('--glob', char='-g', multi=True, parse_as=str,
                   doc='Include or exclude files/directories for searching'
                   ' that match the given glob. Precede with ! to exclude.')
    rg_subcmd.add('--max-count', char='-m', parse_as=int,
                  doc='Limit the number of matching lines per file.')
    rg_subcmd.add('--filetype', ChoicesParam(['py', 'js', 'html']))
    rg_subcmd.add('--extensions', ListParam(strip=True))
    rg_subcmd.add('--strategy', multi='override', missing='fast')

    cmd.add(rg_subcmd)

    ls_subcmd = Command(_ls, 'ls', posargs={'display': 'file_path', 'provides': 'file_paths'})
    cmd.add(ls_subcmd)

    cmd.add(_timestamp_mw)

    if as_parser:
        cmd.__class__ = Parser

    return cmd


def test_search_prs_basic():
    prs = get_search_command(as_parser=True)
    assert repr(prs).startswith('<Parser')

    res = prs.parse(['search', '--verbose'])
    assert repr(res).startswith('<CommandParseResult')
    assert res.name == 'search'
    assert res.flags['verbose'] is True

    assert prs.parse(['/search_pkg/__main__.py']).to_cmd_scope()['cmd_'] == 'python -m search_pkg'


    res = prs.parse(['search', 'rg', '--glob', '*.py', '-g', '*.md', '--max-count', '5'])
    assert res.subcmds == ('rg',)
    assert res.flags['glob'] == ['*.py', '*.md']

    res = prs.parse(['search', 'rg', '--extensions', 'py,html,css'])
    assert res.flags['extensions'] == ['py', 'html', 'css']

    res = prs.parse(['search', 'rg', '--strategy', 'fast', '--strategy', 'slow'])
    assert res.flags['strategy'] == 'slow'


def test_search_prs_errors():
    prs = get_search_command(as_parser=True)

    with raises(UnknownFlag):
        prs.parse(['search', 'rg', '--unknown-flag'])

    with raises(InvalidFlagArgument):
        prs.parse(['search', 'rg', '--max-count', 'not-an-int'])

    with raises(InvalidFlagArgument):
        prs.parse(['search', 'rg', '--max-count', '--glob', '*'])  # max-count should have an arg but doesn't

    with raises(InvalidFlagArgument):
        prs.parse(['search', 'rg', '--max-count'])  # gets a slightly different error message than above

    with raises(DuplicateFlag):
        prs.parse(['search', 'rg', '--max-count', '4', '--max-count', '5'])

    with raises(InvalidSubcommand):
        prs.parse(['search', 'nonexistent-subcommand'])

    with raises(ArgumentParseError):
        prs.parse(['search', 'rg', '--filetype', 'c'])

    return


def test_search_flagfile():
    prs = get_search_command(as_parser=True)

    with raises(ArgumentParseError):
        prs.parse(['search', 'rg', '--flagfile', '_nonexistent_flagfile'])

    flagfile_path = CUR_PATH + '/_search_cmd_a.flags'

    res = prs.parse(['search', 'rg', '--flagfile', flagfile_path])



def test_search_cmd_basic(capsys):
    cmd = get_search_command()

    cmd.run(['search', 'rg', '--glob', '*', '-m', '10'])

    out, err = capsys.readouterr()
    assert 'regrepping' in out

    with raises(SystemExit):
        cmd.run(['search', 'rg', 'badposarg'])
    out, err = capsys.readouterr()
    assert 'error:' in err

    cmd.run(['search', 'rg', '-h', 'badposarg'])
    out, err = capsys.readouterr()
    assert '[FLAGS]' in out  # help printed bc flag


def test_search_parse_errors():
    cmd = get_search_command(as_parser=True)
    with raises(ArgumentParseError):
        cmd.parse(['splorch', 'splarch'])


def test_search_help(capsys):
    # pdb won't work in here bc of the captured stdout/err
    cmd = get_search_command()

    cmd.run(['search', '-h'])

    out, err = capsys.readouterr()
    assert '[FLAGS]' in out
    assert '--help' in out
    assert 'show this help message and exit' in out


def test_search_ls(capsys):
    cmd = get_search_command()

    res = cmd.run(['search', 'ls', 'a', 'b'])

    assert res == ('a', 'b')

    cmd.run(['search', 'ls', '-h'])

    out, err = capsys.readouterr()
    assert 'file_paths' in out
