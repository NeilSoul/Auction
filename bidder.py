#!usr/bin/env python
import setting
import message
import transport

class BidderProtocol(message.Protocol):
	def __init__(self, factory):
		self.factory = factory

	def data_received(self, data, address):
		# get peer info
		ip = address[0]
		try:
			inst, info = data.split(':',1)
		except:
			return
		# parse data
		if inst == 'AUCTION':# receive an auction
			self.factory.bid(ip, info)
		elif inst == 'WIN':# win a bid
			index,url = info.split(',',1)
			self.factory.win(ip, eval(index), url)

class SenderProtocol(transport.Protocol):
	def __init__(self, factory):
		self.factory = factory

	def on_send_success(self, index):
		print 'transported', index

	def on_send_failure(self, index):
		print 'transported error', index

class Bidder(object):
	def __init__(self):
		self.message_center  = message.Message(
			setting.MSG_HOST, 
			setting.BID_PORT, 
			setting.MSG_BROADCAST, 
			setting.AUCTION_PORT, 
			BidderProtocol(self))
		self.sender = transport.Sender(
			setting.TRP_PORT,
			SenderProtocol(self))
		# mark if idle status
		self.idle = True

	""" Life Cycle
	start->join->close.
	"""
	def start(self):
		self.message_center.start()

	def join(self):
		self.message_center.join()

	def close(self):
		self.message_center.close()

	""" Bid Factory.
	auction : broadcast an auction.
	"""
	def bid(self, ip, info):
		if self.idle:
			self.message_center.sendto(ip, 'BID:i want to bid.')

	def win(self, ip, index, url):
		self.idle = False
		self.sender.transport(ip, index, url)
		self.idle = True


if __name__ == "__main__":
	bidder  = Bidder()
	bidder.start()
	try:
		while True:
			command = raw_input().lower()
			if not command:
				break
			if command == 'exit':
				break
	except KeyboardInterrupt:
		pass
	bidder.close()
	bidder.join()