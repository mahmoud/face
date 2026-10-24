import pytest

from face import Command


@pytest.mark.parametrize('subcommand', [False, True])
@pytest.mark.parametrize('posargs,post_posargs,argv,expected', [
    (False, {'max_count': 1}, ['--', 'tail'], 'tail'),
    ({'max_count': 1}, {'max_count': None}, ['head', '--', 'one', 'two'], ('one', 'two')),
    ({'max_count': None}, {'max_count': 1}, ['head', 'other', '--', 'tail'], 'tail'),
    ({'max_count': 1}, {'max_count': 1}, ['head', '--', 'tail'], 'tail'),
    ({'max_count': None}, {'max_count': None}, ['head', '--', 'one', 'two'], ('one', 'two')),
    (False, {'max_count': 1}, ['--'], None),
])
def test_post_posargs_use_their_own_cardinality(subcommand, posargs,
                                                post_posargs, argv, expected):
    command = Command(lambda tail: tail, name='child', posargs=posargs,
                      post_posargs=dict(post_posargs, provides='tail'))
    if subcommand:
        root = Command(None, name='root')
        root.add(command)
        argv = ['root', 'child'] + argv
    else:
        root = command
        argv = ['child'] + argv

    parsed = root.parse(argv)
    assert parsed.to_cmd_scope()['tail'] == expected
    assert root.run(argv) == expected
