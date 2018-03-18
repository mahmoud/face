
from face import Parser, ListParam


def get_calc_parser():
    prs = Parser('cmd')

    sum_subprs = Parser('sum')
    sum_subprs.add('--num', multi=True, missing=0, parse_as=int,
                   doc='a number to include in the sum, expects integers at the moment'
                   ' because it is fun to change things later')
    prs.add(sum_subprs)

    prs.add('--verbose', char='-V', parse_as=True)
    prs.add('--loop-count', parse_as=int)

    return prs


def test_calc_parser():
    prs = get_calc_parser()

    res = prs.parse(['calc.py', '--verbose'])

    assert res.name == 'calc.py'
    assert res.flags['verbose'] is True

    res = prs.parse(['calc.py', '--loop_count', '5'])
    assert res.flags['loop_count'] == 5

    res = prs.parse(['calc.py', '--loop-count', '4'])
    assert res.flags['loop_count'] == 4

    res = prs.parse(['calc.py', 'sum', '--num', '4', '--num', '-2', '--num', '0'])
    assert res.subcmds == ('sum',)
    assert res.flags['num'] == [4, -2, 0]

    return
