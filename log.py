import os
import time
import socket
import select
import setting

class LogServer(object):
	def __init__(self):
		self.server_address = (setting.LOG_HOST, setting.LOG_PORT)
		self.server = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.server.setblocking(False)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.server.bind(self.server_address)
		self.timeout = 3
		self.auction = open(os.path.join(setting.LOG_DIR, 'auction.log'), 'w')
		self.peername = {} # {ip:peer}
		self.auctioneers = {} # {ip:is auctioning}
		self.bidders = {} #{ ip :{auction_peer : is bidding}} #TODO multi bidding at begin
		self.timestart = time.time()

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

		self.server.close()
		self.auction.close()

	def receive(self, data, address):
		# parse instruction
		ip = address[0]
		try:
			inst, pack = data.split(':',1)
		except:
			return
		# divide instructions
		if inst == 'A':
			self.auction_broadcast(ip, pack)
		elif inst == 'D':
			self.auction_decide(ip, pack)
		elif inst == 'C':
			self.decide_complete(ip, pack)
		elif inst == 'B':
			self.bid_send(ip, pack)
		elif inst == 'T':
			self.transport_complete(ip, pack)

	def logline(self, line):
		self.auction.write(line)
		self.auction.write('\r\n')

	def loglist(self, list):
		self.logline(' '.join(map(lambda x:str(x), list)))

	def auction_broadcast(self, ip, pack):
		# extract
		timestamp = time.time() - self.timestart
		peer,segments,capacity,cti,cda,cwda = eval(pack)
		# mark
		self.peername[ip] = peer
		# write to file
		if not ip in self.auctioneers or not self.auctioneers[ip]:
			self.loglist(['#A', peer])
			self.logline(str(timestamp))
			self.loglist([segments, capacity, cti, cda, cwda])
		self.auctioneers[ip] = 1

	def auction_decide(self,ip, pack):
		# extract
		timestamp = time.time()- self.timestart
		peer, bidder_ip, segments, bitrate, payment = eval(pack)
		bidder_peer = self.peername[bidder_ip]
		# write to file
		self.loglist(['#D', peer, bidder_peer])
		self.logline(str(timestamp))
		self.loglist([segments, float(bitrate)/1024/1024, payment])
		# clear
		self.bidders[bidder_ip][peer] = 0

	def decide_complete(self, ip, peer):
		self.auctioneers[ip] = 0

	def bid_send(self, ip, pack):
		# extract
		timestamp = time.time()- self.timestart
		peer, auction_peer, bid = eval(pack)
		bitrates,prices,gains = bid
		# mark
		self.peername[ip] = peer
		# write to file
		if not ip in self.bidders:
			self.bidders[ip] = {}
		if not auction_peer in self.bidders[ip] or not self.bidders[ip][auction_peer]:
			self.loglist(['#B', peer, auction_peer])
			self.logline(str(timestamp))
			self.loglist([len(bitrates)])
			self.loglist(map(lambda rate:float(rate)/1024/1024,bitrates))
			self.loglist(prices)
		self.bidders[ip][auction_peer] = 1
	
	def transport_complete(self, ip, pack):
		# extract
		timestamp = time.time() - self.timestart
		bidder_ip, size, duration = eval(pack)
		from_peer = self.peername[ip]
		to_peer = self.peername[bidder_ip]
		# write to file
		self.loglist(['#T', from_peer, to_peer])
		self.logline(str(timestamp))
		self.loglist([float(size)/1024/1024, duration])
		

class LogClient(object):
	def __init__(self, code):
		self.code = code
		self.sender = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.sender.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
		self.sender_address = (setting.LOG_BROADCAST, setting.LOG_PORT)

	def send(self, message):
		self.sender.sendto(message, self.sender_address)

	def auction_broadcast(self, peer, k, capacity, cti, cda, cwda):
		pack = str([peer, k, capacity, cti, cda, cwda])
		self.send(':'.join(['A', pack]))

	def auction_decide(self, peer, bidder_ip, segments, bitrate, payment):
		pack = str([peer, bidder_ip, segments, bitrate, payment])
		self.send(':'.join(['D', pack]))

	def decide_complete(self, peer):
		self.send(':'.join(['C',peer]))

	def bid_send(self, peer, auction_peer, bid):
		pack = str([peer, auction_peer, bid])
		self.send(':'.join(['B', pack]))

	def transport_complete(self, bidder_ip, size, duration):
		pack = str([bidder_ip, size, duration])
		self.send(':'.join(['T', pack]))

if __name__=="__main__":
	server = LogServer()
	server.run()

