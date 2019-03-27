# Design

Unlike URLs, there is no spec for parsing arguments. Much to my
dismay, frankly. Living through argparse and docopt and click, it was
like lash after lash against my poor CLI-loving flesh.

* getopt basis?
* Single- or no-argument flags only. No multi-argument flags
* Configurable behavior as to multiple appearances of the same flag
    * error (default)
    * additive - value will be an int for no-arg flags (as with
      --verbose and -vvv), and added to a list for single-argument
      flags
* Short flag support?
* strong subcommand support (compositionally similar to clastic?)
* store_true and store_false, or something better?
* single argument flags support space-based and 'x=y' style arguments
* transparent transformation between underscore and dash-based
  arguments (--enable-action and --enable_action are the same)
* single variadic argument list
    * only valid for leaf subcommands
* support partial parsing (a la parse_known_args)
* support taking multiple flagfiles
    * always the same argument name, like a builtin, then warn on conflict
    * could be an argument type
    * might need to take a flagfilereader argument for testin purposes
* No multi-level flag support. Flags push down under subcommands,
  conflicts raise errors early (at setup time). Flags can be masked
  out against being pushed under further subcommands (i.e., make the
  flag subcommand-local).

Big challenge: helpful error messages

/* TODO --key=val style arguments? */

## Functionality

By design, face supports command structure composed of five parts:

1. The command
2. The subcommand path
3. Flags
4. Positional arguments
5. Passthrough arguments

cmd subcmd subsubcmd subsubsubcmd --flags -v --flag-with-arg arg posarg1 posarg2       -- passarg1 passarg2
--- ----------------------------- ------------------------------ ----------------------   -----------------
command | subcommand path        | flags                        | positional arguments | passthrough arguments

Note that only leaf subcommands support positional arguments.

"command" is just a display name, as no parsing is required for sys.argv[0]

Collapsing abbreviated flags is not supported

# Help Design

If there are subcommands, do zfs-style subcommand syntax, only showing
required flags and pos args (by display name).

If at a leaf command, print full options listing for that path, with
argparse-style help.

If at a non-leaf command, argparse-style options help at that level
(and above) can go below the zfs-style subcommand summary.

Square [brackets] for optional. Angle <brackets> for required.

Boltons dependency can do basic pluralization/singularization for help
displays.

If a command has subcommands, then the automatic help should manifest
as a subcommand. Otherwise, it should be a longform flag like
--help. In a subcommand setting, the short "usage" message that pops
up when an invalid command is issued should recommend typing "cmd
help" for more options.

## OG Design Log

### Problems with argparse

argparse is a pretty solid library, and despite many competitors over
the years, the best argument parsing library available. Until now, of
course. Here's an inventory of problems argparse did not solve, and in
many ways, created.

* "Fuzzy" flag matching
* Inconvenient subcommand interface
* Flags at each level of the subcommand tree
* Positional arguments acceptable everywhere
* Bad help rendering (esp for subcommands)
* Inheritance-based API for extension with a lot of _*

At the end of the day, the real sin of argparse is that it enables the
creation of bad CLIs, often at the expense of ease of making good UIs
Despite this friction, argparse is far from infinitely powerful. As a
library, it is still relatively opinionated, and can only model a
somewhat-conventional UNIX-y CLI.

### Should face be more than a parser?

clastic calls your function for you, should this do that, too?  is
there an advantage to sticking to the argparse route of handing back
a namespace? what would the signature of a CLI route be?

* Specifying the CLI
* Wiring up the routing/dispatch
* OR Using the programmatic result of the parse (the Result object)
* Formatting the help messages?
* Using the actual CLI

### "Types" discussion

* Should we support arbitrary validators (schema?) or go the clastic route and only basic types:
  * str
  * int
  * float
  * bool (TODO: default to true/false, think store_true, store_false in argparse)
  * list of the above
  * (leaning toward just basic types)


### Some subcommand ideas

