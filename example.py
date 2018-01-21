
import sys
from face import Parser


def main():
    prs = Parser('cmd')
    sum_subprs = Parser('sum')
    sum_subprs.add('--num', int, on_duplicate='extend')
    prs.add(sum_subprs)
    prs.add('--verbose', alias='-V')
    prs.add('--loop-count', parse_as=int)

    args = prs.parse(None)
    if args.verbose:
        print 'starting in verbose mode'

    if args.cmd == ('sum',):
        print sum(args.num)
    else:
        for i in range(args.flags.get('loop_count', 3)):
            print 'work', i + 1

    print 'complete'
    return 0


if __name__ == '__main__':
    sys.exit(main())
