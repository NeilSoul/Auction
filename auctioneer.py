#!usr/bin/env python
"""
TODO, retrieved time out.
	, transport time out.
"""
import threading
import time
import setting
import message
import transport
import log

""" Auctioneer(Downloader)
idle --> auction --> decide --> receive task --> downloading task -> idle --> ...
                 --> not yet --> waiting --> idle --> ...
"""
class AuctionProtocol(message.Protocol):

	def __init__(self, factory):
		self.factory = factory
	''' auction server callback '''
	def data_received(self, data, ip):
		try:
			inst, info = data.split(':',1)
		except:
			return
		# parse data
		if inst == 'BID':
			self.factory.receive_bid(ip, info)
		if inst == 'TASK':
			threading.Thread(target=self.factory.receive_task, args=(ip, info)).start()

class TransportProtocol(transport.Protocol):

	def __init__(self, factory):
		self.factory = factory
	''' downloader sending callback '''
	def send_successed(self, index):
		pass
	def send_failed(self, index):
		pass

class Auctioneer(object):

	def __init__(self, code):
		# auction message server
		self.message_server  = message.MessageServer(
			setting.UDP_HOST, 
			setting.UDP_AUCTION_PORT, 
			AuctionProtocol(self))
		# auction sender
		self.message_client = message.MessageClient(
			setting.UDP_BROADCAST,
			setting.UDP_BID_PORT,
			message.Protocol())
		# transport center
		self.transport = transport.TransportClient(
			setting.TRP_PORT,
			TransportProtocol(self))
		# log center
		self.logger = log.LogClient(code)
		# status
		self.code = code
		self.status = 'idle'

	""" Auctioneer Life Cycle"""
	def start(self):
		self.message_server.start()
		self.message_client.start()
		self.running = True
		self.lifecycle = threading.Thread(target=self.run)
		self.lifecycle.start()
		

	def join(self):
		self.message_server.join()
		self.message_client.join()
		self.lifecycle.join()

	def close(self):
		self.message_server.close()
		self.message_client.close()
		self.running = False

	def run(self):
		# timeout mechanism
		while self.running:
			if self.status == 'idle':
				self.auction()
			elif self.status == 'auction':
				time.sleep(0.1) #TODO signal
				if not self.status == 'task':
					#time out
					self.status = 'idle'

	""" Auction Factory.
	auction : make an auction.
	receive_bid : receive a bid.
	"""
	def auction(self):
		# logging
		self.logger.send('auction created.')
		# bid {ip:bid}
		self.bids = {}
		self.status = 'auction'
		self.message_client.broadcast('AUCTION:cost function of '+self.code)
		time.sleep(0.1)
		if self.bids:
			for ip in self.bids:
				choice = ip
			self.decide_bid(ip, self.bids[ip])

	def receive_bid(self, ip, bid):
		if self.status == 'auction':
			self.bids[ip] = bid

	def decide_bid(self, ip, bid):
		# logging
		self.logger.send('bid decided.')
		# notify the winner
		self.message_client.sendto(ip, 'WIN:'+self.code)

	def receive_task(self, ip, task):
		if not self.status == 'auction':
			return
		# logging
		self.logger.send('bid tasking.')
		self.status = 'task'
		index, url = task.split(',',1)
		self.transport.transport(ip, index, url)
		self.status = 'idle'

if __name__ == "__main__":
	auctioneer  = Auctioneer('A')
	auctioneer.start()
	try:
		while True:
			command = raw_input().lower()
			if not command:
				break
			if command == 'exit':
				break
	except KeyboardInterrupt:
		pass
	auctioneer.close()
	auctioneer.join()