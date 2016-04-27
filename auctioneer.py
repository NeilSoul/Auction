#!usr/bin/env python
# -*- coding: UTF-8 -*-

import threading
import time
import argparse
import setting
import transport
from Queue import Queue
from discovery import ListenerProtocol
from discovery import Listener
from message import MessageProtocol
from message import Message
from auctioneer_core import AuctioneerCore

""" Auctioneer(Downloader)
Description:
	Auctioneers also role of downloaders. They broadcast auctions when idle.
Life Cycle:
	idle --> auction | waiting--> decide | timeout--> receive tasks --> downloading tasks -> idle --> ...
	                 --> not yet | timeout --> idle --> ...
"""
class AuctionProtocol(MessageProtocol):

	def __init__(self, factory):
		self.factory = factory

	def on_msg_from_peer(self, data, peer):
		# parse instruction
		try:
			inst, info = data.split(':',1)
		except:
			return
		# divide instructions
		if inst == 'BID':
			self.factory.receive_bid(peer, info)
		if inst == 'TASK':
			self.factory.receive_task(peer,info)

class Auctioneer(ListenerProtocol):

	def __init__(self, auctioneer_params, logger):
		# propertys
		self.auctioneer_params = auctioneer_params
		self.peername = auctioneer_params['peer']
		self.delay = auctioneer_params['delay'] if auctioneer_params['delay'] > 1.0 else 1.0
		# discovery center
		self.discovery_center = Listener(
			setting.DIS_HOST,#auctioneer_params['broadcast'], 
			setting.DIS_BID_PORT,
			self)
		# message center
		self.message_center = Message(
			setting.MSG_HOST, 
			setting.MSG_AUC_PORT, 
			setting.MSG_BID_PORT, 
			AuctionProtocol(self))
		# transport center
		self.transport = transport.TransportClient(
			setting.TRP_PORT,
			transport.Protocol())
		# log center
		self.logger = logger #self.logger = log.LogClient(peername, self.auctioneer_params['broadcast'])
		# algorithm core
		self.core = AuctioneerCore(self, self.auctioneer_params)
		self.running = 0

	""" Auctioneer Life Cycle"""
	def run(self):
		print ''
		print '### Auctioneer', self.peername, '( delay = ', self.auctioneer_params['delay'],') running...'
		print ''
		# INIT
		self.running = 1
		self.transport_queue = Queue()
		self.bids = {}# bids {ip:bid}
		self.tasks = {}# tasks {ip:task number}
		self.auction_index = 0
		# launch
		self.discovery_center.run()
		self.message_center.run()
		threading.Thread(target=self.auction_loop).start() # join ignore

	def close(self):
		self.discovery_center.close()
		self.message_center.close()
		self.running = 0
		print ''
		print '### Auctioneer', self.peername, 'stopped.'
		print ''


	def auction_loop(self):
		# timeout mechanism
		while self.running:
			try:
				ip,task = self.transport_queue.get(timeout=0.3)
			except:
				#Time out
				self.auction()
				time.sleep(0.1)
				#repeated broadcast
				''' deprecated
				for i in range(3):
					self.auction()
					time.sleep(0.033)
				'''
				self.decide_auction()
			else:
				if not ip in self.tasks or self.tasks[ip] <= 0:
					continue
				index, url = task.split(',',1)
				size, duration, success = self.transport.transport(ip, index, url)
				size = float(size) / 1024 / 128 #bytes to mb
				#delay
				if self.delay > 1.0:
					#print 'delay', duration  * (self.delay - 1.0)
					time.sleep(duration * (self.delay - 1.0))
					duration = duration * self.delay
				capacity = size / duration if duration > 0 else self.auctioneer_params['capacity']
				self.core.estimate_capacity(capacity)
				self.tasks[ip] = self.tasks[ip] - 1
				if success:
					#logging 
					#self.logger.log('T', [ip, index, size, duration])#self.logger.transport_complete(ip, index, size, duration)
					print '[A  completed] No.%s, size=%0.2f(mb), capacity=%0.2f~%0.2f(mbps), url=%s, at %s' % (index, size, capacity, self.core.capacity, url, time.strftime("%H:%M:%S"))
				else:
					print '[A     failed] No.%s' % index
			


	""" Auction Factory.
	auction : make an auction.
	receive_bid : receive a bid.
	"""
	def auction(self):
		# logging
		'''
		self.logger.log('A', [
			self.peername, 
			self.auction_index,
			self.auctioneer_params['segment'], 
			self.core.capacity, 
			self.auctioneer_params['timecost'], 
			self.auctioneer_params['cellular'], 
			self.auctioneer_params['wifi']
			])'''
		# broadcast
		self.bids.clear()
		auction_info = self.core.auction_message(self.auction_index)
		for peer in self.discovery_center.peers.keys():
				self.message_center.sendto(peer, ':'.join(['AUCTION', auction_info]))

	def receive_bid(self, ip, bid):
		index, bid_details = bid.split(',',1)
		if int(index) == self.auction_index:
			self.bids[ip] = bid_details

	def decide_auction(self):
		if not self.bids:#receive no bids
			return
		# finish one auction
		self.auction_index += 1 # TODO thread safe ,dict size change when iteration
		self.tasks.clear()
		# dict {ip : (segments, rate, payment)}
		allocs = self.core.select_bid(self.bids)
		# notify the winner
		for ip in allocs:
			self.tasks[ip] = allocs[ip][0]
			alloc_result =  ','.join([str(allocs[ip][0]), str(allocs[ip][1])])
			self.message_center.sendto(ip, ':'.join(['WIN', alloc_result]))
			# logging
			#self.logger.log('D', [self.peername, self.auction_index-1, ip, allocs[ip][0], allocs[ip][1], allocs[ip][2]])
		# logging
		#self.logger.log('C', self.peername)#self.logger.decide_complete(self.peername)

	def receive_task(self, ip, task):
		self.transport_queue.put((ip,task))

