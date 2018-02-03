
from __future__ import print_function

import sys

from face import Parser, Command, face_middleware
from face.parser import PosArgSpec
from face.helpers import AutoHelpBuilder


@face_middleware
def verbose_mw(next_, verbose):
    if verbose:
        print('starting in verbose mode')
    ret = next_()
    if verbose:
        print('complete')
    return ret


# TODO: need to check for provides names + flag names conflict
@face_middleware(provides=['stdout', 'stderr'])
def output_streams_mw(next_):
    return next_(stdout=sys.stdout, stderr=sys.stderr)


def busy_loop(loop_count, stdout):
    """
    Does a bit of busy work. No sweat.
    """
    for i in range(loop_count or 3):
        stdout.write('work %s\n' % (i + 1))
    return


def sum_func(num):
    print(sum(num))


def subtract_func(posargs_):
    summable = [float(posargs_[0])] + [-float(a) for a in posargs_[1:]]
    print(sum(summable))


def print_args(args_):
    print(args_.flags, args_.posargs, args_.trailing_args)


def main():
    cmd = Command(busy_loop, 'cmd', middlewares=[output_streams_mw])
    print(cmd.parser.desc)
    sum_subcmd = Command(sum_func, 'sum')
    sum_subcmd.add('--num', parse_as=int, on_duplicate='extend')
    cmd.add(sum_subcmd)

    cmd.add(verbose_mw)

    pas = PosArgSpec(parse_as=int, max_count=2, display_name='num')
    subt_subcmd = Command(subtract_func, 'subtract', '', posargs=pas)
    cmd.add(subt_subcmd)

    cmd.add(print_args, 'print', '', posargs=True)

    cmd.add('--verbose', alias='-V', parse_as=True)
    cmd.add('--loop-count', parse_as=int)

    ahb = AutoHelpBuilder(subt_subcmd)
    print(ahb.get_text())

    # return 0

    return cmd.run()  # execute


if __name__ == '__main__':
    sys.exit(main())
