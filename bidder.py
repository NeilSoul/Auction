#!usr/bin/env python
## TODO timeout refer to capacity
import os
import threading
import subprocess
import time
from Queue import Queue
from Queue import PriorityQueue
import argparse
import setting
import message
import transport
import log
from parser import parse_m3u8
from bidder_core import BidderCore

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
		threading.Thread(target=self.factory.receive_trunk, args=(ip, int(index), data)).start()
	def receive_failed(self, index, list, address):
		ip = address[0]
		self.factory.fail_trunk(ip, int(index))
		

class Bidder(object):
	def __init__(self, peername, url, silent, bidder_params):
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
		# log center
		self.logger = log.LogClient(peername, bidder_params['broadcast'])
		self.logger.add_peer(peername)
		# other properties
		self.peername = peername
		self.silent = silent
		self.streaming_url = url
		self.bidder_params = bidder_params

	""" Bidder(receiver, player) Life Cycle """
	def start(self):
		self.running = 1
		self.prepare2play(self.streaming_url)
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
		self.running = 0
		self.retrieving_timeout_cond.acquire()
		self.retrieving_timeout_cond.notify()
		self.retrieving_timeout_cond.release()
		self.played_cond.acquire()
		self.played_cond.notify()
		self.played_cond.release()
		self.clear_player()

	""" Player Methods"""
	def prepare2play(self, url):
		print '[m3u8 parsing]...'
		self.descriptor_list = parse_m3u8(url)
		self.rate_list = sorted(self.descriptor_list[0][1].keys())
		# streaming parameters
		self.selected_rate = self.rate_list[0]
		self.last_index = len(self.descriptor_list) - 1
		self.average_duration = self.descriptor_list[0][0]
		self.max_rate = self.rate_list[-1]
		# wait for auction : priority queue
		self.wait_for_auction = PriorityQueue()
		for i in range(len(self.descriptor_list)):
			self.wait_for_auction.put(i)
		# wait for retrieve : dictionary (index:time)
		self.retrieving = {}
		# retrieved : dictionary (index:data)
		self.retrieved = {}
		# the index of which trunk is ready to write into buffer  
		self.bufferd_index = 0
		# status of player
		self.player_status = 'prepared'
		print 'duration', self.average_duration
		print 'rates', map(lambda r:float(r)/1024/1024, self.rate_list)
		# streaming engine
		self.played_queue = Queue() # [(index, bytes_of_data)]
		self.played_cond = threading.Condition()
		threading.Thread(target = self.streaming).start()
		# timeout protection
		self.retrieving_timeout_cond = threading.Condition()
		threading.Thread(target=self.time_trunk, args=(setting.AUCTIONEER_DOWNLOAD_TIMEOUT,)).start()
		# clear player
		self.clear_player()
		# core
		self.core = BidderCore(self, self.bidder_params)

	def clear_player(self):
		try:
			os.remove(setting.PLAYER_BUFFER)
		except:
			pass

	def streaming(self):
		rebuffer = 0
		rebuffer_mark = time.time()
		while self.running:
			try:
				index, bytes = self.played_queue.get(timeout=1)
			except:
				continue
			# record rebuffer
			rebuffer += time.time() -rebuffer_mark
			duration = self.descriptor_list[index][0]
			print '[play]', index, 'rebuffer', rebuffer, 'duration', duration
			#time.sleep(duration)
			self.played_cond.acquire()
			self.played_cond.wait(duration)
			self.played_cond.release()
			# mark 
			rebuffer_mark = time.time()
			if index >= self.last_index:
				break 

	def realstreaming(self):
		p = subprocess.Popen(setting.PLAYER_COMMAND.split() + [setting.PLAYER_BUFFER],stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		p.wait()
		self.player_status = 'stopped'
		self.close()
		os._exit(0)

	def buffer_size(self):
		return self.average_duration * (len(self.retrieved) + self.played_queue.qsize() + len(self.retrieving))

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
		while segment_allocated > 0 and not self.wait_for_auction.empty():
			index = self.wait_for_auction.get()
			descriptor = self.descriptor_list[index]
			trunk_duration = descriptor[0]
			trunk_url = descriptor[1][rate]
			# send it to bidder
			self.retrieving[index] = time.time()
			self.message_client.sendto(ip, 'TASK:'+str(index)+','+trunk_url)
			segment_allocated = segment_allocated - 1

	""" Transport Factory """
	def receive_trunk(self, ip, index, data):
		print '[received]', index, 'size', float(len(data))/1024/128
		# discard wild data
		if not index in self.retrieving: 
			return
		# logging
		# self.logger.send('trunk received.')
		# write into buffer
		del self.retrieving[index]
		self.retrieved[index] = data
		# TODO buffered_index thread safe
		while self.bufferd_index in self.retrieved:
			# push into simuation
			played_entry = (self.bufferd_index, len(self.retrieved[self.bufferd_index]))
			self.played_queue.put(played_entry)
			# write into real file
			if not self.silent:
				with open(setting.PLAYER_BUFFER, 'ab') as f:
					#buffered
					f.write(self.retrieved[self.bufferd_index])
					if self.player_status == 'prepared':
						self.player_status = "playing"
						realplay = threading.Thread(target = self.realstreaming)
						realplay.start()
			# next
			del self.retrieved[self.bufferd_index]
			self.bufferd_index = self.bufferd_index + 1

	def fail_trunk(self, ip, index):
		if not index in self.retrieving: #wild data
			return
		del self.retrieving[index]
		self.wait_for_auction.put(index)

	def time_trunk(self, timeout):
		self.retrieving_timeout_cond
		while self.running:
			now = time.time()
			for index in self.retrieving:#TODO thread safe
				if self.retrieving[index] - now > timeout:
					del self.retrieving[index]
					self.wait_for_auction.put(index)
			#time.sleep(timeout)
			self.retrieving_timeout_cond.acquire()
			self.retrieving_timeout_cond.wait(timeout)
			self.retrieving_timeout_cond.release()

def parse_args():
	parser = argparse.ArgumentParser(description='Bidder')
	parser.add_argument('-p','--peer', required=False, default='Peer', help='name of peer')
	parser.add_argument('-u','--url', required=False, default=setting.PLAYER_DEFAULT_URL, help='url to play')
	parser.add_argument('-s','--silent', action='store_true', help='not play video actually')
	parser.add_argument('-t','--theta', default=setting.BIDDER_BASIC_TH, type=float, help='bidder preference theta')
	parser.add_argument('-q','--quality', default=setting.BIDDER_K_QV, type=float, help='bidder quality coefficient')
	parser.add_argument('-b','--buffer', default=setting.BIDDER_K_BUF, type=float, help='bidder buffer coefficient')
	parser.add_argument('-m','--mbuffer', default=setting.BIDDER_MAX_BUF, type=float, help='bidder max buffer')
	parser.add_argument('-a', '--broadcast', default=setting.UDP_BROADCAST, help='udp broadcast address')
	args = parser.parse_args()
	bidder_params = {}
	bidder_params['theta'] = args.theta
	bidder_params['kqv'] = args.quality
	bidder_params['kbuf'] = args.buffer 
	bidder_params['mbuf'] = args.mbuffer
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