#!/usr/bin/env python3

import re
import sys
from argparse import ArgumentParser
from collections import defaultdict
from os import rename
from logging import getLogger, DEBUG, INFO
from pathlib import PurePath
from os import getcwd
from os.path import isdir, isfile, join
from colorlog import StreamHandler, ColoredFormatter


LOG = getLogger(__name__)


def run(input, dry_run, source_dir, move_dir):
    files = defaultdict(list)

    for line_num, line in enumerate(input, start=1):
        match = re.match(r"(?P<hash>\w+) \((?P<path>.*)\)$", line)
        if not match:
            LOG.error("Invalid input line %d: '%s'", line_num, line)
            return 3

        files[match.group("hash")].append(PurePath(match.group("path")))

    for (file_hash, paths) in files.items():
        if len(paths) == 1:
            # No duplicates found
            continue

        # Sort first by name
        paths.sort(key=lambda p: p.name)
        # Now sort by whether the file is in the 'Sent' folder or not
        paths.sort(key=lambda p: p.parents[0].match('Sent'))

        if dry_run:
            keep_msg = "Hash %s, would keep %s (dry run)"
            drop_msg = "Hash %s, would drop %s (dry run)"
        else:
            keep_msg = "Hash %s, keeping %s"
            drop_msg = "Hash %s, dropping %s"

        keep = paths[0]
        drop = paths[1:]
        drop_names = [p.as_posix() for p in drop]

        # Warn when a file from the 'Sent' folder will be kept while
        # a file not in the 'Sent' folder will be removed
        warn = (keep.parents[0].match('Sent') and
            any(not p.parents[0].match('Sent') for p in drop))

        if warn:
            LOG.warning(keep_msg, file_hash, keep)
            LOG.warning(drop_msg, file_hash, drop_names)
        else:
            LOG.info(keep_msg, file_hash, keep)
            LOG.info(drop_msg, file_hash, drop_names)

        # Make sure the files to drop have valid paths
        for drop_path in drop:
            full_path = source_dir / drop_path
            if not isfile(full_path):
                LOG.error("Invalid file path '%s'", full_path)
                return 4

        if dry_run:
            continue

        # Remove or move files to specified directory
        for drop_path in drop:
            full_path = source_dir / drop_path
            if move_dir is None:
                LOG.info("Removing '%s'", full_path)
            else:
                move_path = move_dir / drop_path.name
                LOG.info("Moving '%s' to '%s'", full_path, move_path)
                rename(full_path, move_path)


def setup_log(log_level):
    handler = StreamHandler()
    handler.setFormatter(ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s"))
    LOG.addHandler(handler)
    LOG.setLevel(log_level)


def parse_args():
    parser = ArgumentParser(description="Media File Deduplicator")
    parser.add_argument("file", help="list of files with MD5 hashes")
    parser.add_argument("-s", "--source", default=getcwd(),
                        help="root of the file paths")
    parser.add_argument("-m", "--move", dest="move_dir",
                        help="move files to this directory instead of removing them")
    parser.add_argument("-d", "--debug", dest="log_level", default=INFO,
                        action="store_const", const=DEBUG,
                        help="enable debug logging")
    parser.add_argument("-n", "--dry-run", dest="dry_run", default=False,
                        action="store_const", const=True,
                        help="do not update files")
    return parser.parse_args()


def main():
    args = parse_args()
    setup_log(args.log_level)

    if args.move_dir is None:
        move_dir = None
    else:
        move_dir = PurePath(args.move_dir)
        if not isdir(move_dir):
            LOG.error("Invalid move directory '%s'", move_dir)
            return 2

    # try:
    with open(args.file) as file:
        return run(file.readlines(), args.dry_run, args.source, move_dir)
    # except...
    # return


if __name__ == '__main__':
    sys.exit(main())