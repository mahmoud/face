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


@pytest.mark.parametrize('depth', [0, 1, 2])
@pytest.mark.parametrize('posargs,post_posargs,head,tail,expected', [
    (False, {'count': 1}, [], ['7'], 7),
    (False, {'count': 2}, [], ['7', '11'], (7, 11)),
    ({'count': 1}, {'max_count': None}, ['head'], ['7', '11'], (7, 11)),
    ({'max_count': None}, {'count': 1}, ['head', 'other'], ['7'], 7),
])
def test_typed_post_posargs_keep_their_shape_through_nested_commands(
        depth, posargs, post_posargs, head, tail, expected):
    command = Command(lambda values: values, name='leaf', posargs=posargs,
                      post_posargs=dict(post_posargs, parse_as=int, provides='values'))
    argv = ['leaf'] + head + ['--'] + tail
    for level in range(depth):
        root = Command(None, name='root' + str(level))
        root.add(command)
        command = root
        argv.insert(0, root.name)

    parsed = command.parse(argv)
    assert parsed.post_posargs == tuple(map(int, tail))
    assert parsed.to_cmd_scope()['values'] == expected
    assert command.run(argv) == expected
