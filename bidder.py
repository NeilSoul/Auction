#!usr/bin/env python
import os
import threading
import subprocess
from Queue import PriorityQueue
import setting
import message
import transport
import log
from parser import parse_m3u8

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
		threading.Thread(target=self.factory.receive_trunk, args=(ip, eval(index), data)).start()
	def receive_failed(self, index, list, address):
		ip = address[0]
		self.factory.fail_trunk(ip, eval(index))
		

class Bidder(object):
	def __init__(self, code):
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
		self.logger = log.LogClient(code)
		# init
		self.code = code
		self.prepare2play(setting.PLAYER_URL)

	""" Bidder(receiver, player) Life Cycle """
	def start(self):
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
		self.clear_player()

	""" Player Methods"""
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

	""" Bid Factory.
	bid : bid for auction.
	send task : send segment task for auction.
	"""
	def bid(self, ip, info):
		if not self.player_status == 'stopped':
			self.message_client.sendto(ip, 'BID:i want to bid.')

	def send_task(self, ip, info):
		if not self.player_status == 'stopped' and not self.wait_for_auction.empty():
			index = self.wait_for_auction.get()
			descriptor = self.descriptor_list[index]
			trunk_duration = descriptor[0]
			trunk_url = descriptor[1][self.selected_rate]
			# send it to bidder
			self.retrieving[index] = ip
			self.message_client.sendto(ip, 'TASK:'+str(index)+','+trunk_url)

	""" Transport Factory """
	def receive_trunk(self, ip, index, data):
		# discard wild data
		if not index in self.retrieving: 
			return
		# logging
		self.logger.send('trunk received.')
		# write into buffer
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

if __name__ == "__main__":
	bidder  = Bidder('A')
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