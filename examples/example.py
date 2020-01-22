"""The CLI application below is a motley assortment of subcommands
just for the purposes of showing off some face features.

( -- ._> -- )

"""
from __future__ import print_function

import sys

from face import Command, face_middleware, ListParam


def busy_loop(loop_count, stdout):
    """
    Does a bit of busy work. No sweat.
    """
    for i in range(loop_count or 3):
        stdout.write('work %s\n' % (i + 1))
    return


def sum_func(num):
    "Just a lil fun in the sum."
    print(sum(num))


def subtract(posargs_):
    summable = [float(posargs_[0])] + [-float(a) for a in posargs_[1:]]
    print(sum(summable))


def print_args(args_):
    print(args_.flags, args_.posargs, args_.post_posargs)


def main():
    cmd = Command(busy_loop, 'cmd', middlewares=[output_streams_mw])

    sum_subcmd = Command(sum_func, 'sum')
    sum_subcmd.add('--num', parse_as=ListParam(int), missing=(0,),
                   doc='a number to include in the sum, expects integers at the moment'
                   ' because it is fun to change things later')
    sum_subcmd.add('--grummmmmmmmmmmmmmmmmmm', parse_as=int, multi=True, missing=0,
                   doc='a bizarre creature, shrek-like, does nothing, but is here to'
                   ' make the help longer and less helpful but still good for wraps.')

    cmd.add(sum_subcmd)

    cmd.add(verbose_mw)

    cmd.add(subtract, doc='', posargs=float)

    cmd.add(print_args, 'print', '', posargs=True)

    cmd.add('--loop-count', parse_as=int)

    return cmd.run()  # execute


from face.parser import Flag


@face_middleware(flags=[Flag('--verbose', char='-V', parse_as=True)])
def verbose_mw(next_, verbose):
    if verbose:
        print('starting in verbose mode')
    ret = next_()
    if verbose:
        print('complete')
    return ret


@face_middleware(provides=['stdout', 'stderr'], optional=True)
def output_streams_mw(next_):
    return next_(stdout=sys.stdout, stderr=sys.stderr)



if __name__ == '__main__':
    sys.exit(main())
