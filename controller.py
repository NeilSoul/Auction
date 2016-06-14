#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import time
import struct
import logging
import setting
from discovery import Broadcaster
from discovery import ListenerProtocol
from discovery import Listener
from message import MessageProtocol
from message import Message

class Slave(ListenerProtocol, MessageProtocol):

	def __init__(self, peername):
		self.peername = peername
		# discovery module
		self.listener = Listener(setting.CTR_HOST, setting.CTR_MASTER_BCAST_PORT, self)
		# message module
		self.message = Message(setting.CTR_HOST, setting.CTR_SLAVE_PORT, setting.CTR_MASTER_PORT, self)

	def log(self, tag, content):
		for peer in self.listener.peers.keys():
			#print 'send', ':'.join([tag, str(content)]), 'to', peer
			self.message.sendto(peer, ':'.join([tag, str(content)]))

	'Open API'
	def run(self):
		self.listener.run()
		self.message.run()

	def close(self):
		self.listener.close()
		self.message.close()

	def introduce(self):
		time.sleep(1.0) #prepare time to find master
		self.log('INT', self.peername)

	def slave_play(self, desc):
		#rate, duration, delay = desc
		pack = struct.pack('!fff', *desc)
		self.log('P', pack)

	def slave_bid(self, desc):
		#[auction_peer, auction_index, self.buffer_size(), bid]
		pack = str(desc)
		self.log('B', pack)

	def slave_auction(self, desc):
		self.log('A', desc)

	def slave_decide(self, desc):
		#[self.auction_index-1, ip, allocs[ip][0], allocs[ip][1], allocs[ip][2]]
		self.log('D', str(desc))

	def slave_transport(self, desc):
		#[ip, index, size, duration]
		self.log('T', str(desc))

	'MessageProtocol'
	def on_msg_from_peer(self, data, peer):
		#print 'received', data, 'from', peer
		try:
			inst, info = data.split(':',1)
		except:
			return
		if inst == 'B1':
			self.bidder_start_from_master(peer, info)
		elif inst == 'B2':
			self.bidder_stop_from_master(peer, info)
		elif inst == 'A1':
			self.auctioneer_start_from_master(peer, info)
		elif inst == 'A2':
			self.auctioneer_stop_from_master(peer, info)


	'Override'
	def bidder_start_from_master(self, master_ip, info):
		pass

	def bidder_stop_from_master(self, master_ip, info):
		pass

	def auctioneer_start_from_master(self, master_ip, info):
		pass

	def auctioneer_stop_from_master(self, master_ip, info):
		pass

class Master(MessageProtocol):

	def __init__(self, peername, logfile):
		self.peername = peername
		# discovery module
		self.bcaster = Broadcaster(setting.UDP_BROADCAST, setting.CTR_MASTER_BCAST_PORT)
		# message module
		self.message = Message(setting.CTR_HOST, setting.CTR_MASTER_PORT, setting.CTR_SLAVE_PORT, self)
		# slaves
		self.slaves = {}
		self.peers = {}
		# logging
		self.logfile = logfile if logfile else '%s-%s' % (time.strftime("%m-%d"),str(int(time.time()) % 100).zfill(3))
		self.logfile = os.path.join(setting.LOG_DIR, self.logfile)
		logging.basicConfig(level=logging.DEBUG,
			format = '%(asctime)s %(filename)s [line:%(lineno)d] %(message)s',
			datefmt = '%a, %d %b %Y %H:%M:%S',
			filename = self.logfile+'.log',
			filemode = 'a')
		console = logging.StreamHandler()
		console.setLevel(logging.INFO)
		formatter = logging.Formatter('%(levelname)-8s %(message)s')
		console.setFormatter(formatter)
		logging.getLogger('').addHandler(console)
		'Plot module'
		import plot
		self.plot = plot

	'Open API'
	def run(self):
		self.bcaster.run()
		self.message.run()
		self.plot_rate_init()

	def close(self):
		self.bcaster.close()
		self.message.close()
		self.plot_rate_finish()

	def send_order_to_slave(self, peername, order):
		if peername in self.slaves:
			self.message.sendto(self.slaves[peername], order)

	def start_bidder_of_slave(self, peername):
		self.send_order_to_slave(peername, 'B1')

	def stop_bidder_of_slave(self, peername):
		self.send_order_to_slave(peername, 'B2')

	def start_auctioneer_of_slave(self, peername):
		self.send_order_to_slave(peername, 'A1')

	def stop_auctioneer_of_slave(self, peername):
		self.send_order_to_slave(peername, 'A2')
		

	'MessageProtocol'
	def on_msg_from_peer(self, data, peer):
		#print 'received', data, 'from', peer
		# parse log message
		try:
			tag, pack = data.split(':',1)
		except:
			return
		# response
		if tag == 'INT':#introduce
			self.slaves[pack] = peer
			self.peers[peer] = pack
			logging.info('%s@join ip=%s' % (pack, peer))
			self.on_slave_join(pack)
		else:
			try:
				peername = self.peers[peer]
			except:
				return
			if tag == 'P':
				self.on_slave_play(peername, pack)
			elif tag == 'B':
				self.on_slave_bid(peername, pack)
			elif tag == 'A':
				self.on_slave_auction(peername, pack)
			elif tag == 'D':
				self.on_slave_decide(peername, pack)
			elif tag == 'T':
				self.on_slave_transport(peername, pack)

	'Recall API'
	def on_slave_play(self, peername, pack):
		rate, duration, delay = struct.unpack('!fff', pack)
		self.plot_rate_add((rate,duration,delay))
		logging.info('%s@play rate=%0.2f, duration=%0.2f, rebuffer=%0.2f'% (peername, rate, duration, delay))

	def on_slave_bid(self, peername, pack):
		logging.info('%s@bid %s' % (peername, pack))

	def on_slave_auction(self, peername, pack):
		logging.info('%s@auction %s' % (peername, pack))

	def on_slave_decide(self, peername, pack):
		#[self.auction_index-1, ip, allocs[ip][0], allocs[ip][1], allocs[ip][2]]
		index, ip, tasks, bitrate, price = eval(pack)
		try:
			bidderpeer = self.peers[ip]
		except:
			return
		logging.info('%s@decide index=%d, winner=%s, bitrate=%0.2f, price=%0.2f, segments=%d' % (peername, index, bidderpeer, bitrate/1024.0/1024.0, price, tasks))

	def on_slave_transport(self, peername, pack):
		#[ip, index, size, duration]
		ip, index, size, duration = eval(pack)
		try:
			bidderpeer = self.peers[ip]
		except:
			return
		logging.info('%s@transport index=%d, bidder=%s, size=%0.2f, transport_duration=%0.2f' %(peername, int(index), bidderpeer, size, duration))

	#Overide
	def on_slave_join(self, peername):
		pass 

	'Plot API'
	def plot_rate_init(self):
		self.rate_items = []

	def plot_rate_add(self, item):
		self.rate_items.append(item)

	def plot_rate_finish(self):
		self.plot.create_rate_plot(self.rate_items, self.logfile+'_rate.png')