#UNIT TEST

from controller import Slave		

def parse_args():
	parser = argparse.ArgumentParser(description='Auctioneer')
	parser.add_argument('-p', '--peer', required=False, default='Peer', help='name of peer')
	parser.add_argument('-s', '--segment', type=int, default=setting.AUCTIONEER_SEG_NUM, help='segments per auction')
	parser.add_argument('-c', '--capacity', type=float, default=setting.AUCTIONEER_DEFAULT_CAPACITY, help='initial capacity')
	parser.add_argument('-t', '--timecost', type=float, default=setting.AUCTIONEER_COST_TI, help='rebuffer time cost coefficient')
	parser.add_argument('-l', '--lte', type=float, default=setting.AUCTIONEER_COST_DA, help='lte cost coefficient')
	parser.add_argument('-w', '--wifi', type=float, default=setting.AUCTIONEER_COST_WDA, help='WiFi cost coefficient')
	parser.add_argument('-d', '--delay', type=float, default=1.0, help='delay of data transport.')
	parser.add_argument('-a', '--broadcast', default=setting.UDP_BROADCAST, help='udp broadcast address')
	args = parser.parse_args()
	auctioneer_params = {}
	auctioneer_params['peer'] = args.peer
	auctioneer_params['segment'] = args.segment
	auctioneer_params['capacity'] = args.capacity
	auctioneer_params['timecost'] = args.timecost
	auctioneer_params['cellular'] = args.lte
	auctioneer_params['wifi'] = args.wifi
	auctioneer_params['delay'] = args.delay
	auctioneer_params['broadcast'] = args.broadcast
	return auctioneer_params

if __name__ == "__main__":
	# params
	auctioneer_params = parse_args()
	# logger
	logger = Slave(auctioneer_params['peer'])
	logger.run()
	logger.introduce()
	# auctioneer
	auctioneer  = Auctioneer(auctioneer_params, logger)
	auctioneer.run()
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
	logger.close()