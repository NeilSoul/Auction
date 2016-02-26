import sys
import os
import asyncio
import threading
import subprocess
import logging
from collections import deque
from urllib.parse import urlparse
from m3u8_parser import parse_m3u8

from server import PROXY_PORT, PLAYER_PORT


PLAYER_CMD = "mplayer"
BUFFER_PATH = "tmp_video"

REQUEST_TEMPLATE = 'GET %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n'


class Downloader(asyncio.Protocol):

    def __init__(self, player):
        self.player = player
        # use a list and join it at last for efficiency
        self.buf = []

    def connection_made(self, transport):
        self.idx_buf = self.player.current_idx
        self.player.current_idx += 1
        url = self.player.infolist[self.idx_buf][self.player.rate]
        o = urlparse(url)
        request = REQUEST_TEMPLATE % (o.path, o.netloc)
        transport.write(request.encode())

    def data_received(self, data):
        self.buf.append(data)

    def connection_lost(self, _):
        # strip HTTP header
        self.player.buflist[self.idx_buf] = b''.join(
            self.buf).split(b'\r\n', 1)[1]
        writer = threading.Thread(target=self.player.write_file)
        writer.start()


class DirectDownloader(Downloader):

    def connection_made(self, transport):
        Downloader.connection_made(self, transport)
        logging.info("Downloading segment %d directly ..." % self.idx_buf)

    def connection_lost(self, _):
        logging.info("Download completed.")
        if not self.player.check_complete():
            asyncio.Task(self.player.direct_dl())
        Downloader.connection_lost(self, _)


class ProxyDownloader(Downloader):

    def connection_made(self, transport):
        Downloader.connection_made(self, transport)
        peername = transport.get_extra_info("peername")
        logging.info("Downloading segment %d from %s..."
                     % (self.idx_buf, peername[0]))

    def connection_lost(self, _):
        logging.info("Download of segment %d completed." % self.idx_buf)
        Downloader.connection_lost(self, _)


class Player(asyncio.Protocol):

    def __init__(self, loop, infolist):
        self.loop = loop
        self.infolist = infolist
        self.segment_count = len(infolist)
        self.current_idx = 0
        self.buflist = [None] * self.segment_count

        self.write_idx = 0
        self.writing = False

        self.bitrates = sorted(infolist[0].keys())
        # start with the lowest bitrate
        self.rate = self.bitrates[0]

    def connection_made(self, transport):
        self.transport = transport
        logging.info("Connected to server.")
        transport.write(repr(self.bitrates).encode())
        asyncio.Task(self.direct_dl())

    def data_received(self, data):
        data = data.decode()
        proxy_ip, rate_str = data.split(',')
        self.rate = eval(rate_str)
        asyncio.Task(self.proxy_dl(proxy_ip))

    @asyncio.coroutine
    def proxy_dl(self, proxy_ip):
        url = self.infolist[self.current_idx][self.rate]
        # does not take download failure into account
        yield from self.loop.create_connection(
            lambda: ProxyDownloader(self),
            proxy_ip, PROXY_PORT
        )
        self.check_complete()

    @asyncio.coroutine
    def direct_dl(self):
        url = self.infolist[self.current_idx][self.rate]
        try:
            host, port_str = urlparse(url).netloc.rsplit(':', 1)
            port = int(port_str)
        except:
            host, port = urlparse(url).netloc, 80
        yield from self.loop.create_connection(
            lambda: DirectDownloader(self),
            host, port
        )

    def check_complete(self):
        if self.current_idx == self.segment_count:
            logging.info("All segments started streaming.")
            self.transport.close()
            return True
        return False

    def write_file(self):
        if not self.writing:
            self.writing = True
            with open(BUFFER_PATH, 'ab') as f:
                while self.buflist[self.write_idx]:
                    f.write(self.buflist[self.write_idx])
                    self.buflist[self.write_idx] = None
                    logging.info("Segment %d ready to play." % self.write_idx)

                    # first segment buffered, start playing
                    if self.write_idx == 0:
                        player = threading.Thread(target=self.play)
                        player.start()

                    self.write_idx += 1
                    if self.write_idx == self.segment_count:
                        break
            self.writing = False

    def play(self):
        # does not need to actually run player for experiment purpose
        # subprocess.run(PLAYER_CMD.split() + [BUFFER_PATH],
        #                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info("Player started.")


if __name__ == "__main__":
    logfile = open("player.log", 'w')
    logging.basicConfig(stream=logfile, level=logging.INFO,
                        format="%(levelname)s: %(asctime)s; %(message)s")
    if len(sys.argv) == 1:
        print("No input url.")
        exit()
    try:
        os.remove(BUFFER_PATH)
    except:
        pass
    infolist_raw = parse_m3u8(sys.argv[1])
    # [(float, dict)] -> [dict]
    # assume each segment has equal duration
    infolist = [item[1] for item in infolist_raw]
    loop = asyncio.get_event_loop()
    # loop.set_debug(True)
    coro = loop.create_connection(lambda: Player(loop, infolist),
                                  "127.0.0.1", PLAYER_PORT)
    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()
