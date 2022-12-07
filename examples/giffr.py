#!/usr/bin/env python
"""giffr extracts batches of gifs from mp4 files using
a few tricks to improve quality and output filesize.

Example command:

  ./giffr.py --fps 12 --height 360 --video ~/Videos/input.mp4

Timestamp ranges are expected as text file located in the same directory
as the video, with the same name and a .txt extension. The file can also
be explicitly specified with the --stamps flag. Timestamp file format is
one range per line:

  (HH:)MM:SS - (HH:)MM:SS (optional description can go here)

An example timestamp file:

  01:30 - 01:35 Nice clip
  
  00:04:22 - 00:04:44

This would generate two gifs, named 00_nice_clip.gif and 01.gif, in a
directory adjacent the input video.

Requires recent ffmpeg (2018+), and optionally gifsicle (for further gif optimization). 

See giffr.py -h for more options.

"""

import os
import re
import pprint
import datetime
import subprocess

from boltons.fileutils import mkdir_p
from boltons.strutils import slugify

from face import Command, ERROR, UsageError, echo  # NOTE: pip install face to fix an ImportError

FFMPEG_CMD = 'ffmpeg'
TIME_FORMAT = '%M:%S'
TIME_FORMAT_2 = '%H:%M:%S'


def main():
    cmd = Command(process, doc=__doc__)

    cmd.add('--video', missing=ERROR, doc='path to the input mp4 file')
    cmd.add('--stamps', missing=None, doc='path to the stamps file')
    cmd.add('--overwrite', parse_as=True, doc='overwrite files if they already exist')
    cmd.add('--verbose', parse_as=True, doc='more output')
    cmd.add('--fps', parse_as=int, doc='framerate (frames per second) for the final rendered gif. omit to keep full framerate, set lower to decrease filesize. 12 is good.')
    cmd.add('--height', parse_as=int, doc='height in pixels of the output gif. width is autocomputed, omit to keep full size, set lower to decrease filesize.')
    cmd.add('--optimize', parse_as=True, doc='use gifsicle to losslessly compress gif output (shaves a few kilobytes sometimes)')
    cmd.add('--alt-palette', parse_as=True, doc='use alternative approach to palette: computing once per frame instead of once for whole gif. improved look, but may increase filesize.')
    cmd.add('--out-dir', missing=None, doc='where to create the directory with gifs. defaults to same directory as video.')

    cmd.run()

def _parse_time(text):
    try:
        ret = datetime.datetime.strptime(text, TIME_FORMAT)
    except:
        ret = datetime.datetime.strptime(text, TIME_FORMAT_2)
    return ret


def _parse_timestamps(ts_text):
    ret = []
    lines = [line.strip() for line in ts_text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        parts = [x for x in re.split('[^\w:]', line) if x]
        start, end = parts[:2]
        desc = slugify(' '.join([f'{i:02}'] + parts[2:]), delim="_")

        start_dt = _parse_time(start)
        end_dt = _parse_time(end)
        assert end_dt > start_dt
        duration_ts = str(end_dt - start_dt)

        ret.append([start, end, duration_ts, desc])
    return ret


def process(video, stamps, overwrite, verbose, optimize, alt_palette, out_dir, fps=None, height=None):
    video_dir = os.path.dirname(os.path.abspath(video))
    if out_dir is None:
        out_dir = video_dir
        
    basename, extension = os.path.splitext(os.path.basename(video))
    if extension.lower() != '.mp4':
        raise UsageError(f'this command only supports mp4 at this time, not: {extension}')
    if not os.path.isfile(video):
        raise UsageError(f'missing video file: {video}')

    if stamps is None:
        inferred_stamps = video_dir + '/' + basename + '.txt'
        if os.path.isfile(inferred_stamps):
            stamps = inferred_stamps
            if verbose:
                echo(f'inferred timestamps filename: {stamps}')
        else:
            raise UsageError(f'missing --stamps value or file: {inferred_stamps}')

    with open(stamps) as f:
        timestamps = _parse_timestamps(f.read())
    if verbose:
        pprint.pprint(timestamps)

    gif_dir = out_dir + '/' + slugify(basename)
    mkdir_p(gif_dir)

    filters = []
    if fps:
        filters.append(f'fps={fps}')
    if height:
        assert height > 0
        filters.append(f'scale=-1:{height}')
    filters.append('split')

    for start, _, duration_ts, desc in timestamps:
        cmd = [FFMPEG_CMD, '-ss', start, '-t', duration_ts, '-i', video]
        if overwrite:
            cmd.append('-y')

        if alt_palette:
            palette_part = '[a] palettegen=stats_mode=single [p];[b][p] paletteuse=new=1'
        else:
            palette_part = '[a] palettegen [p];[b][p] paletteuse'

        cmd.extend(['-filter_complex', f'[0:v] {",".join(filters)} [a][b];{palette_part}'])

        if verbose:
            echo('# ' + ' '.join(cmd))

        gif_path = gif_dir + f'/{desc}.gif'
        cmd.append(gif_path)
        subprocess.check_call(cmd)

        if optimize:
            opt_cmd = ['gifsicle', '-i', gif_path, '--optimize=3', '-o', gif_path]
            subprocess.check_call(opt_cmd)
        
    return

if __name__ == '__main__':
    main()
