#!/usr/bin/env python
"""This small CLI app losslessly extracts parts of mp4 video by
wrapping the canonical command-line video encoder, ffmpeg. ffmpeg's
CLI interface is tricky, and cut_mp4's isn't! No more having to
remember flag order!

cut_mp4.py was written to minimally "edit" individual talk videos out of
longer streams, recorded at Pyninsula, a local Python meetup I
co-organize. Earlier videos didn't use this approach and had minor
audio sync issues. Later videos are better about this. Results
available here:
https://www.youtube.com/channel/UCiT1ZWcRdFLx7PuR3fTjTfA

An example command:

   ./cut_mp4.py --input input.mp4 --start 00:00:08 --end 00:02:02 --no-align-keyframes --output output.mp4

Run ./cut_mp4.py --help for more info.

"""

import os
import sys
import argparse
import datetime
import subprocess

from face import Command, ERROR  # NOTE: pip install face to fix an ImportError

FFMPEG_CMD = 'ffmpeg'
TIME_FORMAT = '%H:%M:%S'


def cut_mp4(input, output, start, end, no_align_keyframes=False):
    start_ts = start or '00:00:00'
    start_dt = datetime.datetime.strptime(start_ts, TIME_FORMAT)

    end_ts = end or '23:59:59'  # TODO
    end_dt = datetime.datetime.strptime(end_ts, TIME_FORMAT)

    assert end_dt > start_dt
    duration_ts = str(end_dt - start_dt)

    cmd = [FFMPEG_CMD, '-ss', start_ts]

    if not no_align_keyframes:
        cmd.append('-noaccurate_seek')

    cmd.extend(['-i', input, '-vcodec', 'copy', '-acodec', 'copy',
                '-t', duration_ts, '-avoid_negative_ts', 'make_zero', output])

    print('# ' + ' '.join(cmd))

    return subprocess.check_call(cmd)


def main():
    cmd = Command(cut_mp4, doc='losslessly cut an mp4 video to a time range')
    cmd.add('--input')
    cmd.add('--output')
    cmd.add('--start')
    cmd.add('--end')
    cmd.add('--no-align-keyframes', parse_as=True)

    cmd.run()


if __name__ == '__main__':
    main()


"""This program was originally written with argparse, the CLI
integration code of which is below::

    def main(argv):
        prs = argparse.ArgumentParser()
        add_arg = prs.add_argument
        add_arg('--input', required=True)
        add_arg('--output', required=True)
        add_arg('--start')
        add_arg('--end')
        add_arg('--no-align-keyframes', action="store_true")

        args = prs.parse_args(argv)

        return cut_mp4(input=args.input,
                       output=args.output,
                       start=args.start,
                       end=args.end,
                       no_align_keyframes=args.no_align_keyframes)


    if __name__ == '__main__':
        sys.exit(main(sys.argv[1:]))


Due to the lack of subcommands and relative simplicity, the delta
between face and argparse isn't so remarkable. Still, you can see how
certain constructs compare.

"""
