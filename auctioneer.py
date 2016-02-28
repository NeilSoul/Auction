#!usr/bin/env python
"""
retriveing time out or failure TODO
"""
import os
import subprocess
import threading
import time
from Queue import PriorityQueue
import setting
import message
import transport
from parser import parse_m3u8

class AuctionProtocol(message.Protocol):

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
		if inst == 'BID':
			self.factory.receive_bid(ip, info)

class TransportProtocol(transport.Protocol):

	def __init__(self, factory):
		self.factory = factory
	def on_receive_success(self, index, list, address):
		ip = address[0]
		data = b''.join(list)
		self.factory.receive_trunk(ip, eval(index), data)
	def on_receive_failure(self, index, list, address):
		ip = address[0]
		self.factory.fail_trunk(ip, eval(index))

class Auctioneer(object):

	def __init__(self):
		# auction message center
		self.message_center  = message.Message(
			setting.MSG_HOST, 
			setting.AUCTION_PORT, 
			setting.MSG_BROADCAST, 
			setting.BID_PORT, 
			AuctionProtocol(self))
		# transport center
		self.transport_center = transport.Transport(
			setting.TRP_HOST,
			setting.TRP_PORT,
			TransportProtocol(self))
		# player status
		self.player_status = "idle"

	""" Auctioneer Life Cycle
	start->play->close, join.
	"""
	def start(self):
		self.message_center.start()
		self.transport_center.start()

	def join(self):
		self.message_center.join()
		self.transport_center.join()

	def close(self):
		self.message_center.close()
		self.transport_center.close()

	def prepare2play(self, url):
		self.descriptor_list = parse_m3u8(url)
		self.rate_list = self.descriptor_list[0][1].keys()
		self.selected_rate = self.rate_list[0]
		self.clear_player()
		# wait for auction : priority queue
		self.wait_for_auction = PriorityQueue()
		for i in range(len(self.descriptor_list)):
			self.wait_for_auction.put(i)
		# wait for retrieve : dictionary (index:ip)
		self.retrieving = {}
		# retrieved : dictionary (index:data)
		self.retrieved = {}
		# the index of which trunk is ready to write into buffer  
		self.bufferd_index = 0
		# status of player
		self.player_status = 'prepared' 

	def play(self, url):
		self.prepare2play(url)
		while not self.wait_for_auction.empty():
			if self.player_status == 'stopped':
				break
			self.auction()
			time.sleep(0.5)
		self.clear_player()

	""" Auction Factory.
	auction : make an auction.
	receive_bid : receive a bid.
	"""
	def auction(self):
		self.bids = {}
		self.message_center.broadcast('AUCTION:cost function')
		time.sleep(0.1)
		if self.bids:
			for ip in self.bids:
				choice = ip
			self.decide_bid(ip, self.bids[ip])

	def receive_bid(self, ip, info):
		if not self.player_status == 'idle':
			self.bids[ip] = info

	def decide_bid(self, ip, info):
		# get the prior index
		if self.wait_for_auction.empty():
			return
		index = self.wait_for_auction.get()
		descriptor = self.descriptor_list[index]
		trunk_duration = descriptor[0]
		trunk_url = descriptor[1][self.selected_rate]
		# send it to bidder
		self.retrieving[index] = ip
		self.message_center.sendto(ip, 'WIN:'+str(index)+','+trunk_url)

	""" Transport Factory
	"""
	def receive_trunk(self, ip, index, data):
		if not index in self.retrieving: #wild data
			return
		del self.retrieving[index]
		self.retrieved[index] = data
		while self.bufferd_index in self.retrieved:
			if self.player_status == 'stopped':
				break
			with open(setting.PLAYER_BUFFER, 'ab') as f:
				#buffered
				f.write(self.retrieved[self.bufferd_index])
				if self.player_status == 'prepared':
					streaming = threading.Thread(target = self.streaming)
					streaming.start()
			# next
			del self.retrieved[self.bufferd_index]
			self.bufferd_index = self.bufferd_index + 1

	def fail_trunk(self, ip, index):
		if not index in self.retrieving: #wild data
			return
		del self.retrieving[index]
		self.wait_for_auction.put(index)#TODO multi thread safe

	""" Player Methods
	clear and streaming.
	"""
	def clear_player(self):
		try:
			os.remove(setting.PLAYER_BUFFER)
		except:
			pass

	def streaming(self):
		self.player_status = 'playing' 
		p = subprocess.Popen(setting.PLAYER_COMMAND.split() + [setting.PLAYER_BUFFER],stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		p.wait()
		self.player_status = 'stopped'

if __name__ == "__main__":
	auctioneer  = Auctioneer()
	auctioneer.start()
	try:
		while True:
			command = raw_input().lower()
			if not command:
				break
			if command == 'exit':
				break
			elif command == 'play':
				auctioneer.play(setting.PLAYER_URL)
	except KeyboardInterrupt:
		pass
	auctioneer.close()
	auctioneer.join()