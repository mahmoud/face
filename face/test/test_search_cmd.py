
import datetime

from pytest import raises

from face import Command, Parser, ListParam, ArgumentParseError, face_middleware


def _rg(glob, max_count):
    "Great stuff from the regrep"
    print('regrepping', glob, max_count)
    return


@face_middleware(provides=['timestamp'])
def _timestamp_mw(next_, glob):
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

    cmd.add(rg_subcmd)

    cmd.add(_timestamp_mw)

    if as_parser:
        cmd.__class__ = Parser

    return cmd


def test_search_prs_basic():
    prs = get_search_command(as_parser=True)

    res = prs.parse(['search', '--verbose'])

    assert res.name == 'search'
    assert res.flags['verbose'] is True

    res = prs.parse(['search', 'rg', '--glob', '*.py', '-g', '*.md', '--max-count', '5'])
    assert res.subcmds == ('rg',)
    assert res.flags['glob'] == ['*.py', '*.md']


def test_search_cmd_basic(capsys):
    cmd = get_search_command()

    cmd.run(['search', 'rg', '--glob', '*', '-m', '10'])

    out, err = capsys.readouterr()
    assert 'regrepping' in out

    with raises(SystemExit):
        cmd.run(['search', 'rg', 'badposarg'])
    out, err = capsys.readouterr()
    assert 'error:' in err

    with raises(SystemExit):
        cmd.run(['search', 'rg', '-h', 'badposarg'])
    out, err = capsys.readouterr()
    assert '[FLAGS]' in out


def test_search_parse_errors():
    cmd = get_search_command(as_parser=True)
    with raises(ArgumentParseError):
        cmd.parse(['splorch', 'splarch'])


def test_search_help(capsys):
    # pdb won't work in here bc of the captured stdout/err
    cmd = get_search_command()

    with raises(SystemExit):
        cmd.run(['search', '-h'])

    out, err = capsys.readouterr()
    assert '[FLAGS]' in out
    assert '--help' in out
    assert 'show this help message and exit' in out
