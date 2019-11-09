
import pytest

from face import Command, Flag
from face.utils import format_flag_label, identifier_to_flag, get_minimal_executable

def test_cmd_name():

    def handler():
        return 0

    Command(handler, name='ok_cmd')

    name_err_map = {'': 'non-zero length string',
                    5: 'non-zero length string',
                    'name_': 'without trailing dashes or underscores',
                    'name--': 'without trailing dashes or underscores',
                    'n?me': ('valid subcommand name must begin with a letter, and'
                             ' consist only of letters, digits, underscores, and'
                             ' dashes')}

    for name, err in name_err_map.items():
        with pytest.raises(ValueError, match=err):
            Command(handler, name=name)

    return


def test_flag_name():
    flag = Flag('ok_name')
    assert format_flag_label(flag) == '--ok-name OK_NAME'
    assert format_flag_label(Flag('name', display={'label': '--nAmE'})) == '--nAmE'

    with pytest.raises(ValueError, match='expected identifier.*'):
        assert identifier_to_flag('--flag')

    name_err_map = {'': 'non-zero length string',
                    5: 'non-zero length string',
                    'name_': 'without trailing dashes or underscores',
                    'name--': 'without trailing dashes or underscores',
                    'n?me': ('must begin with a letter.*and'
                             ' consist only of letters, digits, underscores, and'
                             ' dashes'),
                    'for': 'valid flag names must not be Python keywords'}

    for name, err in name_err_map.items():
        with pytest.raises(ValueError, match=err):
            Flag(name=name)


def test_minimal_exe():
    venv_exe_path = '/home/mahmoud/virtualenvs/face/bin/python'
    res = get_minimal_executable(venv_exe_path,
                                 environ={'PATH': ('/home/mahmoud/virtualenvs/face/bin'
                                                   ':/home/mahmoud/bin:/usr/local/sbin'
                                                   ':/usr/local/bin:/usr/sbin'
                                                   ':/usr/bin:/sbin:/bin:/snap/bin')})
    assert res == 'python'

    res = get_minimal_executable(venv_exe_path,
                                 environ={'PATH': ('/home/mahmoud/bin:/usr/local/sbin'
                                                   ':/usr/local/bin:/usr/sbin'
                                                   ':/usr/bin:/sbin:/bin:/snap/bin')})
    assert res == venv_exe_path

    # TODO: where is PATH not a string?
    res = get_minimal_executable(venv_exe_path, environ={'PATH': []})
    assert res == venv_exe_path