- autosuggest on incorrect subcommand
- allow subcommand grouping
- hyphens and underscores equivalent for flags and subcommands

A command cannot have positional arguments _and_ subcommands.

Need to be able to set display name for posargs

Which is the best default behavior for a flag? single flag where
presence=True (e.g., --verbose) or flag which accepts single string
arg (e.g., --path /a/b/c)

What to do if there appears to be flags after positional arguments?
How to differentiate between a bad flag and a positional argument that
starts with a dash?

### Design tag and philosophy

"Face: the CLI framework that's friendly to your end-user."

* Flag-first design that ensures flags stay consistent across all
  subcommands, for a more coherent API, less likely to surprise, more
  likely to delight.

(Note: need to do some research re: non-unicode flags to see how much
non-US CLI users care about em.)

Case-sensitive flags are bad for business *except for*
single-character flags (single-dash flags like -v vs -V).

TODO: normalizing subcommands

Should parse_as=List() with multi=extend give one long list or
a list of lists?

Parser is unable to determine which subcommands are valid leaf
commands, i.e., which ones can be handled as the last subcommand. The
Command dispatcher will have to raise an error if a specific
intermediary subcommand doesn't have a handler to dispatch to.

TODO: Duplicate arguments passed at the command line with the same value = ok?

### Strata integration

* will need to disable and handle flagfiles separately if provenance
is going to be retained?


### Should face have middleware or other clastic features?

* middleware seems unavoidable for setting up logs and generic
  teardowns/exit messages
* Might need an error map that maps various errors to exit codes for
  convenience. Neat idea, sort a list of classes by class hierarchy.

### Re: parse error corner cases

There are certain parse errors, such as the omission of a value
that takes a string argument which can semi-silently pass. For instance:

copy --dest --verbose /a/b/c

In this terrible CLI, --verbose could be absorbed as --dest's value
and now there's a file called --verbose on the filesystem. Here are a
few ideas to improve the situation:

1. Raise an exception for all flags' string arguments which start with
   a "-". Create a separate syntax for passing these args such as
   --flag=--dashedarg.
2. Similar to the above, but only raise exceptions on known
   flags. This creates a bit of a moving API, as a new flag could cause
   old values to fail.
3. Let particularly bad APIs like the above fail, but keep closer
   track of state to help identify missing arguments earlier in the line.

### A notable difference with Clastic

One big difference between Clastic and Face is that with Face, you
typically know your first and only request at startup time. With
Clastic, you create an Application and have to wait for some remote
user to issue a request.

This translates to a different default behavior. With Clastic, all
routes are checked for dependency satisfaction at Application
creation. With Face, this check is performed on-demand, and only the
single subcommand being executed is checked.

### Ideas for flag types:

* iso8601 date/time/datetime
* duration

### Middleware thoughts

* Clastic-like, but single function
* Mark with a @middleware(provides=()) decorator for provides

* Keywords (ParseResult members) end with _ (e.g., flags_), leaving
  injection namespace wide open for flags. With clastic, argument
  names are primarily internal, like a path parameter's name is not
  exposed to the user. With face, the flag names are part of the
  exposed API, and we don't want to reserve keywords or have
  excessively long prefixes.

* add() supports @middleware decorated middleware

* add_middleware() exists for non-decorated middleware functions, and
  just conveniently calls middleware decorator for you (decorator only
  necessary for provides)

Also Kurt says an easy way to access the subcommands to tweak them
would be useful. I think it's better to build up from the leaves than
to allow mutability that could trigger rechecks and failures across
the whole subcommand tree. Better instead to make copies of
subparsers/subcommands/flags and treat them as internal state.

* Different error message for when the command's handler function is
  unfulfilled vs middlewares.
* In addition to the existing function-as-first-arg interface, Command
  should take a list of add()-ables as the first argument. This allows
  easy composition from subcommands and common flags.
* DisplayOptions/DisplaySpec class? (display name and hidden)
* Should Commands have resources like clastic?


