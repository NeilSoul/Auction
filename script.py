import os
import time
import socket
import select
import argparse
import setting
from auctioneer import Auctioneer
from bidder import Bidder
from log import LogServer

class Peer(object):
	def __init__(self, peer):
		self.peer = peer
		self.server_address = (setting.SCRIPT_HOST, setting.SCRIPT_PORT)
		self.server = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.server.setblocking(False)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.server.bind(self.server_address)
		self.timeout = 3

	def run(self):
		while 1:
			try:
				readable , writable , exceptional = select.select([self.server], [], [], self.timeout)
			except select.error,e:
				break
			# When timeout reached , select return three empty lists
			if not (readable or writable or exceptional) :
				continue  
			for s in readable :
				if s is self.server:
					data, address=s.recvfrom(1024)
					self.receive(data, address)


	def receive(self, data, address):
		try:
			peer, inst, pack = data.split(':',2)
		except:
			return
		if peer == self.peer:
			if inst == 'A_START':
				self.auctioneer_start(pack)
			elif inst == 'A_STOP':
				self.auctioneer_stop(pack)
			elif inst == 'B_START':
				self.bidder_start(pack)
			elif inst == 'B_STOP':
				self.bidder_stop(pack)


	def auctioneer_start(self, pack):
		delay, k = pack.split(',',1)
		auctioneer_params = {}
		auctioneer_params['segment'] = int(k)
		auctioneer_params['capacity'] = setting.AUCTIONEER_DEFAULT_CAPACITY
		auctioneer_params['timecost'] = setting.AUCTIONEER_COST_TI
		auctioneer_params['cellular'] = setting.AUCTIONEER_COST_DA
		auctioneer_params['wifi'] = setting.AUCTIONEER_COST_WDA
		auctioneer_params['delay'] = float(delay)
		auctioneer_params['broadcast'] = setting.UDP_BROADCAST
		self.auctioneer  = Auctioneer(self.peer, auctioneer_params)
		self.auctioneer.start()

	def auctioneer_stop(self, pack):
		self.auctioneer.close()
		self.auctioneer.join()

	def bidder_start(self,pack):
		bidder_params = {}
		bidder_params['theta'] = setting.BIDDER_BASIC_TH
		bidder_params['kqv'] = setting.BIDDER_K_QV
		bidder_params['kbuf'] = setting.BIDDER_K_BUF
		bidder_params['ktheta'] = setting.BIDDER_K_THETA
		bidder_params['kbr'] = setting.BIDDER_K_BR
		bidder_params['mbuf'] = setting.BIDDER_MAX_BUF
		bidder_params['kcapacity'] = float(pack)
		bidder_params['broadcast'] = setting.UDP_BROADCAST
		self.bidder  = Bidder(self.peer, setting.PLAYER_DEFAULT_URL, True, bidder_params)
		self.bidder.start()

	def bidder_stop(self, pack):
		self.bidder.close()
		self.bidder.join()


class CenterBase(object):
	def __init__(self, logfname):
		self.sender = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.sender.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
		self.sender_address = (setting.UDP_BROADCAST, setting.SCRIPT_PORT)
		self.logfname = logfname
	def send(self, peer, pack):
		message = ''.join([peer, ':', pack])
		self.sender.sendto(message, self.sender_address)

	''' To override '''
	def run(self):
		print '3 seconds demo, save log into', self.logfname, '...'
		# log
		logger = LogServer(self.logfname)
		logger.start()
		# peers
		peers = ['A', 'B', 'C']
		for peer in peers:
			self.send(peer, 'A_START:1.0,'+str(setting.AUCTIONEER_SEG_NUM))
		for peer in peers:
			self.send(peer, 'B_START:1.0')
		time.sleep(3.0)
		for peer in peers:
			self.send(peer, 'A_STOP:')
		for peer in peers:
			self.send(peer, 'B_STOP:')
		# log
		logger.close()

''' Scene A '''
class CenterA(CenterBase):
	
	''' @override '''
	def run(self):
		print 'Scene A'
		print 'log into', self.logfname
		print 'waiting 400 seconds...'
		t = 40.0#400.0
		# log
		logger = LogServer(self.logfname)
		logger.start()
		# peers
		peers = ['A', 'B', 'C']
		for peer in peers:
			self.send(peer, 'B_START:1.0')
		for peer in peers:
			self.send(peer, 'A_START:10.0,3')
		time.sleep(t*0.25) # 100s
		self.send('B', 'A_STOP:')
		time.sleep(t*0.125) # 50s : 150s
		self.send('C', 'A_STOP:')
		time.sleep(t*0.125) # 50s : 200s
		self.send('B', 'A_START:10.0,3')
		time.sleep(t*0.125) # 50s : 250s
		self.send('C', 'A_START:10.0,3')
		time.sleep(t*0.375) # 150 : 400s
		for peer in peers:
			self.send(peer, 'A_STOP:')
		for peer in peers:
			self.send(peer, 'B_STOP:')
		# log
		logger.close()


def parse_args():
	parser = argparse.ArgumentParser(description='Script')
	parser.add_argument('-c','--center', action='store_true', help='if is a role of center(peer default)')
	parser.add_argument('-s','--script', default='Base', help='which script')
	parser.add_argument('-l','--logfile', help='file name of the log.')
	parser.add_argument('-p','--peer', default='P', help='peer name')
	return parser.parse_args()

if __name__=="__main__":
	args = parse_args()
	if args.center:
		if args.script == 'Base':
			CenterBase(args.logfile).run()
		elif args.script == 'A':
			CenterA(args.logfile).run()
		else:
			print 'This script does not exist.'
	else:
		Peer(args.peer).run()


