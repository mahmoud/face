from enum import Enum

import pytest

from face import ChoicesParam, Flag, Parser


class Color(Enum):
    RED = 'red'
    BLUE = 'blue'


@pytest.mark.parametrize('make_choices', [list, tuple, iter])
def test_unordered_choices_keep_all_values(make_choices):
    choices = ChoicesParam(make_choices([Color.RED, Color.BLUE]))
    assert choices.parse('red') is Color.RED
    assert choices.parse('blue') is Color.BLUE
    with pytest.raises(ValueError):
        choices.parse('green')


def test_choices_generator_with_explicit_parser():
    choices = ChoicesParam((value for value in [1, 'auto']), parse_as=str)
    parser = Parser('example', flags=[Flag('--mode', parse_as=choices)])
    assert parser.parse(['example', '--mode', 'auto']).flags['mode'] == 'auto'


@pytest.mark.parametrize('choices', [[], (), iter(())])
def test_empty_choices_are_rejected(choices):
    with pytest.raises(ValueError, match='expected at least one choice'):
        ChoicesParam(choices)


def test_sortable_choices_generator():
    choices = ChoicesParam(value for value in [3, 1, 2])
    assert choices.choices == [1, 2, 3]
    assert choices.parse('2') == 2
