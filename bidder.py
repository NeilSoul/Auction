#!usr/bin/env python
## TODO timeout refer to capacity
import os
import threading
import subprocess
import time
from Queue import PriorityQueue
import argparse
import setting
import message
import transport
import log
from parser import parse_m3u8
from bidder_core import BidderCore
from bidder_player import BidderPlayer

class BidderProtocol(message.Protocol):
	def __init__(self, factory):
		self.factory = factory

	''' bidder server callback '''
	def data_received(self, data, ip):
		# get peer info
		try:
			inst, info = data.split(':',1)
		except:
			return
		# parse data
		if inst == 'AUCTION':# receive an auction
			self.factory.bid(ip, info)
		elif inst == 'WIN':# win a bid
			self.factory.send_task(ip, info)

class TransportProtocol(transport.Protocol):
	def __init__(self, factory):
		self.factory = factory
	''' bidder server callback '''
	def receive_successed(self, index, list, address):
		ip = address[0]
		data = b''.join(list)
		self.factory.receive_trunk(ip, int(index), data)

	def receive_failed(self, index, list, address):
		ip = address[0]
		self.factory.fail_trunk(ip, int(index))
		

class Bidder(object):
	def __init__(self, peername, url, silent, bidder_params):
		# INIT properties
		self.peername = peername
		self.silent = silent
		self.streaming_url = url
		self.bidder_params = bidder_params
		self.fname_of_buffer = setting.PLAYER_BUFFER
		self.command_of_player = setting.PLAYER_COMMAND
		# bidder message server
		self.message_server  = message.MessageServer(
			setting.UDP_HOST, 
			setting.UDP_BID_PORT, 
			BidderProtocol(self))
		# bidder sender
		self.message_client = message.MessageClient(
			bidder_params['broadcast'],
			setting.UDP_AUCTION_PORT,
			message.Protocol())
		# transport center
		self.transport_center = transport.TransportServer(
			setting.TRP_HOST,
			setting.TRP_PORT,
			TransportProtocol(self))
		# player
		self.player = BidderPlayer(self)
		# log center
		self.logger = log.LogClient(peername, bidder_params['broadcast'])
		self.logger.add_peer(peername)
		

	""" Bidder(receiver, player) Life Cycle """
	def start(self):
		self.running = 1
		self.prepare()
		self.player.play()
		self.message_server.start()
		self.message_client.start()
		self.transport_center.start()
		

	def join(self):
		self.message_server.join()
		self.message_client.join()
		self.transport_center.join()

	def close(self):
		self.message_server.close()
		self.message_client.close()
		self.transport_center.close()
		self.player.close()
		self.running = 0
		self.task_timeout_cond.acquire()
		self.task_timeout_cond.notify()
		self.task_timeout_cond.release()

	def prepare(self):
		self.player.prepare2play()
		# the index of which trunk is ready to write into buffer  
		self.ready_index = 0
		# wait for auction : priority queue [segment number]
		self.auction_waiting_queue = PriorityQueue()
		for i in range(self.player.get_segment_number()):
			self.auction_waiting_queue.put(i)
		# wait for retrieve : dictionary (index:time)
		self.retrieving = {}
		# retrieved : dictionary (index:data)
		self.retrieved = {}
		self.task_cond = threading.Condition()
		threading.Thread(target=self.task_loop, args=(1.0, )).start()
		# timeout protection
		self.task_timeout_cond = threading.Condition()
		threading.Thread(target=self.task_timeout, args=(setting.AUCTIONEER_DOWNLOAD_TIMEOUT,)).start()
		# core
		self.core = BidderCore(self, self.bidder_params)

	def buffer_size(self):
		buffer_in_player = self.player.get_buffer()
		buffer_in_auction = self.player.get_segment_duration() * (len(self.retrieved) + len(self.retrieving))
		return buffer_in_player + buffer_in_auction

	""" Bid Factory.
	bid : bid for auction.
	send task : send segment task for auction.
	"""
	def bid(self, ip, auction):
		bid_pack = self.core.bid2auction(auction)
		if bid_pack:
			# unpack
			auction_peer, auction_index, bid = bid_pack
			# logging
			self.logger.bid_send(self.peername, auction_peer, auction_index, self.buffer_size(), bid)
			# response
			bid_info = ','.join([auction_index, str(bid)])
			self.message_client.sendto(ip, ':'.join(['BID', bid_info]))

	def send_task(self, ip, info):
		segment_allocated, rate = map(lambda a:int(a), info.split(','))
		self.core.update_previous(rate)
		while segment_allocated > 0 and not self.auction_waiting_queue.empty():
			index = self.auction_waiting_queue.get()
			task_url = self.player.get_segment_url(index, rate)
			print '[sended  ]No.',index,' rate = ', float(rate)/1024/1024 
			# send it to bidder
			self.retrieving[index] = time.time()
			self.message_client.sendto(ip, 'TASK:'+str(index)+','+task_url)
			segment_allocated = segment_allocated - 1

	""" Transport Factory """
	def receive_trunk(self, ip, index, data):
		print '[received]No.', index, ', size =', round(float(len(data))/1024/128,3), '(mb), buffer =', self.buffer_size(),'(s)'
		# discard wild data
		if not index in self.retrieving: 
			return
		del self.retrieving[index]
		# retrieve thread safe
		self.task_cond.acquire()
		self.retrieved[index] = data
		self.task_cond.notify()
		self.task_cond.release()
		

	def fail_trunk(self, ip, index):
		if not index in self.retrieving: #wild data
			return
		del self.retrieving[index]
		self.auction_waiting_queue.put(index)

	""" Task """
	def task_timeout(self, timeout):
		while self.running:
			now = time.time()
			for index in self.retrieving:#TODO thread safe
				if self.retrieving[index] - now > timeout:
					del self.retrieving[index]
					self.auction_waiting_queue.put(index)
			#time.sleep(timeout)
			self.task_timeout_cond.acquire()
			self.task_timeout_cond.wait(timeout)
			self.task_timeout_cond.release()

	def task_loop(self, timeout):
		while self.running:
			self.task_cond.acquire()
			while self.running and not self.ready_index in self.retrieved:
				self.task_cond.wait(timeout)
			if not self.running:
				break
			if self.ready_index in self.retrieved:
				self.player.segment_received(self.ready_index, self.retrieved[self.ready_index])
				del self.retrieved[self.ready_index]
				self.ready_index = self.ready_index + 1
			self.task_cond.release()

