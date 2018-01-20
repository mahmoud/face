
import sys
from face import Parser


def main():
    prs = Parser('cmd')
    prs.add(Parser('subcmd'))
    prs.add('--verbose', '-V')
    prs.add('--num', parse_as=int)

    args = prs.parse(None)
    if args.verbose:
        print 'starting in verbose mode'
    if args.flags.get('num'):
        print args.flags['num'], type(args.flags['num'])
    print 'complete'
    return 1


if __name__ == '__main__':
    sys.exit(main())
