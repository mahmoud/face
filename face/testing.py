# Design (and some implementation) of this owes heavily to Click's
# CliRunner (TODO: bring in license?)

import os
import sys
import shlex
import contextlib

PY2 = sys.version_info[0] == 2

if PY2:
    from cStringIO import StringIO
else:
    import io


def make_input_stream(input, encoding):
    # Is already an input stream.
    if callable(getattr(input, 'read', None)):
        if PY2:
            return input
        # TODO
        #rv = _find_binary_reader(input)
        #if rv is not None:
        #    return rv
        raise TypeError('Could not find binary reader for input stream: %r' % (input,))

    if input is None:
        input = b''
    elif not isinstance(input, bytes):
        input = input.encode(encoding)
    if PY2:
        return StringIO(input)
    return io.BytesIO(input)


class Result(object):
    """Holds the captured result of an invoked CLI script."""

    def __init__(self, test_client, stdout_bytes, stderr_bytes, exit_code, exc_info):
        self.test_client = test_client
        self.stdout_bytes = stdout_bytes
        self.stderr_bytes = stderr_bytes
        self.exit_code = exit_code  # integer

        # if an exception occurred:
        self.exc_info = exc_info

    @property
    def exception(self):
        return self.exc_info[0] if self.exc_info else None

    @property
    def stdout(self):
        """The standard output as unicode string."""
        return self.stdout_bytes.decode(self.test_client.encoding, 'replace') \
            .replace('\r\n', '\n')

    @property
    def stderr(self):
        """The standard error as unicode string."""
        # TODO: differentiate between mixed stderr and blank stderr
        if not self.stderr_bytes:
            raise ValueError("stderr not separately captured")
        return self.stderr_bytes.decode(self.test_client.encoding, 'replace') \
            .replace('\r\n', '\n')


    def __repr__(self):
        return '<%s %s>' % (
            self.__class__.__name__,
            repr(self.exception) if self.exception else ('exit_code=%s' % self.exit_code),
        )


class TestClient(object):
    def __init__(self, cmd, env=None, echo_stdin=False, mix_stderr=False, reraise=True):
        self.cmd = cmd
        self.base_env = env or {}
        self.echo_stdin = echo_stdin
        self.reraise = reraise
        self.mix_stderr = mix_stderr
        self.encoding = 'utf8'  # not clear if this should be an arg yet

    def invoke(self, args, input=None, env=None, chdir=None):
        with self.isolate(input=input, env=env, chdir=chdir) as (stdout, stderr):
            exc_info = None
            exit_code = 0

            if isinstance(args, str):
                args = shlex.split(args)

            try:
                res = self.cmd.run(args or ())
            except SystemExit as se:
                exc_info = sys.exc_info()
                exit_code = se.code
                if exit_code is None:
                    exit_code = 0

                #if exit_code != 0:
                #    exception = e

                if not isinstance(exit_code, int):
                    sys.stdout.write(str(exit_code))
                    sys.stdout.write('\n')
                    exit_code = 1
            except Exception:
                if self.reraise:
                    raise
                exit_code = 1
                exc_info = sys.exc_info()
            finally:
                sys.stdout.flush()
                stdout = stdout.getvalue()
                stderr = stderr and stderr.getvalue()

            # TODO: unconsumed stdin?
            return Result(test_client=self,
                          stdout_bytes=stdout,
                          stderr_bytes=stderr,
                          exit_code=exit_code,
                          exc_info=exc_info)

    @contextlib.contextmanager
    def isolate(self, input=None, env=None, chdir=None):
        input_stream = make_input_stream(input, self.encoding)
        old_cwd = os.getcwd()
        old_stdin, old_stdout, old_stderr = sys.stdin, sys.stdout, sys.stderr

        full_env = dict(self.base_env)
        if env:
            full_env.update(env)

        if PY2:
            bytes_output = StringIO()
            input = input_stream
            if self.echo_stdin:
                input = _EchoingStdin(input_stream, bytes_output)
            sys.stdout = bytes_output  # TODO: move these assignments below
            if not self.mix_stderr:
                bytes_error = StringIO()
                sys.stderr = bytes_error
        else:
            bytes_output = io.BytesIO()
            if self.echo_stdin:
                input_stream = _EchoingStdin(input_stream, bytes_output)
            input = io.TextIOWrapper(input_stream, encoding=self.encoding)
            sys.stdout = io.TextIOWrapper(
                bytes_output, encoding=self.encoding)
            if not self.mix_stderr:
                bytes_error = io.BytesIO()
                sys.stderr = io.TextIOWrapper(
                    bytes_error, encoding=self.encoding)

        if self.mix_stderr:
            sys.stderr = sys.stdout
        sys.stdin = input

        old_env = {}
        try:
            if chdir:
                os.chdir(chdir)

            _sync_env(os.environ, full_env, old_env)

            yield (bytes_output, bytes_error if not self.mix_stderr else None)
        finally:
            if chdir:
                os.chdir(old_cwd)

            _sync_env(os.environ, old_env)

            sys.stdout = old_stdout
            sys.stderr = old_stderr
            sys.stdin = old_stdin

        return


def _sync_env(env, new, backup=None):
    for key, value in new.items():
        if backup is not None:
            backup[key] = env.get(key)
        if value is not None:
            env[key] = value
            continue
        try:
            del env[key]
        except Exception:
            pass
    return backup



class _EchoingStdin(object):

    def __init__(self, input, output):
        self._input = input
        self._output = output

    def __getattr__(self, x):
        return getattr(self._input, x)

    def _echo(self, rv):
        self._output.write(rv)
        return rv

    def read(self, n=-1):
        return self._echo(self._input.read(n))

    def readline(self, n=-1):
        return self._echo(self._input.readline(n))

    def readlines(self):
        return [self._echo(x) for x in self._input.readlines()]

    def __iter__(self):
        return iter(self._echo(x) for x in self._input)

    def __repr__(self):
        cn = self.__class__.__name__
        return '%s(%r)' % (cn, self._input)
