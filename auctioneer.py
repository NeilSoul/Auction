#!usr/bin/env python
import threading
import time
import argparse
import setting
import message
import transport
import log
from Queue import Queue
from auctioneer_core import AuctioneerCore

""" Auctioneer(Downloader)
Description:
	Auctioneers also role of downloaders. They broadcast auctions when idle.
Life Cycle:
	idle --> auction | waiting--> decide | timeout--> receive tasks --> downloading tasks -> idle --> ...
	                 --> not yet | timeout --> idle --> ...
"""
class AuctionProtocol(message.Protocol):

	def __init__(self, factory):
		self.factory = factory
	''' auction server callback '''
	def data_received(self, data, ip):
		# parse instruction
		try:
			inst, info = data.split(':',1)
		except:
			return
		# divide instructions
		if inst == 'BID':
			self.factory.receive_bid(ip, info)
		if inst == 'TASK':
			self.factory.receive_task(ip,info)

class TransportProtocol(transport.Protocol):

	def __init__(self, factory):
		self.factory = factory
	''' downloader sending callback '''
	def send_successed(self, index):
		pass
	def send_failed(self, index):
		pass

class Auctioneer(object):

	def __init__(self, peername, segmentnumber):
		# propertys
		self.peername = peername
		self.segment_number = segmentnumber
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
		self.logger = log.LogClient(peername)
		# algorithm core
		self.core = AuctioneerCore(self)

	""" Auctioneer Life Cycle"""
	def start(self):
		print self.peername, 'running...'
		# init
		self.running = 1
		self.transport_queue = Queue()
		self.bids = {}# bids {ip:bid}
		self.tasks = {}# tasks {ip:task number}
		# launch
		self.message_server.start()
		self.message_client.start()
		threading.Thread(target=self.auction_loop).start() # join ignore
		

	def join(self):
		self.message_server.join()
		self.message_client.join()

	def close(self):
		self.message_server.close()
		self.message_client.close()
		self.running = 0


	def auction_loop(self):
		# timeout mechanism
		while self.running:
			try:
				ip,task = self.transport_queue.get(timeout=0.3)
				if self.tasks[ip] > 0:
					index, url = task.split(',',1)
					size, duration = self.transport.transport(ip, index, url)
					capacity = size/duration/1024/1024 if duration > 0 else setting.AUCTIONEER_DEFAULT_CAPACITY
					self.core.estimate_capacity(round(capacity,3))
					self.tasks[ip] = self.tasks[ip] - 1
					#logging 
					self.logger.transport_complete(ip, index, size, duration)
					print '[task completed]', index, url
			except:
				#Time out
				self.auction()
				time.sleep(0.1)
				self.bid_decide()


	""" Auction Factory.
	auction : make an auction.
	receive_bid : receive a bid.
	"""
	def auction(self):
		# logging
		self.logger.auction_broadcast(self.peername, self.segment_number, self.core.capacity, self.core.cti, self.core.cda, self.core.cwda)
		self.bids.clear()
		auction_info = ':'.join(['AUCTION',self.core.auction_message()])
		self.message_client.broadcast(auction_info)

	def receive_bid(self, ip, bid):
		self.bids[ip] = bid

	def bid_decide(self):
		if not self.bids:#receive no bids
			return
		self.tasks.clear()
		# dict {ip : (segments, rate, payment)}
		allocs = self.core.select_bid(self.bids)
		# notify the winner
		for ip in allocs:
			self.tasks[ip] = allocs[ip][0]
			alloc_result =  ','.join([str(allocs[ip][0]), str(allocs[ip][1])])
			self.message_client.sendto(ip, ':'.join(['WIN', alloc_result]))
			# logging
			self.logger.auction_decide(self.peername, ip, allocs[ip][0], allocs[ip][1], allocs[ip][2])
		# logging
		self.logger.decide_complete(self.peername)

	def receive_task(self, ip, task):
		self.transport_queue.put((ip,task))
		

def parse_args():
	parser = argparse.ArgumentParser(description='Auctioneer')
	parser.add_argument('--peer', required=False, default='Peer', help='name of peer')
	parser.add_argument('--segment', type=int, default=setting.AUCTIONEER_SEG_NUM, help='segments per auction')
	return parser.parse_args()

if __name__ == "__main__":
	args = parse_args()
	auctioneer  = Auctioneer(args.peer, args.segment)
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