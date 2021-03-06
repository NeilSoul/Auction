#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sys
import time
import argparse
import threading
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
		#auctioneer bidder
		self.bidder = None
		self.auctioneer = None
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
		if self.bidder and self.bidder.running:
			self.bidder.close()
		if self.auctioneer and self.auctioneer.running:
			self.auctioneer.close()
		self.close()

	'Override'
	def bidder_start_from_master(self, master_ip, info):
		if self.bidder and self.bidder.running:
			self.bidder.close()
		bidder_params = setting.default_bidder_params(self.peername)
		bidder_params['bnumber'] = int(info)
		self.bidder  = Bidder(bidder_params, self)
		self.bidder.run()

	def bidder_stop_from_master(self, master_ip, info):
		if self.bidder:
			self.bidder.close()

	def auctioneer_start_from_master(self, master_ip, info):
		if self.auctioneer and self.auctioneer.running:
			self.auctioneer.close()
		auctioneer_params = setting.default_auctioneer_params(self.peername)
		auctioneer_params['delay'] = float(info)
		self.auctioneer = Auctioneer(auctioneer_params, self)
		self.auctioneer.run()

	def auctioneer_stop_from_master(self, master_ip, info):
		if self.auctioneer:
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
		threading.Thread(target = self.scene_process).start()

	#Overide
	def set_scene_members(self):
		self.members = []
		print 'Members to be set...'
		self.scene_start()#trick

	def scene_process(self):
		print 'Scene to be write...'

	def scene_process_end(self):
		self.running = 0

class SceneNo1(SceneMaster):

	def set_scene_members(self):
		self.members = ['A']

	def scene_process(self):
		print 'A launch bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'B1:1')
		print 'A launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A1:2.20')
		time.sleep(200.0)
		print 'A close bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'B2:')
		print 'A close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A2:')
		self.scene_process_end()

class SceneNo2(SceneMaster):

	def set_scene_members(self):
		self.members = ['A']

	def scene_process(self):
		print 'A launch bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'B1:1')
		print 'A launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A1:4.40')
		time.sleep(200.0)
		print 'A close bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'B2:')
		print 'A close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A2:')
		self.scene_process_end()

class SceneNo3(SceneMaster):

	def set_scene_members(self):
		self.members = ['A']

	def scene_process(self):
		print 'A launch bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'B1:1')
		print 'A launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A1:22')
		time.sleep(200.0)
		print 'A close bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'B2:')
		print 'A close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A2:')
		self.scene_process_end()

class SceneCo4(SceneMaster):

	def set_scene_members(self):
		self.members = ['A', 'B', 'C']

	def scene_process(self):
		print 'A launch bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'B1:3')
		print 'A launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A1:2.2')
		print 'B launch bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'B1:3')
		print 'B launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'A1:4.4')
		print 'C launch bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('C', 'B1:3')
		print 'C launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('C', 'A1:22')
		time.sleep(200.0)
		print 'A close bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'B2:')
		print 'A close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A2:')
		print 'B close bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'B2:')
		print 'B close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'A2:')
		print 'C close bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('C', 'B2:')
		print 'C close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('C', 'A2:')
		self.scene_process_end()

class SceneCo5(SceneMaster):

	def set_scene_members(self):
		self.members = ['A', 'B']

	def scene_process(self):
		print 'A launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A1:2.2')
		print 'B launch bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'B1:2')
		print 'B launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'A1:22')
		time.sleep(200.0)
		print 'A close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A2:')
		print 'B close bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'B2:')
		print 'B close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'A2:')
		self.scene_process_end()

class SceneCo6(SceneMaster):

	def set_scene_members(self):
		self.members = ['A', 'B']

	def scene_process(self):
		#0~40s
		print 'A launch bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'B1:2')
		print 'A launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A1:2.2')
		print 'B launch bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'B1:2')
		print 'B launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'A1:2.2')
		time.sleep(40.0)
		#40s~90s
		print 'B close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'A2:')
		time.sleep(1.0)
		print 'B launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'A1:22')
		time.sleep(50.0)
		#90~150s
		print 'B close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'A2:')
		time.sleep(1.0)
		print 'B launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'A1:2.2')
		time.sleep(10.0)
		print 'A close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A2:')
		time.sleep(1.0)
		print 'A launch auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A1:22')
		time.sleep(50.0)
		#final
		print 'A close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'A2:')
		print 'A close bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('A', 'B2:')
		print 'B close bidder at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'B2:')
		print 'B close auctioneer at', time.strftime("%H:%M:%S")
		self.send_order_to_slave('B', 'A2:')
		self.scene_process_end()

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
		elif args.scene == 'N1':
			m = SceneNo1(args.peer, args.log)
			m.loop()
		elif args.scene == 'N2':
			m = SceneNo2(args.peer, args.log)
			m.loop()
		elif args.scene == 'N3':
			m = SceneNo3(args.peer, args.log)
			m.loop()
		elif args.scene == 'C4':
			m = SceneCo4(args.peer, args.log)
			m.loop()
		elif args.scene == 'C5':
			m = SceneCo5(args.peer, args.log)
			m.loop()
		elif args.scene == 'C6':
			m = SceneCo6(args.peer, args.log)
			m.loop()
	else:
		if args.auto:
			s = AutoSlave(args.peer)
			s.loop(args.video)
		else:
			s = ManualSlave(args.peer)
			s.loop(args.video)