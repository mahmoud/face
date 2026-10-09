import subprocess
import sys
import textwrap

import pytest


@pytest.mark.parametrize('optimization', ['', '-O', '-OO'])
def test_terminal_size_with_optimization(optimization):
    script = textwrap.dedent("""\
        import sys
        import types
        from face.helpers import get_winsize, get_wrap_width

        def ioctl(stream, request, size):
            size[0], size[1] = 24, 100
            return 0

        sys.modules['fcntl'] = types.SimpleNamespace(ioctl=ioctl)
        sys.modules['termios'] = types.SimpleNamespace(TIOCGWINSZ=1)
        if get_winsize() != (24, 100):
            raise RuntimeError('terminal dimensions were not read')
        if get_wrap_width() != 98:
            raise RuntimeError('incorrect help wrapping width')
        """)
    args = [sys.executable] + ([optimization] if optimization else [])
    subprocess.run(args + ['-c', script], check=True, capture_output=True, text=True)
