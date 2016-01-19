import asyncio
import logging
import re
from algorithm import utility, cost


CONTROL_PORT = 7000
PLAYER_PORT = 7001
PROXY_PORT = 7002
BC_INTERVAL = 1.0


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
        """Receive stream info, start bid."""
        self.factory.bid(*eval(data.decode()))

    def connection_lost(self, _):
        self.factory.player = None
        self.factory.idle = True
        self.factory.broadcast()
        logging.info("Player disconnected.")


class Control(asyncio.Protocol):
    """Handle a single connection from/to a peer."""
    def __init__(self, factory):
        self.factory = factory

    def connection_made(self, transport):
        self.transport = transport
        self.factory.peers.append(self)
        self.peername = transport.get_extra_info("peername")
        logging.info("Connected to peer %s." % self.peername[0])

    def data_received(self, data):
        data = data.decode()
        if data == "FAILURE":
            logging.info("Bid failed.")
            self.factory.write_player(data)
        elif data == "IDLE":
            self.factory.auctioneer = self
            self.factory.write_player(data)
        elif data.startswith("SUCCESS"):
            logging.info("Bid succeeded.")
            success, payment = data.split(':')
            # TODO: billing system
            msg = ','.join((success, self.peername[0], str(self.factory.rate)))
            self.factory.write_player(msg)
        else:
            # map this Control instance to its bid info
            self.factory.bid_info[self] = eval(data)

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
            self.factory.broadcast()


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

        self.peers = []
        self.player = None
        self.idle = True

        # TODO: integrate with initialization module
        self.coros = []
        self.coros.append(self.loop.create_server(lambda: Control(self),
                                                    "0.0.0.0", CONTROL_PORT))
        self.coros.append(self.loop.create_server(lambda: PlayerHandler(self),
                                               "127.0.0.1", PLAYER_PORT))
        self.coros.append(self.loop.create_server(lambda: Proxy(self),
                                                  "0.0.0.0", PROXY_PORT))

        self.reset_aunction()
        self.broadcast()

    def write_player(self, data):
        if self.player:
            self.player.transport.write(data.encode())

    def broadcast(self):
        """Broadcast 'IDLE' message to all peers at a certain interval."""
        if self.idle:
            if self.bid_info:
                self.auction()
            else:
                for peer in self.peers:
                    # TODO: device-specific parameters to cost function
                    peer.transport.write(b"IDLE")
                self.loop.call_later(BC_INTERVAL, self.broadcast)

    def bid(self, duration, rate_url_list):
        """Choose a bitrate and send the bid message.

        The message contains url, bitrate, duration, price,
        separated by ','.
        """
        logging.info("Starting bid.")
        rates = rate_url_list.keys()
        pref = lambda r: utility(r, duration) - cost(r, duration)
        self.rate = sorted(rates, key=pref, reverse=True)[0]
        url = rate_url_list[self.rate]
        price = utility(self.rate, duration)
        msg = repr((url, self.rate, duration, price))
        self.auctioneer.transport.write(msg.encode())

    def auction(self):
        """Choose a winner, inform all bidders, and reset auction state."""
        # each value is (url, bitrate, duration, price)
        info = self.bid_info
        logging.info("Received bid from %d peers." % len(info))
        score = lambda bidder: info[bidder][3] - cost(*info[bidder][1:3])
        bidders = info.keys()
        if len(bidders) == 1:
            winner = second = list(bidders)[0]
        else:
            winner, second = sorted(bidders, key=score, reverse=True)[:2]
        payment = score(second) + cost(*info[winner][1:3])
        for bidder in bidders:
            if bidder is winner:
                bidder.transport.write(("SUCCESS:" + str(payment)).encode())
            else:
                bidder.transport.write(b"FAILURE")
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
