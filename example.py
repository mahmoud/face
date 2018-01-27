
import sys
from face import Parser, Command
from face.parser import PosArgSpec
from face.helpers import AutoHelpBuilder


def busy_loop(args):
    if args.verbose:
        print 'starting in verbose mode'
    for i in range(args.flags.get('loop_count', 3)):
        print 'work', i + 1
    print 'complete'


def sum_func(args):
    if args.verbose:
        print 'starting in verbose mode'
    print sum(args.num)
    print 'complete'


def subtract_func(args):
    if args.verbose:
        print 'starting in verbose mode'
    pos_args = args.pos_args
    summable = [pos_args[0]] + [-a for a in pos_args[1:]]
    print sum(summable)
    print 'complete'


def main():
    cmd = Command(busy_loop, 'cmd', '')
    sum_subcmd = Command(sum_func, 'sum', '')
    sum_subcmd.add('--num', int, on_duplicate='extend')
    cmd.add(sum_subcmd)

    pas = PosArgSpec(parse_as=int, min_count=5, display_name='num')
    subt_subcmd = Command(subtract_func, 'subtract', '', pos_args=pas)
    cmd.add(subt_subcmd)

    cmd.add('--verbose', alias='-V')
    cmd.add('--loop-count', parse_as=int)

    ahb = AutoHelpBuilder(subt_subcmd)
    print ahb.get_text()

    # return 0

    return cmd.run()  # execute


if __name__ == '__main__':
    sys.exit(main())
