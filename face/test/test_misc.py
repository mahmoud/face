
from face import Flag


def test_flag():
    f1 = Flag('--verbose', parse_as=True)
    f2 = Flag('--verbosity', parse_as=int)

    assert f1 != f2

    f3 = Flag('--verbose', parse_as=True)
    assert f1 == f3
