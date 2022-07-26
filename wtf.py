#!/usr/bin/env python3

import re
import sys
from argparse import ArgumentParser
from datetime import datetime
from logging import getLogger, DEBUG, INFO
from os import listdir, getcwd
from os.path import isfile, join
from subprocess import run, CalledProcessError
from colorlog import StreamHandler, ColoredFormatter


LOG = getLogger(__name__)


def get_exif(dir_name, file_name):
    command = ["exiftool", "-s", "-EXIF:DateTimeOriginal", "-EXIF:Make",
               "-EXIF:Model", join(dir_name, file_name)]
    ret = run(command, check=True, capture_output=True)
    pairs = [line.split(":", 1) for line in ret.stdout.decode().splitlines()]
    return dict((kv[0].strip(), kv[1].strip()) for kv in pairs if len(kv) == 2)


def set_exif(dir_name, file_name, timestamp_str):
    LOG.info("Updating timestamp of '%s' to '%s'...", file_name, timestamp_str)
    command = ["exiftool", f"-EXIF:DateTimeOriginal='{timestamp_str}'",
               "-EXIF:Make=WhatsApp", "-EXIF:Model=WhatsApp",
               join(dir_name, file_name)]
    run(command, check=True)


def update(dir_name, file_name, received_ts):
    exif_data = get_exif(dir_name, file_name)

    curr_ts = exif_data.get("DateTimeOriginal")
    if curr_ts is not None:
        LOG.warning("Skipping '%s': timestamp already set: '%s'",
                    file_name, curr_ts)
        return

    make = exif_data.get("Make", "WhatsApp")
    model = exif_data.get("Model", "WhatsApp")
    if make != "WhatsApp" or model != "WhatsApp":
        LOG.error("Make/Model of '%s' already set: '%s/%s'", file_name, make,
                  model)
        return

    set_exif(dir_name, file_name, received_ts.strftime("%Y:%m:%d %H:%M:%S"))


def process_dir(dir_name):
    LOG.debug("Scanning directory '%s'...", dir_name)

    # exiftool does not support updating video files
    pattern = re.compile(
        r"^WhatsApp Image (?P<timestamp>[^\(]+)( \(\d+\))?\.jpeg$")

    for file_name in listdir(dir_name):
        match = pattern.match(file_name)
        if not match:
            LOG.warning("Skipping '%s': unrecognised file name.", file_name)
            continue

        if not isfile(join(dir_name, file_name)):
            LOG.warning("Skipping '%s': not a regular file.", file_name)
            continue

        try:
            timestamp = datetime.strptime(
                match.group("timestamp"), "%Y-%m-%d at %I.%M.%S %p")
        except ValueError:
            LOG.error("'%s': invalid timestamp.", file_name)
            continue

        update(dir_name, file_name, timestamp)


def setup_log(log_level):
    handler = StreamHandler()
    handler.setFormatter(ColoredFormatter(
        "%(log_color)s%(asctime)s - %(levelname)s - %(message)s"))
    LOG.addHandler(handler)
    LOG.setLevel(log_level)


def parse_args():
    parser = ArgumentParser(description="WhatsApp Timestamp Fix")
    parser.add_argument("directory", nargs='?', default=getcwd(),
                        help="path containing image and video files to fix")
    parser.add_argument("-d", "--debug", dest="log_level", default=INFO,
                        action="store_const", const=DEBUG,
                        help="enable debug logging")
    return parser.parse_args()


def main():
    args = parse_args()
    setup_log(args.log_level)

    try:
        process_dir(args.directory)
    except FileNotFoundError as exc:
        LOG.error("exiftool not found: %s", exc)
        return 1
    except CalledProcessError as exc:
        LOG.error("Failed to run exiftool: %s; %s", exc, exc.stderr)
        return 2

    return 0


if __name__ == '__main__':
    sys.exit(main())
