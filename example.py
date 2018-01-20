
import sys
from face import Parser


def main():
    prs = Parser('cmd')
    prs.add(Parser('subcmd'))
    prs.add('--verbose', '-V')

    args = prs.parse(None)
    if args.verbose:
        print 'starting in verbose mode'
    print 'complete'
    return 1


if __name__ == '__main__':
    sys.exit(main())
