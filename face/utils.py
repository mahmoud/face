
def unwrap_text(text):
    all_grafs = []
    cur_graf = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            cur_graf.append(line)
        else:
            all_grafs.append(' '.join(cur_graf))
            cur_graf = []
    if cur_graf:
        all_grafs.append(' '.join(cur_graf))
    return '\n'.join(all_grafs)


def format_invocation(name='', args=(), kwargs=None):
    kwargs = kwargs or {}
    a_text = ', '.join([repr(a) for a in args])
    kw_text = ', '.join(['%s=%r' % (k, v) for k, v in kwargs.items()])

    star_args_text = a_text
    if star_args_text and kw_text:
        star_args_text += ', '
    star_args_text += kw_text

    return '%s(%s)' % (name, star_args_text)


def get_rdep_map(dep_map):
    """
    expects and returns a dict of {item: set([deps])}

    item can be a string or any other hashable object.
    """
    # TODO: the way this is used, this function doesn't receive
    # information about what functions take what args. this ends up
    # just being args depending on args, with no mediating middleware
    # names. this can make circular dependencies harder to debug.
    ret = {}
    for key in dep_map:
        to_proc, rdeps, cur_chain = [key], set(), []
        while to_proc:
            cur = to_proc.pop()
            cur_chain.append(cur)

            cur_rdeps = dep_map.get(cur, [])

            if key in cur_rdeps:
                raise ValueError('dependency cycle: %r recursively depends'
                                 ' on itself. full dep chain: %r' % (cur, cur_chain))

            to_proc.extend([c for c in cur_rdeps if c not in to_proc])
            rdeps.update(cur_rdeps)

        ret[key] = rdeps
    return ret
