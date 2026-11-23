import pytest

from face import Command, Flag, face_middleware


@pytest.mark.parametrize('defaulted', [False, True])
def test_keyword_only_handler_flag(defaulted):
    def required(*, value):
        return value

    def optional(*, value='fallback'):
        return value

    cmd = Command(optional if defaulted else required)
    cmd.add('--value')
    assert cmd.run(['demo', '--value', 'provided']) == 'provided'


def test_keyword_only_handler_builtin():
    def handler(*, cmd_):
        return cmd_

    assert Command(handler).run(['demo']) == 'demo'


def test_keyword_only_middleware_flag():
    @face_middleware(flags=[Flag('--value')])
    def capture(next_, *, value):
        return value, next_()

    def handler():
        return 'handled'

    assert Command(handler, middlewares=[capture]).run(
        ['demo', '--value', 'provided']) == ('provided', 'handled')


def test_keyword_only_provided_value():
    @face_middleware(provides=['value'])
    def provide(next_):
        return next_(value='provided')

    def handler(*, value):
        return value

    assert Command(handler, middlewares=[provide]).run(['demo']) == 'provided'


def test_keyword_only_intermediate_middleware():
    @face_middleware(provides=['value'])
    def provide(next_):
        return next_(value='provided')

    @face_middleware(provides=['result'])
    def transform(next_, *, value):
        return next_(result=value.upper())

    def handler(*, result):
        return result

    # add_middleware prepends, so install inner before outer.
    cmd = Command(handler, middlewares=[transform, provide])
    assert cmd.run(['demo']) == 'PROVIDED'


def test_ordinary_arguments_still_work():
    def handler(value):
        return value

    cmd = Command(handler)
    cmd.add('--value')
    assert cmd.run(['demo', '--value', 'provided']) == 'provided'


def test_missing_keyword_only_dependency_still_fails_preparation():
    def handler(*, unavailable):
        return unavailable

    with pytest.raises(NameError, match='unavailable'):
        Command(handler).prepare()


def test_unprovided_optional_keyword_only_value_keeps_default():
    def handler(*, value='fallback'):
        return value

    assert Command(handler).run(['demo']) == 'fallback'


def test_keyword_only_callable_instance():
    class Handler:
        def __call__(self, *, value):
            return value

    cmd = Command(Handler())
    cmd.add('--value')
    assert cmd.run(['demo', '--value', 'provided']) == 'provided'


def test_keyword_only_bound_method():
    class Handler:
        def handle(self, *, value):
            return value

    cmd = Command(Handler().handle)
    cmd.add('--value')
    assert cmd.run(['demo', '--value', 'provided']) == 'provided'
