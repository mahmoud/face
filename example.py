
from __future__ import print_function

import sys

from face import Parser, Command, face_middleware
from face.parser import PosArgSpec
from face.helpers import AutoHelpBuilder


@face_middleware(provides=['lol'])
def my_first_mw(next_):
    print('hi')
    ret = next_(lol='lol')
    print('bye')
    return ret


def busy_loop(args_):
    """
    does a bit of busy work. No sweat.
    """
    if args_.verbose:
        print('starting in verbose mode')
    for i in range(args_.flags.get('loop_count', 3)):
        print('work', i + 1)
    print('complete')


def sum_func(args_):
    if args_.verbose:
        print('starting in verbose mode')
    print(sum(args_.num))
    print('complete')


def subtract_func(args_):
    if args_.verbose:
        print('starting in verbose mode')
    pos_args_ = args_.pos_args
    summable = [pos_args_[0]] + [-a for a in pos_args_[1:]]
    print(sum(summable))
    print('complete')


def print_args(args_):
    if args_.verbose:
        print('starting in verbose mode')
    print(args_.flags, args_.pos_args, args_.trailing_args)
    print('complete')


def main():
    cmd = Command(busy_loop, 'cmd', middlewares=[my_first_mw])
    print(cmd.parser.desc)
    sum_subcmd = Command(sum_func, 'sum')
    sum_subcmd.add('--num', int, on_duplicate='extend')
    cmd.add(sum_subcmd)

    cmd.add(my_first_mw)

    pas = PosArgSpec(parse_as=int, max_count=2, display_name='num')
    subt_subcmd = Command(subtract_func, 'subtract', '', pos_args=pas)
    cmd.add(subt_subcmd)

    cmd.add(print_args, 'print', '', pos_args=True)

    cmd.add('--verbose', alias='-V', default=False)
    cmd.add('--loop-count', parse_as=int)

    ahb = AutoHelpBuilder(subt_subcmd)
    print(ahb.get_text())

    # return 0

    return cmd.run()  # execute


if __name__ == '__main__':
    sys.exit(main())
