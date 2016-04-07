#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import socket
import select
import threading
import time

# Discovery Protocols
DIS_HOST = '0.0.0.0'
DIS_PORT = 5190

class DiscoveryProtocol(object):

	def onPeerJoin(self, peer):
		pass

	def onPeerLeave(self, peer):
		pass

class Discovery(object):

	def __init__(self, host, port, protocol):
		# open property
		self.host = host
		self.port = port
		self.protocol = protocol
		self.peers = {}# {peer:time_updated}
		# socket
		self.server = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.server.setblocking(False)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.server_address= (host,port)
		self.server.bind(self.server_address)
		self.sender = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.sender.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
		self.sender.setblocking(False)
		self.socket_timeout = 1
		# conditions
		self.broadcast_cond = threading.Condition()
		self.broadcast_timeout = 1
		self.refresh_cond = threading.Condition()
		self.refresh_timeout = 2


	def peerJoin(self, peer):
		if not peer in self.peers:
			self.peers[peer] = time.time()
			self.protocol.onPeerJoin(peer)
		else:
			self.peers[peer] = time.time()

	def peerLeave(self, peer):
		if peer in self.peers:
			del self.peers[peer]
			self.protocol.onPeerLeave(peer)

	def listen(self):
		while self.running:
			try:
				readable , writable , exceptional = select.select([self.server], [], [], self.socket_timeout)
			except select.error,e:
				break
			# When timeout reached , select return three empty lists
			if not (readable or writable or exceptional) :
				continue
			for s in readable :
				if s is self.server:
					# Receive message from broadcast
					try:
						data, address=s.recvfrom(1024)
						inst, info = data.split(':',1)
					except:
						continue
					# parse data
					if inst == 'JOIN':# a peer join
						self.peerJoin(address[0])
					elif inst == 'LEAVE':# a peer leave
						self.peerLeave(address[0])
		self.server.close()

	def broadcast(self):
		while self.running:
			try:
				self.sender.sendto('JOIN:', (self.host, self.port))
			except:
				pass
			self.broadcast_cond.acquire()
			self.broadcast_cond.wait(self.broadcast_timeout)
			self.broadcast_cond.release()
		self.sender.sendto('LEAVE:', (self.host, self.port))
		self.sender.close()

	def refresh(self):
		while self.running:
			current = time.time()
			for peer in self.peers:
				if current - self.peers[peer] > self.refresh_timeout:
					self.peerLeave(peer)
			self.refresh_cond.acquire()
			self.refresh_cond.wait(self.refresh_timeout)
			self.refresh_cond.release()

	def run(self):
		self.running = 1
		threading.Thread(target=self.listen).start()
		threading.Thread(target=self.broadcast).start()
		threading.Thread(target=self.refresh).start()

	def close(self):
		self.broadcast_cond.acquire()
		self.broadcast_cond.notify()
		self.broadcast_cond.release()
		self.refresh_cond.acquire()
		self.refresh_cond.notify()
		self.refresh_cond.release()
		self.running = 0

# UNION TEST
class UnitTest(DiscoveryProtocol):

	def __init__(self):
		self.discovery = Discovery('0.0.0.0', 5190, self)

	def onPeerJoin(self, peer):
		print peer, 'join.'

	def onPeerLeave(self, peer):
		print peer, 'leave.'

	def test(self):
		self.discovery.run()
		for i in range(10):
			print self.discovery.peers
			time.sleep(1.0)
		self.discovery.close()

if __name__ == '__main__':
	unit = UnitTest()
	unit.test()

