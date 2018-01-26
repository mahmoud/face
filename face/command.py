
import sys
from collections import OrderedDict

from boltons.setutils import IndexedSet

from parser import Parser, Flag


def _get_default_name(frame_level=1):
    # TODO: is this a good idea? What if multiple parsers are created
    # in the same function for the sake of subparsers. This should
    # probably only be used from a classmethod or maybe a util
    # function.  TODO: what happens if a python module file contains a
    # non-ascii character?
    frame = sys._getframe(frame_level + 1)
    mod_name = frame.f_globals.get('__name__')
    if mod_name is None:
        return 'COMMAND'
    module = sys.modules[mod_name]
    if mod_name == '__main__':
        return module.__file__
    # TODO: reverse lookup entrypoint?
    return mod_name


class Command(object):
    def __init__(self, func, name, desc):
        name = name if name is not None else _get_default_name()
        self._parser = Parser(name, desc)
        # TODO: properties for name/desc/other parser things

        self.path_func_map = OrderedDict()
        self.path_func_map[()] = func

    @property
    def name(self):
        return self._parser.name

    @property
    def func(self):
        return self.path_func_map[()]

    def add(self, *a, **kw):
        subcmd = a[0]
        if not isinstance(subcmd, Command) and callable(subcmd):
            subcmd = Command(*a, **kw)  # attempt to construct a new subcmd
        if isinstance(subcmd, Command):
            old_paths = self._parser.subcmd_map.keys()
            self._parser.add(subcmd._parser)
            new_paths = IndexedSet(self._parser.subcmd_map.keys()) - IndexedSet(old_paths)
            # TODO: need to handle the case when there are multiple subcommands
            for subcmd_path in new_paths:
                self.path_func_map[subcmd_path] = subcmd.func
            return

        flag = a[0]
        if not isinstance(flag, Flag):
            flag = Flag(*a, **kw)  # attempt to construct a Flag from arguments
        self._parser.add(flag)

        return

    def run(self, argv=None):
        prs_res = self._parser.parse(argv=argv)
        func = self.path_func_map[prs_res.cmd]
        return func(prs_res)
