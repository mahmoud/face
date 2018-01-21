
import sys
from face import Parser


def main():
    prs = Parser('cmd')
    prs.add(Parser('subcmd'))
    prs.add('--verbose', alias='-V')
    prs.add('--loop-count', parse_as=int)

    args = prs.parse(None)
    if args.verbose:
        print 'starting in verbose mode'

    for i in range(args.flags.get('loop_count', 3)):
        print 'work', i

    print 'complete'
    return 1


if __name__ == '__main__':
    sys.exit(main())
