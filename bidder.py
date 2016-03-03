#!usr/bin/env python
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
	def __init__(self, peername, url, silent):
		# bidder message server
		self.message_server  = message.MessageServer(
			setting.UDP_HOST, 
			setting.UDP_BID_PORT, 
			BidderProtocol(self))
		# bidder sender
		self.message_client = message.MessageClient(
			setting.UDP_BROADCAST,
			setting.UDP_AUCTION_PORT,
			message.Protocol())
		# transport center
		self.transport_center = transport.TransportServer(
			setting.TRP_HOST,
			setting.TRP_PORT,
			TransportProtocol(self))
		# log center
		self.logger = log.LogClient(peername)
		# init
		self.peername = peername
		self.silent = silent
		self.streaming_url = url

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
		self.stream_simulation.join()
		self.retrieving_timeout.join()

	def close(self):
		self.message_server.close()
		self.message_client.close()
		self.transport_center.close()
		self.clear_player()
		self.running = 0
		self.played_queue.put(-1)#important

	""" Player Methods"""
	def prepare2play(self, url):
		print 'm3u8 parsing...'
		self.descriptor_list = parse_m3u8(url)
		self.rate_list = self.descriptor_list[0][1].keys()
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
		print 'm3u8 ready.'
		self.played_queue = Queue()
		self.stream_simulation = threading.Thread(target = self.streaming)
		self.stream_simulation.start()
		self.retrieving_timeout = threading.Thread(target=self.time_trunk, args=(10,))
		self.retrieving_timeout.start()
		self.clear_player()
		# core
		self.core = BidderCore(self)

	def clear_player(self):
		try:
			os.remove(setting.PLAYER_BUFFER)
		except:
			pass

	def streaming(self):
		while self.running:
			index = self.played_queue.get()
			if index < 0:
				break
			duration = self.descriptor_list[index][0]
			print '[play]', index, 'duration', duration
			time.sleep(duration)
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
		auction_peer, bid = self.core.handle_auction(auction)
		if bid:
			self.logger.bid_send(self.peername, auction_peer, self.buffer_size(), bid)
			self.message_client.sendto(ip, ':'.join(['BID',str(bid)]))

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
		print '[received]', index
		# discard wild data
		if not index in self.retrieving: 
			return
		# logging
		# self.logger.send('trunk received.')
		# write into buffer
		del self.retrieving[index]
		self.retrieved[index] = data
		while self.bufferd_index in self.retrieved:
			with open(setting.PLAYER_BUFFER, 'ab') as f:
				#buffered
				f.write(self.retrieved[self.bufferd_index])
				if self.player_status == 'prepared' and not self.silent:
					self.player_status = "playing"
					realplay = threading.Thread(target = self.realstreaming)
					realplay.start()
			self.played_queue.put(self.bufferd_index)
			# next
			del self.retrieved[self.bufferd_index]
			self.bufferd_index = self.bufferd_index + 1

	def fail_trunk(self, ip, index):
		if not index in self.retrieving: #wild data
			return
		del self.retrieving[index]
		self.wait_for_auction.put(index)

	def time_trunk(self, timeout):
		while self.running:
			now = time.time()
			for index in self.retrieving:#TODO thread safe
				if self.retrieving[index] - now > timeout:
					del self.retrieving[index]
					self.wait_for_auction.put(index)
			time.sleep(timeout)

def parse_args():
	parser = argparse.ArgumentParser(description='Bidder')
	parser.add_argument('--peer', required=False, default='Peer', help='name of peer')
	parser.add_argument('--url', required=False, default=setting.PLAYER_DEFAULT_URL, help='url to play')
	parser.add_argument('--silent', action='store_true')
	return parser.parse_args()

if __name__ == "__main__":
	args = parse_args()
	bidder  = Bidder(args.peer, args.url, args.silent)
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