import asyncio
import logging
import re
import socket
import random
import string
from algorithm import utility, cost


CONTROL_PORT = 7000
PLAYER_PORT = 7001
PROXY_PORT = 7002
BROADCAST_IP = "192.168.11.255"
BROADCAST_IDLE_INTERVAL = 1.0


class PlayerHandler(asyncio.Protocol):
    """Handle a single connection from a player."""

    def __init__(self, factory):
        self.factory = factory

    def connection_made(self, transport):
        if not self.factory.player:
            self.transport = transport
            self.factory.player = self
            self.factory.idle = False
            logging.info("Player connected.")
        else:
            logging.error("Another player instance is running!")
            transport.close()

    def data_received(self, data):
        self.bitrates = eval(data.decode())

    def connection_lost(self, _):
        self.factory.player = None
        self.factory.idle = True
        self.factory.broadcast_idle()
        logging.info("Player disconnected.")


class UDPControl(asyncio.Protocol):
    """Handle a single connection from/to a peer."""

    def __init__(self, factory):
        self.factory = factory
        self.broadcast_addr = (BROADCAST_IP, CONTROL_PORT)
        self.rand_str = ''.join([random.choice(string.ascii_letters)
                                 for _ in range(10)])

    def connection_made(self, transport):
        self.factory.control = self
        self.transport = transport
        sock = transport.get_extra_info("socket")
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        logging.info("Listening UDP.")

    def datagram_received(self, data, addr):
        ip = addr[0]
        data = data.decode()
        if data == "FAILURE":
            logging.info("Bid failed.")
        elif data.startswith("IDLE"):
            if data.split(':')[1] != self.rand_str:
                logging.info("Received offer from %s" % ip)
                self.factory.auctioneer = ip
                if self.factory.player:
                    self.factory.bid(self.factory.player.bitrates)
        elif data.startswith("SUCCESS"):
            logging.info("Bid succeeded.")
            payment = data.split(':', 1)[1]
            # TODO: log payment
            msg = ','.join((ip, str(self.factory.rate)))
            self.factory.write_player(msg)
        elif data.startswith("BID"):
            # map this Control instance to its bid info
            self.factory.bid_info[ip] = eval(data.split(':', 1)[1])

    def broadcast_idle(self):
        self.transport.sendto(("IDLE:" + self.rand_str).encode(),
                              self.broadcast_addr)

    def sendto(self, data, ip):
        self.transport.sendto(data.encode(), (ip, CONTROL_PORT))

    def connection_lost(self, _):
        self.factory.peers.remove(self)
        logging.info("Disconnected from peer %s." % self.peername[0])


class HTTPClient(asyncio.Protocol):
    """Fetch video segment."""

    def __init__(self, proxy):
        self.proxy = proxy
        self.factory = proxy.factory

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        self.proxy.transport.write(data)

    def connection_lost(self, _):
        logging.info("Download completed.")
        self.proxy.transport.close()
        if not self.factory.player:
            self.factory.idle = True
            self.factory.broadcast_idle()


class Proxy(asyncio.Protocol):
    """Fetch video segment."""

    def __init__(self, factory):
        self.factory = factory

    def connection_made(self, transport):
        self.transport = transport
        self.factory.idle = False
        peername = transport.get_extra_info("peername")
        logging.info("Downloading for %s ..." % peername[0])

    @asyncio.coroutine
    def send(self, request):
        host = re.findall(r"Host:(?P<value>.*?)\r\n", request.decode())[0]\
            .lstrip()
        try:
            host, port_str = host.split(':')
            port = int(port_str)
        except:
            port = 80
        _, http_client = yield from self.factory.loop.create_connection(
            lambda: HTTPClient(self), host, port
        )
        http_client.transport.write(request)

    def data_received(self, data):
        asyncio.Task(self.send(data))


class Server:

    def __init__(self, loop):
        self.loop = loop

        self.control = None
        self.player = None
        self.idle = True

        self.coros = []
        self.coros.append(self.loop.create_datagram_endpoint(
            lambda: UDPControl(self), ("0.0.0.0", CONTROL_PORT)))
        self.coros.append(self.loop.create_server(lambda: PlayerHandler(self),
                                                  "127.0.0.1", PLAYER_PORT))
        self.coros.append(self.loop.create_server(lambda: Proxy(self),
                                                  "0.0.0.0", PROXY_PORT))

        self.reset_aunction()
        self.broadcast_idle()

    def write_player(self, data):
        if self.player:
            self.player.transport.write(data.encode())

    def broadcast_idle(self):
        """Broadcast 'IDLE' message to all peers at a certain interval."""
        if self.control is None:
            self.loop.call_later(BROADCAST_IDLE_INTERVAL, self.broadcast_idle)
        elif self.idle:
            if self.bid_info:
                # TODO: device-specific parameters to cost function
                self.auction()
            else:
                self.control.broadcast_idle()
                self.loop.call_later(BROADCAST_IDLE_INTERVAL,
                                     self.broadcast_idle)

    def bid(self, bitrates):
        """Choose a bitrate and send the bid message.

        The message starts with "BID:", followed by (bitrate, price).
        """
        logging.info("Starting bid.")
        pref = lambda r: utility(r, duration) - cost(r, duration)
        self.rate = sorted(bitrates, key=pref, reverse=True)[0]
        price = utility(self.rate)
        msg = repr((self.rate, price))
        self.control.sendto("BID:" + msg, self.auctioneer)

    def auction(self):
        """Choose a winner, inform all bidders, and reset auction state."""
        # each value is (bitrate, price)
        info = self.bid_info
        logging.info("Received bid from %d peers." % len(info))
        score = lambda bidder: info[bidder][1] - cost(info[bidder][0])
        bidders = info.keys()
        if len(bidders) == 1:
            winner = second = list(bidders)[0]
        else:
            winner, second = sorted(bidders, key=score, reverse=True)[:2]
        payment = score(second) + cost(info[winner][0])
        for bidder in bidders:
            if bidder is winner:
                self.control.sendto("SUCCESS:" + str(payment), bidder)
            else:
                self.control.sendto("FAILURE", bidder)
        logging.info("Aunction done.")
        self.reset_aunction()

    def reset_aunction(self):
        self.auctioneer = None
        self.bid_info = {}


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    logging.basicConfig(level=logging.INFO)
    server = Server(loop)
    for coro in server.coros:
        loop.run_until_complete(coro)
    loop.run_forever()
    loop.close()
