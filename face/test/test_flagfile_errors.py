import shlex

import pytest

from face import ArgumentParseError, Command, CommandLineError, Flag


@pytest.mark.parametrize('value', ['"unfinished', "'unfinished", 'unfinished\\'])
def test_flagfile_quoting_error_has_location(tmp_path, value):
    path = tmp_path / 'broken.flags'
    path.write_text('# comment\n--message ' + value + '\n', encoding='utf-8')
    cmd = Command(lambda message: message, name='cmd', flags=[Flag('--message')])

    with pytest.raises(ArgumentParseError) as caught:
        cmd.parse(['cmd', '--flagfile', str(path)])

    assert str(path) in str(caught.value)
    assert 'on line 2' in str(caught.value)
    assert caught.value.prs_res.name == 'cmd'


def test_nested_flagfile_quoting_error_has_both_locations(tmp_path):
    inner = tmp_path / 'inner.flags'
    inner.write_text('--message "unfinished\n', encoding='utf-8')
    outer = tmp_path / 'outer.flags'
    outer.write_text('# comment\n--flagfile ' + shlex.quote(str(inner)) + '\n', encoding='utf-8')
    cmd = Command(lambda message: message, name='cmd', flags=[Flag('--message')])

    with pytest.raises(ArgumentParseError) as caught:
        cmd.parse(['cmd', '--flagfile', str(outer)])

    assert 'on line 1 of flagfile "%s"' % inner in str(caught.value)
    assert 'on line 2 of flagfile "%s"' % outer in str(caught.value)


def test_flagfile_quoting_error_uses_command_line_error(tmp_path, capsys):
    path = tmp_path / 'broken.flags'
    path.write_text('--message "unfinished\n', encoding='utf-8')
    cmd = Command(lambda message: message, name='cmd', flags=[Flag('--message')])

    with pytest.raises(CommandLineError):
        cmd.run(['cmd', '--flagfile', str(path)])

    assert 'No closing quotation' in capsys.readouterr().err


def test_quoted_flagfile_value_still_parses(tmp_path):
    path = tmp_path / 'valid.flags'
    path.write_text('--message "hello # world" # comment\n', encoding='utf-8')
    cmd = Command(lambda message: message, name='cmd', flags=[Flag('--message')])
    assert cmd.run(['cmd', '--flagfile', str(path)]) == 'hello # world'