### What goes in a bound command?

* name
* doc
* handler func
* list of middlewares
* parser (currently contains the following)
    * flag map
    * PosArgSpecs for posargs, post_posargs
    * flagfile flag
    * help flag (or help subcommand)

TODO: allow user to configure the message for CommandLineErrors
TODO: should Command take resources?
TODO: should version_ be a built-in/injectable?

Need to split up the checks. Basic verification of middleware
structure OK. Can check for redefinitions of provides and
conflicts. Need a final .check() method that checks that all
subcommands have their requirements fulfilled. Technically a .run()
only needs to run one specific subcommand, only thta one needs to get
its middleware chain built. .check() would have to build/check them
all.

* Command inherit from Parser
* Enable middleware flags
* Ensure top-level middleware flags like --verbose show up for subcommands
* Ensure "builtin" flags like --flagfile and --help show up for all commands
* Make help flag come from HelpHandler
* What to do when the top-level command doesn't have a help_handler,
  but a subcommand does? Maybe dispatch to the subcommand's help
  handler? Would deferring adding the HelpHandler's flag/subcmd help?
  Right now the help flag is parsed and ignored.


### Notes on making Command inherit from Parser

The only fuzzy area is when to use prs.get_flag_map() vs
prs._path_flag_map directly. Basically, when filtration-by-usage is
desired, get_flag_map() (or get_flags()) should be used. Only Commands
do this, so it looks a bit weird if you're only looking at the Parser,
where this operation appears to do nothing. This only happens in 1-2
places so probably safe to just comment it for now.

Relatedly, there are some linting errors where it appears the private
_path_flag_map is being accessed. I think these are ok, because these
methods are operating on objects of the same type, so the members are
still technically "protected", in the C++ OOP sense.

### A question about weakdeps

Should weak deps on builtins_ be treated differently than weak
deps on flags? Should weak deps in handler functions be treated
differently than that in the middleware (middleware implies more
"passthrough")?


## zfs-style help

zpool help is probably handwritten (as evidenced by multiple instances
of subcommands like "import" and spacing between groups like
add/remove), but we can probably get pretty close to this.

```
$ zpool --help
usage: zpool command args ...
where 'command' is one of the following:

create [-fnd] [-o property=value] ...
    [-O file-system-property=value] ...
    [-m mountpoint] [-R root] <pool> <vdev> ...
destroy [-f] <pool>

add [-fgLnP] [-o property=value] <pool> <vdev> ...
remove <pool> <device> ...

labelclear [-f] <vdev>

list [-gHLPv] [-o property[,...]] [-T d|u] [pool] ... [interval [count]]
iostat [-gLPvy] [-T d|u] [pool] ... [interval [count]]
status [-gLPvxD] [-T d|u] [pool] ... [interval [count]]

online <pool> <device> ...
offline [-t] <pool> <device> ...
clear [-nF] <pool> [device]
reopen <pool>

attach [-f] [-o property=value] <pool> <device> <new-device>
detach <pool> <device>
replace [-f] [-o property=value] <pool> <device> [new-device]
split [-gLnP] [-R altroot] [-o mntopts]
    [-o property=value] <pool> <newpool> [<device> ...]

scrub [-s] <pool> ...

import [-d dir] [-D]
import [-d dir | -c cachefile] [-F [-n]] <pool | id>
import [-o mntopts] [-o property=value] ...
    [-d dir | -c cachefile] [-D] [-f] [-m] [-N] [-R root] [-F [-n]] -a
import [-o mntopts] [-o property=value] ...
    [-d dir | -c cachefile] [-D] [-f] [-m] [-N] [-R root] [-F [-n]]
    <pool | id> [newpool]
export [-af] <pool> ...
upgrade
upgrade -v
upgrade [-V version] <-a | pool ...>
reguid <pool>

history [-il] [<pool>] ...
events [-vHfc]

get [-pH] <"all" | property[,...]> <pool> ...
set <property=value> <pool>
```

