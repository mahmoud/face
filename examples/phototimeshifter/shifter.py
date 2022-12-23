import datetime
import os

import tqdm
from boltons.fileutils import atomic_save
from boltons.timeutils import parse_timedelta
from textwrap import dedent
from exif import DATETIME_STR_FORMAT, Image
from face import ERROR, Command


def run(posargs_, shift, verbose, dryrun):
    """
    Shift the EXIF datetimes of photos, mostly to correct for minor clock skew 
    and timezone misconfigurations between multiple cameras.

    Modifies both the original EXIF date and the "digitized" EXIF date to be 
    the same time, shifted from the original time.

    Does not modify any other EXIF or XMP data
    (i.e., tags, ratings, etc. will remain intact and unchanged)
    """
    shift_td = parse_timedelta(shift)
    filenames = posargs_
    
    total_count, update_count = len(filenames), 0
    if len(filenames) > 1 and not dryrun and not verbose:
        filenames = tqdm.tqdm(filenames)
    for i, fn in enumerate(filenames):
        image = Image(fn)
        if not image.has_exif:
            print(f' -- no exif detected in: {fn}')
            continue
        if not image.datetime_original:
            print(f' -- no datetime detected in: {fn}')

        # NOTE: exif doesn't support XMP, so I used pyexiv2 to confirm that writing new times has no effect on XMP.
        # Note that performing this check requires installing pyexiv2, which requires compilation (requiring boost and libexiv2-dev on ubuntu)
        # import pyexiv2; md = pyexiv2.ImageMetadata(fn); md.read(); old_md = {k: v.value for k, v in md.items()}

        dt = datetime.datetime.strptime(image.datetime_original, DATETIME_STR_FORMAT)
        new_dt = dt + shift_td
        old_dt_fmtd = dt.strftime(DATETIME_STR_FORMAT)
        new_dt_fmtd = new_dt.strftime(DATETIME_STR_FORMAT)
        update_count += 1
        short_fn = os.path.split(fn)[-1]
        verbose_msg = f'{short_fn} datetime: {old_dt_fmtd} -> {new_dt_fmtd} (updated {update_count} / {total_count})'
        if dryrun:
            msg = f' ++ dryrun: {verbose_msg}' 
            print(msg, end='\n' if verbose else '\r')
            
        else:
            image.datetime_original = new_dt_fmtd
            image.datetime_digitized = new_dt_fmtd

            with atomic_save(fn, rm_part_on_exc=False) as new_img:
                new_img.write(image.get_file())
            if verbose:
                print(f'updated: {verbose_msg}')
            # md = pyexiv2.ImageMetadata(fn); md.read(); new_md = {k: v.value for k, v in md.items()}
            # assert new_md == old_md  # See NOTE above. Only true if run with "--shift 0m"

    if dryrun:
        print()


cmd = Command(run, posargs=True, doc=dedent(run.__doc__))
cmd.add('--shift', missing=ERROR, doc="shift timedelta string, e.g., '2h' or '3d 1h 4m'")
cmd.add('--dryrun', parse_as=True, doc="output change plan without modifying files")
cmd.add('--verbose', parse_as=True, doc="display file-by-file output instead of progress bar")

if __name__ == '__main__':
    cmd.run()
