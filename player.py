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
    def __init__(self, player, url, buflist, idx_buf):
        self.player = player
        o = urlparse(url)
        self.request = REQUEST_TEMPLATE % (o.path, o.netloc)
        self.buflist = buflist
        self.idx_buf = idx_buf

        # use a list and join it at last for efficiency
        self.buf = []

    def connection_made(self, transport):
        transport.write(self.request.encode())

    def data_received(self, data):
        self.buf.append(data)

    def connection_lost(self, _):
        # strip HTTP header
        self.buflist[self.idx_buf] = b''.join(self.buf).split(b'\r\n', 1)[1]
        writer = threading.Thread(target=self.player.write_file)
        writer.start()


class DirectDownloader(Downloader):
    def connection_made(self, transport):
        logging.info("Downloading segment %d directly ..." % self.idx_buf)
        Downloader.connection_made(self, transport)

    def connection_lost(self, _):
        logging.info("Download completed.")
        if not self.player.check_complete():
            asyncio.Task(self.player.direct_dl())
        Downloader.connection_lost(self, _)


class ProxyDownloader(Downloader):
    def connection_made(self, transport):
        peername = transport.get_extra_info("peername")
        logging.info("Downloading segment %d from %s..."
                     % (self.idx_buf, peername[0]))
        Downloader.connection_made(self, transport)

    def connection_lost(self, _):
        logging.info("Download completed.")
        Downloader.connection_lost(self, _)


class Player(asyncio.Protocol):
    def __init__(self, loop, infolist):
        self.loop = loop
        self.infolist = infolist
        self.idx_stack = deque(range(len(infolist)))
        self.idx_pending = deque()
        self.buflist = [None] * len(infolist)

        self.write_idx = 0
        self.writing = False

        # start with the lowest bitrate
        self.rate = sorted(infolist[0][1].keys())[0]

    def connection_made(self, transport):
        self.transport = transport
        logging.info("Connected to server.")
        asyncio.Task(self.direct_dl())

    def data_received(self, data):
        data = data.decode()
        if data == "IDLE":
            if not self.idx_pending:
                self.idx_pending.append(self.idx_stack.popleft())
            self.transport.write(repr(infolist[self.idx_pending[0]]).encode())
        elif data == "FAILURE":
            self.idx_stack.appendleft(self.idx_pending.popleft())
        else:
            # success
            proxy_ip, rate_str = data.split(',')[1:]
            self.rate = eval(rate_str)
            asyncio.Task(self.proxy_dl(proxy_ip))

    @asyncio.coroutine
    def proxy_dl(self, proxy_ip):
        idx = self.idx_pending.popleft()
        url = self.infolist[idx][1][self.rate]
        yield from self.loop.create_connection(
            lambda: ProxyDownloader(self, url, self.buflist, idx),
            proxy_ip, PROXY_PORT
        )
        self.check_complete()

    @asyncio.coroutine
    def direct_dl(self):
        idx = self.idx_stack.popleft()
        url = self.infolist[idx][1][self.rate]
        try:
            host, port_str = urlparse(url).netloc.rsplit(':', 1)
            port = int(port_str)
        except:
            host, port = urlparse(url).netloc, 80
        yield from self.loop.create_connection(
            lambda: DirectDownloader(self, url, self.buflist, idx),
            host, port
        )

    def check_complete(self):
        if not self.idx_stack:
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

                    # first segment buffered, start playing
                    if self.write_idx == 0:
                        player = threading.Thread(target=self.play)
                        player.start()

                    self.write_idx += 1
                    if self.write_idx == len(self.buflist):
                        break
            self.writing = False

    def play(self):
        subprocess.run(PLAYER_CMD.split() + [BUFFER_PATH],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) == 1:
        print("No input url.")
        exit()
    try:
        os.remove(BUFFER_PATH)
    except:
        pass
    infolist = parse_m3u8(sys.argv[1])
    loop = asyncio.get_event_loop()
    # loop.set_debug(True)
    coro = loop.create_connection(lambda: Player(loop, infolist),
                           "127.0.0.1", PLAYER_PORT)
    loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()
