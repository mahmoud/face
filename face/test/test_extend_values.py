import pytest

from face import ERROR, Flag, Parser
from face.errors import DuplicateFlag, MissingRequiredFlags


def parse_none(text):
    return None


@pytest.mark.parametrize('multi', ['extend', True])
@pytest.mark.parametrize('parse_as,missing,arguments,expected', [
    (int, 0, ['--value', '0'], [0]),
    (int, 0, ['--value', '0', '--value', '1', '--value', '0'], [0, 1, 0]),
    (parse_none, None, ['--value', 'item'], [None]),
    (parse_none, None, ['--value', 'first', '--value', 'second'], [None, None]),
    (True, True, ['--value', '--value'], [True, True]),
    (str, '', ['--value', ''], ['']),
])
def test_extend_preserves_supplied_values(multi, parse_as, missing, arguments, expected):
    parser = Parser('app', flagfile=False,
                    flags=[Flag('value', parse_as=parse_as, missing=missing, multi=multi)])

    assert parser.parse(['app'] + arguments).flags['value'] == expected


@pytest.mark.parametrize('multi', ['extend', True])
@pytest.mark.parametrize('missing', [None, 0, True, object()])
def test_absent_extend_ignores_default(multi, missing):
    parser = Parser('app', flagfile=False,
                    flags=[Flag('value', missing=missing, multi=multi)])

    assert parser.parse(['app']).flags['value'] == []


def test_extend_keeps_flag_and_value_order():
    parser = Parser('app', flagfile=False, flags=[
        Flag('empty', missing=0, multi='extend'),
        Flag('default', missing=False),
        Flag('first', char='f', parse_as=int, missing=0, multi=True),
        Flag('second', char='s', parse_as=int, missing=0, multi='extend'),
    ])
    result = parser.parse(['app', '-s', '2', '--first', '1',
                           '--second', '3', '-f', '4'])

    assert list(result.flags) == ['second', 'first', 'empty', 'default']
    assert result.flags['second'] == [2, 3]
    assert result.flags['first'] == [1, 4]
    assert result.flags['empty'] == []
    assert result.flags['default'] is False


@pytest.mark.parametrize('arguments,count', [
    ([], 1),
    (['--value', 'first', '--value', 'second'], 2),
])
def test_custom_multi_receives_defaults_and_supplied_values(arguments, count):
    marker = object()
    flag = Flag('value', parse_as=lambda text: marker, missing=marker,
                multi=lambda flag, values: tuple(values))
    parser = Parser('app', flagfile=False, flags=[flag])

    values = parser.parse(['app'] + arguments).flags['value']

    assert isinstance(values, tuple)
    assert len(values) == count
    assert all(value is marker for value in values)


@pytest.mark.parametrize('multi', ['error', False, 'override', 'overwrite'])
def test_other_multi_modes_keep_absent_default(multi):
    marker = object()
    parser = Parser('app', flagfile=False,
                    flags=[Flag('value', missing=marker, multi=multi)])

    assert parser.parse(['app']).flags['value'] is marker


def test_required_flags_checked_before_multi_callbacks():
    def unexpected_multi(flag, values):
        raise AssertionError('aggregation must wait for required flags')

    parser = Parser('app', flagfile=False, flags=[
        Flag('value', multi=unexpected_multi),
        Flag('required', missing=ERROR, multi='extend'),
    ])

    with pytest.raises(MissingRequiredFlags):
        parser.parse(['app', '--value', 'item'])


@pytest.mark.parametrize('multi', ['extend', True])
def test_required_extend_preserves_zero(multi):
    parser = Parser('app', flagfile=False,
                    flags=[Flag('value', parse_as=int, missing=ERROR, multi=multi)])

    assert parser.parse(['app', '--value', '0']).flags['value'] == [0]


@pytest.mark.parametrize('multi', ['error', False])
def test_error_modes_reject_duplicate_values(multi):
    parser = Parser('app', flagfile=False,
                    flags=[Flag('value', parse_as=int, missing=0, multi=multi)])

    with pytest.raises(DuplicateFlag):
        parser.parse(['app', '--value', '0', '--value', '0'])


@pytest.mark.parametrize('multi', ['override', 'overwrite'])
def test_override_modes_keep_last_zero(multi):
    parser = Parser('app', flagfile=False,
                    flags=[Flag('value', parse_as=int, missing=0, multi=multi)])

    assert parser.parse(['app', '--value', '1', '--value', '0']).flags['value'] == 0
