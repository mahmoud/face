
import sys
from face import Parser, Command


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


def main():
    cmd = Command(busy_loop, 'cmd', '')
    sum_subcmd = Command(sum_func, 'sum', '')
    sum_subcmd.add('--num', int, on_duplicate='extend')
    cmd.add(sum_subcmd)
    cmd.add('--verbose', alias='-V')
    cmd.add('--loop-count', parse_as=int)

    cmd.run()  # execute


if __name__ == '__main__':
    sys.exit(main())