## youtube-dl help

argparse-based, lots of options

```
Usage: youtube-dl [OPTIONS] URL [URL...]

Options:
  General Options:
    -h, --help                       Print this help text and exit
    --version                        Print program version and exit
    -U, --update                     Update this program to latest version. Make sure that you have sufficient permissions (run with
                                     sudo if needed)
    -i, --ignore-errors              Continue on download errors, for example to skip unavailable videos in a playlist
    --abort-on-error                 Abort downloading of further videos (in the playlist or the command line) if an error occurs
    --dump-user-agent                Display the current browser identification
    --list-extractors                List all supported extractors
    --extractor-descriptions         Output descriptions of all supported extractors
    --force-generic-extractor        Force extraction to use the generic extractor
    --default-search PREFIX          Use this prefix for unqualified URLs. For example "gvsearch2:" downloads two videos from google
                                     videos for youtube-dl "large apple". Use the value "auto" to let youtube-dl guess ("auto_warning"
                                     to emit a warning when guessing). "error" just throws an error. The default value "fixup_error"
                                     repairs broken URLs, but emits an error if this is not possible instead of searching.
    --ignore-config                  Do not read configuration files. When given in the global configuration file /etc/youtube-dl.conf:
                                     Do not read the user configuration in ~/.config/youtube-dl/config (%APPDATA%/youtube-dl/config.txt
                                     on Windows)
    --config-location PATH           Location of the configuration file; either the path to the config or its containing directory.
    --flat-playlist                  Do not extract the videos of a playlist, only list them.
    --mark-watched                   Mark videos watched (YouTube only)
    --no-mark-watched                Do not mark videos watched (YouTube only)
    --no-color                       Do not emit color codes in output

  Network Options:
    --proxy URL                      Use the specified HTTP/HTTPS/SOCKS proxy. To enable experimental SOCKS proxy, specify a proper
                                     scheme. For example socks5://127.0.0.1:1080/. Pass in an empty string (--proxy "") for direct
                                     connection
    --socket-timeout SECONDS         Time to wait before giving up, in seconds
    --source-address IP              Client-side IP address to bind to
    -4, --force-ipv4                 Make all connections via IPv4
    -6, --force-ipv6                 Make all connections via IPv6

  Geo Restriction:
    --geo-verification-proxy URL     Use this proxy to verify the IP address for some geo-restricted sites. The default proxy specified
                                     by --proxy (or none, if the options is not present) is used for the actual downloading.
    --geo-bypass                     Bypass geographic restriction via faking X-Forwarded-For HTTP header (experimental)
    --no-geo-bypass                  Do not bypass geographic restriction via faking X-Forwarded-For HTTP header (experimental)
    --geo-bypass-country CODE        Force bypass geographic restriction with explicitly provided two-letter ISO 3166-2 country code
                                     (experimental)

  Video Selection:
    --playlist-start NUMBER          Playlist video to start at (default is 1)
    --playlist-end NUMBER            Playlist video to end at (default is last)
    --playlist-items ITEM_SPEC       Playlist video items to download. Specify indices of the videos in the playlist separated by commas
                                     like: "--playlist-items 1,2,5,8" if you want to download videos indexed 1, 2, 5, 8 in the playlist.
                                     You can specify range: "--playlist-items 1-3,7,10-13", it will download the videos at index 1, 2,
                                     3, 7, 10, 11, 12 and 13.
    --match-title REGEX              Download only matching titles (regex or caseless sub-string)
    --reject-title REGEX             Skip download for matching titles (regex or caseless sub-string)
    --max-downloads NUMBER           Abort after downloading NUMBER files
    --min-filesize SIZE              Do not download any videos smaller than SIZE (e.g. 50k or 44.6m)
    --max-filesize SIZE              Do not download any videos larger than SIZE (e.g. 50k or 44.6m)
    --date DATE                      Download only videos uploaded in this date
    --datebefore DATE                Download only videos uploaded on or before this date (i.e. inclusive)
    --dateafter DATE                 Download only videos uploaded on or after this date (i.e. inclusive)
    --min-views COUNT                Do not download any videos with less than COUNT views
    --max-views COUNT                Do not download any videos with more than COUNT views
    --match-filter FILTER            Generic video filter. Specify any key (see the "OUTPUT TEMPLATE" for a list of available keys) to
                                     match if the key is present, !key to check if the key is not present, key > NUMBER (like
                                     "comment_count > 12", also works with >=, <, <=, !=, =) to compare against a number, key =
                                     'LITERAL' (like "uploader = 'Mike Smith'", also works with !=) to match against a string literal
                                     and & to require multiple matches. Values which are not known are excluded unless you put a
                                     question mark (?) after the operator. For example, to only match videos that have been liked more
                                     than 100 times and disliked less than 50 times (or the dislike functionality is not available at
                                     the given service), but who also have a description, use --match-filter "like_count > 100 &
                                     dislike_count <? 50 & description" .
    --no-playlist                    Download only the video, if the URL refers to a video and a playlist.
    --yes-playlist                   Download the playlist, if the URL refers to a video and a playlist.
    --age-limit YEARS                Download only videos suitable for the given age
    --download-archive FILE          Download only videos not listed in the archive file. Record the IDs of all downloaded videos in it.
    --include-ads                    Download advertisements as well (experimental)

  Download Options:
    -r, --limit-rate RATE            Maximum download rate in bytes per second (e.g. 50K or 4.2M)
    -R, --retries RETRIES            Number of retries (default is 10), or "infinite".
    --fragment-retries RETRIES       Number of retries for a fragment (default is 10), or "infinite" (DASH, hlsnative and ISM)
    --skip-unavailable-fragments     Skip unavailable fragments (DASH, hlsnative and ISM)
    --abort-on-unavailable-fragment  Abort downloading when some fragment is not available
    --keep-fragments                 Keep downloaded fragments on disk after downloading is finished; fragments are erased by default
    --buffer-size SIZE               Size of download buffer (e.g. 1024 or 16K) (default is 1024)
    --no-resize-buffer               Do not automatically adjust the buffer size. By default, the buffer size is automatically resized
                                     from an initial value of SIZE.
    --playlist-reverse               Download playlist videos in reverse order
    --playlist-random                Download playlist videos in random order
    --xattr-set-filesize             Set file xattribute ytdl.filesize with expected file size (experimental)
    --hls-prefer-native              Use the native HLS downloader instead of ffmpeg
    --hls-prefer-ffmpeg              Use ffmpeg instead of the native HLS downloader
    --hls-use-mpegts                 Use the mpegts container for HLS videos, allowing to play the video while downloading (some players
                                     may not be able to play it)
    --external-downloader COMMAND    Use the specified external downloader. Currently supports
                                     aria2c,avconv,axel,curl,ffmpeg,httpie,wget
    --external-downloader-args ARGS  Give these arguments to the external downloader

  Filesystem Options:
    -a, --batch-file FILE            File containing URLs to download ('-' for stdin)
    --id                             Use only video ID in file name
    -o, --output TEMPLATE            Output filename template, see the "OUTPUT TEMPLATE" for all the info
    --autonumber-start NUMBER        Specify the start value for %(autonumber)s (default is 1)
    --restrict-filenames             Restrict filenames to only ASCII characters, and avoid "&" and spaces in filenames
    -w, --no-overwrites              Do not overwrite files
    -c, --continue                   Force resume of partially downloaded files. By default, youtube-dl will resume downloads if
                                     possible.
    --no-continue                    Do not resume partially downloaded files (restart from beginning)
    --no-part                        Do not use .part files - write directly into output file
    --no-mtime                       Do not use the Last-modified header to set the file modification time
    --write-description              Write video description to a .description file
    --write-info-json                Write video metadata to a .info.json file
    --write-annotations              Write video annotations to a .annotations.xml file
    --load-info-json FILE            JSON file containing the video information (created with the "--write-info-json" option)
    --cookies FILE                   File to read cookies from and dump cookie jar in
    --cache-dir DIR                  Location in the filesystem where youtube-dl can store some downloaded information permanently. By
                                     default $XDG_CACHE_HOME/youtube-dl or ~/.cache/youtube-dl . At the moment, only YouTube player
                                     files (for videos with obfuscated signatures) are cached, but that may change.
    --no-cache-dir                   Disable filesystem caching
    --rm-cache-dir                   Delete all filesystem cache files

  Thumbnail images:
    --write-thumbnail                Write thumbnail image to disk
    --write-all-thumbnails           Write all thumbnail image formats to disk
    --list-thumbnails                Simulate and list all available thumbnail formats

  Verbosity / Simulation Options:
    -q, --quiet                      Activate quiet mode
    --no-warnings                    Ignore warnings
    -s, --simulate                   Do not download the video and do not write anything to disk
    --skip-download                  Do not download the video
    -g, --get-url                    Simulate, quiet but print URL
    -e, --get-title                  Simulate, quiet but print title
    --get-id                         Simulate, quiet but print id
    --get-thumbnail                  Simulate, quiet but print thumbnail URL
    --get-description                Simulate, quiet but print video description
    --get-duration                   Simulate, quiet but print video length
    --get-filename                   Simulate, quiet but print output filename
    --get-format                     Simulate, quiet but print output format
    -j, --dump-json                  Simulate, quiet but print JSON information. See the "OUTPUT TEMPLATE" for a description of
                                     available keys.
    -J, --dump-single-json           Simulate, quiet but print JSON information for each command-line argument. If the URL refers to a
                                     playlist, dump the whole playlist information in a single line.
    --print-json                     Be quiet and print the video information as JSON (video is still being downloaded).
    --newline                        Output progress bar as new lines
    --no-progress                    Do not print progress bar
    --console-title                  Display progress in console titlebar
    -v, --verbose                    Print various debugging information
    --dump-pages                     Print downloaded pages encoded using base64 to debug problems (very verbose)
    --write-pages                    Write downloaded intermediary pages to files in the current directory to debug problems
    --print-traffic                  Display sent and read HTTP traffic
    -C, --call-home                  Contact the youtube-dl server for debugging
    --no-call-home                   Do NOT contact the youtube-dl server for debugging

  Workarounds:
    --encoding ENCODING              Force the specified encoding (experimental)
    --no-check-certificate           Suppress HTTPS certificate validation
    --prefer-insecure                Use an unencrypted connection to retrieve information about the video. (Currently supported only
                                     for YouTube)
    --user-agent UA                  Specify a custom user agent
    --referer URL                    Specify a custom referer, use if the video access is restricted to one domain
    --add-header FIELD:VALUE         Specify a custom HTTP header and its value, separated by a colon ':'. You can use this option
                                     multiple times
    --bidi-workaround                Work around terminals that lack bidirectional text support. Requires bidiv or fribidi executable in
                                     PATH
    --sleep-interval SECONDS         Number of seconds to sleep before each download when used alone or a lower bound of a range for
                                     randomized sleep before each download (minimum possible number of seconds to sleep) when used along
                                     with --max-sleep-interval.
    --max-sleep-interval SECONDS     Upper bound of a range for randomized sleep before each download (maximum possible number of
                                     seconds to sleep). Must only be used along with --min-sleep-interval.

  Video Format Options:
    -f, --format FORMAT              Video format code, see the "FORMAT SELECTION" for all the info
    --all-formats                    Download all available video formats
    --prefer-free-formats            Prefer free video formats unless a specific one is requested
    -F, --list-formats               List all available formats of requested videos
    --youtube-skip-dash-manifest     Do not download the DASH manifests and related data on YouTube videos
    --merge-output-format FORMAT     If a merge is required (e.g. bestvideo+bestaudio), output to given container format. One of mkv,
                                     mp4, ogg, webm, flv. Ignored if no merge is required

  Subtitle Options:
    --write-sub                      Write subtitle file
    --write-auto-sub                 Write automatically generated subtitle file (YouTube only)
    --all-subs                       Download all the available subtitles of the video
    --list-subs                      List all available subtitles for the video
    --sub-format FORMAT              Subtitle format, accepts formats preference, for example: "srt" or "ass/srt/best"
    --sub-lang LANGS                 Languages of the subtitles to download (optional) separated by commas, use --list-subs for
                                     available language tags

  Authentication Options:
    -u, --username USERNAME          Login with this account ID
    -p, --password PASSWORD          Account password. If this option is left out, youtube-dl will ask interactively.
    -2, --twofactor TWOFACTOR        Two-factor authentication code
    -n, --netrc                      Use .netrc authentication data
    --video-password PASSWORD        Video password (vimeo, smotri, youku)

  Adobe Pass Options:
    --ap-mso MSO                     Adobe Pass multiple-system operator (TV provider) identifier, use --ap-list-mso for a list of
                                     available MSOs
    --ap-username USERNAME           Multiple-system operator account login
    --ap-password PASSWORD           Multiple-system operator account password. If this option is left out, youtube-dl will ask
                                     interactively.
    --ap-list-mso                    List all supported multiple-system operators

  Post-processing Options:
    -x, --extract-audio              Convert video files to audio-only files (requires ffmpeg or avconv and ffprobe or avprobe)
    --audio-format FORMAT            Specify audio format: "best", "aac", "flac", "mp3", "m4a", "opus", "vorbis", or "wav"; "best" by
                                     default; No effect without -x
    --audio-quality QUALITY          Specify ffmpeg/avconv audio quality, insert a value between 0 (better) and 9 (worse) for VBR or a
                                     specific bitrate like 128K (default 5)
    --recode-video FORMAT            Encode the video to another format if necessary (currently supported: mp4|flv|ogg|webm|mkv|avi)
    --postprocessor-args ARGS        Give these arguments to the postprocessor
    -k, --keep-video                 Keep the video file on disk after the post-processing; the video is erased by default
    --no-post-overwrites             Do not overwrite post-processed files; the post-processed files are overwritten by default
    --embed-subs                     Embed subtitles in the video (only for mp4, webm and mkv videos)
    --embed-thumbnail                Embed thumbnail in the audio as cover art
    --add-metadata                   Write metadata to the video file
    --metadata-from-title FORMAT     Parse additional metadata like song title / artist from the video title. The format syntax is the
                                     same as --output. Regular expression with named capture groups may also be used. The parsed
                                     parameters replace existing values. Example: --metadata-from-title "%(artist)s - %(title)s" matches
                                     a title like "Coldplay - Paradise". Example (regex): --metadata-from-title "(?P<artist>.+?) -
                                     (?P<title>.+)"
    --xattrs                         Write metadata to the video file's xattrs (using dublin core and xdg standards)
    --fixup POLICY                   Automatically correct known faults of the file. One of never (do nothing), warn (only emit a
                                     warning), detect_or_warn (the default; fix file if we can, warn otherwise)
    --prefer-avconv                  Prefer avconv over ffmpeg for running the postprocessors (default)
    --prefer-ffmpeg                  Prefer ffmpeg over avconv for running the postprocessors
    --ffmpeg-location PATH           Location of the ffmpeg/avconv binary; either the path to the binary or its containing directory.
    --exec CMD                       Execute a command on the file after downloading, similar to find's -exec syntax. Example: --exec
                                     'adb push {} /sdcard/Music/ && rm {}'
    --convert-subs FORMAT            Convert the subtitles to other format (currently supported: srt|ass|vtt|lrc)
```


