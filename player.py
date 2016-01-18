import sys
import time
import threading
import subprocess
import logging
from urllib.request import urlopen
from m3u8_parser import parse_m3u8


PLAYER_CMD = "mplayer"
BUFFER_DIR = "tmp_video"


def direct_dl(url):
    logging.info("directly downloading " + url)
    return urlopen(url).read()


def request_dl(url):
    """Request a connected node to fetch the url."""
    # TODO
    pass


def download(infolist, bufdir):
    """Download the video segments, choosing routes and bitrates."""
    global first_seg_ready
    # TODO: always prefer the lowest bw for now
    with open(bufdir, "ab") as out:
        preferred_bw = sorted(infolist[0][1].keys())[0]
        for item in infolist:
            # TODO: choose route
            out.write(direct_dl(item[1][preferred_bw]))
            first_seg_ready = True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) == 1:
        print("No input url.")
        exit()
    infolist = parse_m3u8(sys.argv[1])
    first_seg_ready = False
    downloader = threading.Thread(target=download, args=(infolist, BUFFER_DIR))
    downloader.start()

    # Wait for the buffer to be ready and start streaming (not robust now)
    while True:
        if first_seg_ready:
            break
        else:
            time.sleep(1)
    subprocess.run(PLAYER_CMD.split() + [BUFFER_DIR])
