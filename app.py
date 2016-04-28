#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
import time
import argparse
from controller import Slave
from controller import Master
import setting
from auctioneer import Auctioneer
from bidder import Bidder


class ManualSlave(Slave):

	def loop(self, streaming = False):
		self.run()
		self.introduce()
		self.bidder  = Bidder(setting.default_bidder_params(self.peername), self)
		self.auctioneer = Auctioneer(setting.default_auctioneer_params(self.peername), self)
		self.bidder.run()
		self.auctioneer.run()
		if streaming:
			if sys.platform.startswith('linux'):
				from vlc_player import VlcPlayer as Player
			elif sys.platform.startswith('darwin'):
				from qtvlc_player import QtvlcPlayer as Player
			player = Player()
			player.open_api_run()
		else:
			try:
				while True:
					command = raw_input().lower()
					if not command or command == 'exit':
						break
			except KeyboardInterrupt:
				pass
		self.bidder.close()
		self.auctioneer.close()
		self.close()

class AutoSlave(Slave):

	def loop(self, streaming = False):
		self.run()
		self.introduce()
		self.bidder  = Bidder(setting.default_bidder_params(self.peername), self)
		self.auctioneer = Auctioneer(setting.default_auctioneer_params(self.peername), self)
		if streaming:
			if sys.platform.startswith('linux'):
				import qtvlc_player.QtvlcPlayer as Player
			elif sys.platform.startswith('darwin'):
				import vlc_player.VlcPlayer as Player
			player = Player()
			player.open_api_run()
		else:
			try:
				while True:
					command = raw_input().lower()
					if not command or command == 'exit':
						break
			except KeyboardInterrupt:
				pass
		if self.bidder.running:
			self.bidder.close()
		if self.auctioneer.running:
			self.auctioneer.close()
		self.close()

	'Override'
	def bidder_start_from_master(self, master_ip):
		if not self.bidder.running:
			self.bidder.run()

	def bidder_stop_from_master(self, master_ip):
		self.bidder.close()

	def auctioneer_start_from_master(self, master_ip):
		if not self.auctioneer.running:
			self.auctioneer.run()

	def auctioneer_stop_from_master(self, master_ip):
		self.auctioneer.close()

class ManualMaster(Master):

	def loop(self):
		self.run()
		try:
			while True:
				command = raw_input().lower()
				if not command or command == 'exit':
					break
				try:
					peername,order = command.split(':',1)
				except:
					continue
				self.send_order_to_slave(peername.upper(), order.upper())
		except KeyboardInterrupt:
			pass
		self.close()

class SceneMaster(Master):

	def loop(self):
		self.scene_not_started = True
		self.running = 1
		self.set_scene_members()
		print 'Waiting' , self.members, '...'
		self.run()
		while self.running:
			try:
				time.sleep(1.0)
			except KeyboardInterrupt:
				break
		self.close()

	def on_slave_join(self, peername):
		if self.scene_not_started and set(self.slaves.keys()) >= set(self.members):
			self.scene_not_started = False
			self.scene_start()

	def scene_start(self):
		self.scene_process()
		self.running = 0

	#Overide
	def set_scene_members(self):
		self.members = []
		print 'Members to be set...'
		self.scene_start()#trick

	def scene_process(self):
		print 'Scene to be write...'

class SceneA(SceneMaster):

	def set_scene_members(self):
		self.members = ['A']

	def scene_process(self):
		print 'A launch bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'B1')
		print 'A launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A1')
		time.sleep(30.0)
		print 'A close bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'B2')
		print 'A close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A2')




def parse_args():
	parser = argparse.ArgumentParser(description='App')
	parser.add_argument('-p','--peer', default='P', help='peer name')
	parser.add_argument('-r','--role', default='m', help='role of the app, to be m(Master) or s(Slave)')
	parser.add_argument('-a','--auto', action='store_true', help='if is a automatic slave')
	parser.add_argument('-s','--scene', default='N', help='select a scene')
	parser.add_argument('-l','--log', help='log file')
	parser.add_argument('-v','--video', action='store_true', help='will play video')
	return parser.parse_args()

if __name__=="__main__":
	args = parse_args()
	if args.role == 'm':
		if args.scene == 'N':
			m = ManualMaster(args.peer, args.log)
			m.loop()
		else:
			m = SceneA(args.peer, args.log)
			m.loop()
	else:
		if args.auto:
			s = AutoSlave(args.peer)
			s.loop(args.video)
		else:
			s = ManualSlave(args.peer)
			s.loop(args.video)