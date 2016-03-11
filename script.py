import os
import time
import socket
import select
import argparse
import setting
from auctioneer import Auctioneer
from bidder import Bidder
from log import LogServer
from message import MessageServer
from message import MessageClient
from message import Protocol


class MessageProtocol(Protocol):
	def __init__(self, factory):
		self.factory = factory

	''' server callback '''
	def data_received(self, data, ip):
		self.factory.receive(data, ip)
	''' client callback '''
	def send_sucessed(self, data, ip):
		print data,'send sucessed'
	def send_failed(self, data, ip):
		print data, 'send failed'

class Peer(object):
	def __init__(self, peer):
		self.peer = peer
		# auction message server
		self.message_server  = MessageServer(
			setting.SCRIPT_HOST, 
			setting.SCRIPT_PORT, 
			MessageProtocol(self))
		self.bidder = None
		self.auctioneer = None

	def run(self):
		self.message_server.start()
		try:
			while True:
				command = raw_input().lower()
				if not command or command == 'exit':
					break
		except KeyboardInterrupt:
			pass
		if self.bidder:
			self.bidder.close()
		if self.auctioneer:
			self.auctioneer.close()
		self.message_server.close()


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
		if self.auctioneer and self.auctioneer.running:
			return
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
		if not self.auctioneer or not self.auctioneer.running:
			return
		self.auctioneer.close()

	def bidder_start(self,pack):
		if self.bidder and self.bidder.running:
			return
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
		if not self.bidder or not self.bidder.running:
			return
		self.bidder.close()

class CenterBase(object):
	def __init__(self, logfname):
		self.message_client = MessageClient(
			setting.UDP_BROADCAST,
			setting.SCRIPT_PORT,
			MessageProtocol(self))
		self.logfname = logfname

	def send(self, peer, pack):
		# at one second 
		repeat = 10
		for i in range(repeat):
			self.message_client.broadcast(''.join([peer, ':', pack]))
			time.sleep(0.1)

	''' To override '''
	def run(self):
		self.message_client.start()
		print '3 seconds demo, save log into', self.logfname, '...'
		# log
		logger = LogServer(self.logfname)
		logger.start()
		# peers
		peers = ['A', 'B', 'C', 'D']
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
		time.sleep(1.0)
		logger.close()
		self.message_client.close()

''' Scene A '''
class CenterA(CenterBase):
	
	''' @override '''
	def run(self):
		print 'Scene A'
		print 'log into', self.logfname
		print 'waiting 400 seconds...'
		t = 400
		# messager
		self.message_client.start()
		# log
		logger = LogServer(self.logfname)
		logger.start()
		# peers
		peers = ['A', 'B', 'C']
		for peer in peers:
			self.send(peer, 'B_START:1.0')
		for peer in peers:
			self.send(peer, 'A_START:3.0,3')
		time.sleep(t*0.25) # 100s
		self.send('B', 'A_STOP:')
		time.sleep(t*0.125) # 50s : 150s
		self.send('C', 'A_STOP:')
		time.sleep(t*0.125) # 50s : 200s
		self.send('B', 'A_START:3.0,3')
		time.sleep(t*0.125) # 50s : 250s
		self.send('C', 'A_START:3.0,3')
		time.sleep(t*0.375) # 150 : 400s
		for peer in peers:
			self.send(peer, 'A_STOP:')
		for peer in peers:
			self.send(peer, 'B_STOP:')
		time.sleep(1.0)
		logger.close()
		self.message_client.close()

''' Scene B'''
class CenterB(CenterBase):
	
	''' @override '''
	def run(self):
		print 'Scene B'
		print 'log into', self.logfname
		print 'waiting 400 seconds...'
		t = 400
		# messager
		self.message_client.start()
		# log
		logger = LogServer(self.logfname)
		logger.start()
		# peers
		peers = ['A', 'B', 'C', 'D']
		for peer in peers:
			self.send(peer, 'B_START:1.0')
		self.send('A', 'A_START:2.0,3')
		self.send('B', 'A_START:6.0,3')
		self.send('C', 'A_START:6.0,3')
		self.send('D', 'A_START:6.0,3')
		time.sleep(t)
		for peer in peers:
			self.send(peer, 'A_STOP:')
		for peer in peers:
			self.send(peer, 'B_STOP:')
		time.sleep(1.0)
		logger.close()
		self.message_client.close()
		time.sleep(5.0)

class CenterBNo(CenterBase):
	
	''' @override '''
	def run(self, peer):
		print 'Scene B'
		print 'log into', self.logfname
		print 'waiting 400 seconds...'
		t = 200
		# messager
		self.message_client.start()
		# log
		logger = LogServer(self.logfname)
		logger.start()
		# peers
		self.send(peer,'B_START:1.0')
		if peer == 'A':
			self.send('A', 'A_START:2.0,3')
		else:
			self.send(peer, 'A_START:6.0,3')
		time.sleep(t)
		self.send(peer, 'A_STOP:')
		self.send(peer, 'B_STOP:')
		time.sleep(1.0)
		logger.close()
		self.message_client.close()
		time.sleep(5.0)


''' Scene E'''
class CenterE(CenterBase):
	
	''' @override '''
	def run(self, k):
		print 'Scene E'
		print 'log into', self.logfname
		print 'waiting 400 seconds...'
		t = 200
		# messager
		self.message_client.start()
		# log
		logger = LogServer(self.logfname)
		logger.start()
		# peers
		peers = ['A', 'B', 'C', 'D']
		for peer in peers:
			self.send(peer, 'B_START:1.0')
		for peer in ['A','B']:
			self.send(peer, 'A_START:3.0,'+str(k))
		time.sleep(t)
		for peer in ['A','B']:
			self.send(peer, 'A_STOP:')
		for peer in peers:
			self.send(peer, 'B_STOP:')
		time.sleep(1.0)
		logger.close()
		self.message_client.close()
		time.sleep(5.0)


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
			for i in range(1):
				CenterA(args.logfile +'_'+ str(i+3)+'.log').run()
		elif args.script == 'B':
			CenterB(args.logfile).run()
		elif args.script == 'E':
			for k in [1,3,5,10]:
				CenterE(args.logfile+'_k_'+str(k)+'.log').run(k)
		else:
			print 'This script does not exist.'
	else:
		Peer(args.peer).run()