## PocketProtector v0.1 help

modified argparse

```
$ pprotect --help
usage: pprotect [COMMANDS]

Commands:
  add-domain            add a new domain to the protected
  add-key-custodian     add a new key custodian to the protected
  add-owner             add a key custodian as owner of a domain
  add-secret            add a secret to a specified domain
  decrypt-domain        decrypt and display JSON-formatted cleartext for a
                        domain
  init                  create a new pocket-protected file
  list-all-secrets      display all secrets, with a list of domains the key is
                        present in
  list-audit-log        display a chronological list of audit log entries
                        representing file activity
  list-domain-secrets   display a list of secrets under a specific domain
  list-domains          display a list of available domains
  list-user-secrets     similar to list-all-secrets, but filtered by a given
                        user
  rm-domain             remove a domain from the protected
  rm-owner              remove an owner's privileges on a specified domain
  rm-secret             remove a secret from a specified domain
  rotate-domain-keys    rotate the internal keys for a particular domain (must
                        be owner)
  set-key-custodian-passphrase
                        change a key custodian passphrase
  update-secret         update an existing secret in a specified domain

Options:
  -h, --help            show this help message and exit
```

# git error messages

```
$ git lol
git: 'lol' is not a git command. See 'git --help'.

Did you mean this?
    log
```

