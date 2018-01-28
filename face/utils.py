
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