def parse_args():
	parser = argparse.ArgumentParser(description='Bidder')
	parser.add_argument('-p','--peer', required=False, default='Peer', help='name of peer')
	parser.add_argument('-u','--url', required=False, default=setting.PLAYER_DEFAULT_URL, help='url to play')
	parser.add_argument('-s','--silent', action='store_true', help='not play video actually')
	parser.add_argument('-t','--theta', default=setting.BIDDER_BASIC_TH, type=float, help='bidder preference theta')
	parser.add_argument('-q','--quality', default=setting.BIDDER_K_QV, type=float, help='bidder quality coefficient')
	parser.add_argument('-b','--buffer', default=setting.BIDDER_K_BUF, type=float, help='bidder buffer coefficient')
	parser.add_argument('-e','--ktheta', default=setting.BIDDER_K_THETA, type=float, help='bidder k^theta coefficient')
	parser.add_argument('-r','--kbr', default=setting.BIDDER_K_BR, type=float, help='bidder k^br coefficient')
	parser.add_argument('-m','--mbuffer', default=setting.BIDDER_MAX_BUF, type=float, help='bidder max buffer')
	parser.add_argument('-k','--kcapacity', default=1.0, type=float, help='bidder capacity coefficient')
	parser.add_argument('-a', '--broadcast', default=setting.UDP_BROADCAST, help='udp broadcast address')
	args = parser.parse_args()
	bidder_params = {}
	bidder_params['theta'] = args.theta
	bidder_params['kqv'] = args.quality
	bidder_params['kbuf'] = args.buffer 
	bidder_params['ktheta'] = args.ktheta
	bidder_params['kbr'] = args.kbr
	bidder_params['mbuf'] = args.mbuffer
	bidder_params['kcapacity'] = args.kcapacity
	bidder_params['broadcast'] = args.broadcast
	return args.peer, args.url, args.silent, bidder_params

if __name__ == "__main__":
	peer, url, silent, bidder_params = parse_args()
	bidder  = Bidder(peer, url, silent, bidder_params)
	bidder.start()
	try:
		while True:
			command = raw_input().lower()
			if not command or command == 'exit':
				break
	except KeyboardInterrupt:
		pass
	bidder.close()
	bidder.join()