Pretty nice, draws attention to itself by being bigger, recommends
help. The "did you mean" should include the command itself, i.e., "git
log" instead of just "log" for easy copy and pastability.

# API Design

Face is designed to scale to a wide variety of command-line
applications. As such, there are multiple levels of integration, each
providing more control.

1. A single "autocommand" convenience function that automatically
   generates a command-line interface.
2. A more explicit object-oriented Command construction interface,
   with a polymorphic .add() method to add subcommands, flags, and
   middlewares.
3. Same as #2, but with explicit Command construction and direct usage
   of the explicit methods used to add subcommands and flags.

All these options also come with the .run() method, which is used to
dispatch to the developer's logic, much like how a web framework
dispatches a client request to a endpoint function (sometimes called a
"view" or "controller"). By default, the program automatically handles
any --help / -h flags, prints the help output, and exits.

For certain advanced use cases, there is an additional API option, the
Parser itself.

Face's Parser is configured almost identically to the Command, except
that it does not take callables, and has no .run() method to dispatch
to application code. Instead, integrators call .parse() to parse and
validate flags and arguments, and handle flow control themselves. The
Parser, much like the Command, has a default HelpHandler, which can
render help, but only if explicitly called by the integrator. Parse
errors can be caught like any other kind of Python exception. Again,
the integrator has full control of program flow.

## Polymorphism

Thanks to their prevalence in our workflow, we developers
underestimate the variety and configurability of CLIs. As mentioned
above, Face's APIs intentionally use polymorphism to better serve the
evolving needs of a growing CLI.

A common pattern for Face arguments:

1. Unset. Most arguments to Face APIs are optional. Everything has
   defaults designed to minimize surprise.
2. Boolean. Pass True to enable a behavior (or show an element), or
   False to disable it (or hide it).
3. Integer or string. Enable/show, and use this limit/label.
4. dict. Complex configurables are represented by objects. This
   dictionary is a mapping of keyword arguments that will be passed
   straight through to the configuration object constructor. Mostly
   used to minimize imports and memorization of class names.
5. A configuration object, manually imported and constructed by the
   user. Like most data objects, stateless and reusable. The most
   explicit option.

For an example of this, look no further than the "posargs" argument to
Parser/Command and the PosArgSpec configuration object that it expects
or expects to be able to create.

In my experience, the worst part about argparse and other UI libraries
is constantly referencing the docs. When the API is too big, and there
are too many methods and signatures to memorize, I find myself
spending too much time in the docs (and often still not finding the
feature I want/need). Face aims to be the library that changes that
for CLIs. As few imports, methods, and arguments as is responsible.
