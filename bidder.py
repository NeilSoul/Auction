#!usr/bin/env python
## TODO timeout refer to capacity
import os
import threading
import subprocess
import time
from Queue import PriorityQueue
import argparse
import setting
import transport
from discovery import Broadcaster
from message import MessageProtocol
from message import Message
from parser import parse_m3u8
from bidder_core import BidderCore
from bidder_player import BidderPlayer

#TODO logger is not a known instance to bidder

class BidderProtocol(MessageProtocol):

	def __init__(self, factory):
		self.factory = factory

	def on_msg_from_peer(self, data, peer):
		# get peer info
		try:
			inst, info = data.split(':',1)
		except:
			return
		# parse data
		if inst == 'AUCTION':# receive an auction
			self.factory.bid(peer, info)
		elif inst == 'WIN':# win a bid
			self.factory.send_task(peer, info)

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
	def __init__(self, bidder_params, logger):
		# INIT properties
		self.bidder_params = bidder_params
		self.peername = bidder_params['peer']
		self.silent = bidder_params['silent']
		self.streaming_url = bidder_params['url']
		self.buffer_folder = setting.BUFFER_DIR
		# discovery center
		self.discovery_center = Broadcaster(
			bidder_params['broadcast'], 
			setting.DIS_BID_PORT)
		# message center
		self.message_center = Message(
			setting.MSG_HOST, 
			setting.MSG_BID_PORT, 
			setting.MSG_AUC_PORT, 
			BidderProtocol(self))
		# transport center
		self.transport_center = transport.TransportServer(
			setting.TRP_HOST,
			setting.TRP_PORT,
			TransportProtocol(self))
		# player
		self.player = BidderPlayer(self)
		# log center
		self.logger = logger #self.logger = log.LogClient(peername, bidder_params['broadcast'])
		self.running = 0
		
	""" Bidder(receiver, player) Life Cycle """
	def run(self):
		print ''
		print '### Bidder', self.peername, '( kcapacity = ', self.bidder_params['kcapacity'],') running...'
		print ''
		self.running = 1
		self.prepare()
		self.player.play()
		self.discovery_center.run()
		self.message_center.run()
		self.transport_center.start()
		

	def join(self):
		self.transport_center.join()

	def close(self):
		self.discovery_center.close()
		self.message_center.close()
		self.transport_center.close()
		self.player.close()
		self.running = 0
		self.task_timeout_cond.acquire()
		self.task_timeout_cond.notify()
		self.task_timeout_cond.release()
		print ''
		print '### Bidder', self.peername, 'stopped'
		print ''

	def prepare(self):
		self.player.prepare2play()
		# the index of which trunk is ready to write into buffer  
		self.ready_index = 0
		# wait for auction : priority queue [segment number]
		self.auction_waiting_queue = PriorityQueue()
		for i in range(self.player.get_segment_number()):
			self.auction_waiting_queue.put(i)
		# wait for retrieve : dictionary { index: (rate,time) }
		self.retrieving = {}
		# retrieved : dictionary  { index:(rate,data) }
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
			#self.logger.log('B', [self.peername, auction_peer, auction_index, self.buffer_size(), bid])
			# response
			bid_info = ','.join([auction_index, str(bid)])
			self.message_center.sendto(ip, ':'.join(['BID', bid_info]))

	def send_task(self, ip, info):
		segment_allocated, rate = map(lambda a:int(a), info.split(','))
		self.core.update_previous(rate)
		while segment_allocated > 0 and not self.auction_waiting_queue.empty():
			index = self.auction_waiting_queue.get()
			task_url = self.player.get_segment_url(index, rate)
			f_rate = float(rate)/1024/1024  
			print '[B     sended] No.%d, rate=%0.2f(mbps)' % (index, f_rate)
			# send it to bidder
			self.retrieving[index] = (f_rate, time.time())
			self.message_center.sendto(ip, 'TASK:'+str(index)+','+task_url)
			segment_allocated = segment_allocated - 1

	""" Transport Factory """
	def receive_trunk(self, ip, index, data):
		print '[B   received] No.%s, size=%0.2f(mb), buffer=%0.2f(s)' % (index, float(len(data))/1024/128, self.buffer_size())
		# discard wild data
		if not index in self.retrieving: 
			return
		# retrieve thread safe
		self.task_cond.acquire()
		self.retrieved[index] = (self.retrieving[index][0], data)
		del self.retrieving[index]
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
				if self.retrieving[index][1] - now > timeout:
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

#UNIT TEST

from controller import Slave

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
	# pack to dict
	bidder_params = {}
	bidder_params['peer'] = args.peer
	bidder_params['url'] = args.url
	bidder_params['silent'] = args.silent
	bidder_params['theta'] = args.theta
	bidder_params['kqv'] = args.quality
	bidder_params['kbuf'] = args.buffer 
	bidder_params['ktheta'] = args.ktheta
	bidder_params['kbr'] = args.kbr
	bidder_params['mbuf'] = args.mbuffer
	bidder_params['kcapacity'] = args.kcapacity
	bidder_params['broadcast'] = args.broadcast
	return bidder_params

if __name__ == "__main__":
	# params
	bidder_params = parse_args()
	# logger
	logger = Slave(auctioneer_params['peer'])
	logger.run()
	logger.introduce()
	# bidder
	bidder  = Bidder(bidder_params, logger)
	bidder.run()
	try:
		while True:
			command = raw_input().lower()
			if not command or command == 'exit':
				break
	except KeyboardInterrupt:
		pass
	bidder.close()
	logger.close()

