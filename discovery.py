#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import socket
import select
import threading
import time

class Broadcaster(object):

	def __init__(self, bcast, port):
		# open property
		self.bcast = bcast
		self.port = port
		# timeout & close conditions
		self.bcast_close_cond = threading.Condition()
		self.bcast_timeout = 0.3

	def _broadcast(self):
		# sender socket
		self.sender = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.sender.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
		#self.sender.setblocking(False)
		while self.running:
			try:
				self.sender.sendto('JOIN', (self.bcast, self.port))
			except:
				pass
			self.bcast_close_cond.acquire()
			self.bcast_close_cond.wait(self.bcast_timeout)
			self.bcast_close_cond.release()
		try:
			self.sender.sendto('LEAV', (self.bcast, self.port))
		except:
			pass
		self.sender.close()

	def run(self):
		self.running = 1
		threading.Thread(target=self._broadcast).start()

	def close(self):
		self.running = 0
		self.bcast_close_cond.acquire()
		self.bcast_close_cond.notify()
		self.bcast_close_cond.release()
		

class ListenerProtocol(object):

	def on_peer_join(self, peer):
		pass

	def on_peer_leave(self, peer):
		pass

class Listener(object):

	def __init__(self, host, port, protocol):
		# open property
		self.host = host
		self.port = port
		self.protocol = protocol
		self.peers = {}# {peer:time_updated}
		# refresh timeout & close conditions
		self.refresh_close_cond = threading.Condition()
		self.refresh_timeout = 3


	def _add_peer_if_need(self, peer):
		if not peer in self.peers:
			self.peers[peer] = time.time()
			self.protocol.on_peer_join(peer)
		else:
			self.peers[peer] = time.time()

	def _remove_peer_if_need(self, peer):
		if peer in self.peers:
			del self.peers[peer]
			self.protocol.on_peer_leave(peer)

	def _listen(self):
		# server socket
		self.server = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.server.setblocking(False)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.server.bind((self.host,self.port))
		# socket timeout
		self.socket_timeout = 1
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
						data, address=s.recvfrom(4)
						if data == 'JOIN':# a peer join
							self._add_peer_if_need(address[0])
						elif data == 'LEAV':# a peer leave
							self._remove_peer_if_need(address[0])
					except:
						continue
		self.server.close()

	def _refresh(self):
		while self.running:
			current = time.time()
			for peer in self.peers.keys():
				if current - self.peers[peer] > self.refresh_timeout:
					self._remove_peer_if_need(peer)
			self.refresh_close_cond.acquire()
			self.refresh_close_cond.wait(self.refresh_timeout)
			self.refresh_close_cond.release()

	def run(self):
		self.running = 1
		threading.Thread(target=self._listen).start()
		threading.Thread(target=self._refresh).start()

	def close(self):
		self.running = 0
		self.refresh_close_cond.acquire()
		self.refresh_close_cond.notify()
		self.refresh_close_cond.release()
		

# UNIT TEST
class ListenerUnitTest(ListenerProtocol):

	def __init__(self):
		self.listener = Listener('0.0.0.0', 9001, self)

	def on_peer_join(self, peer):
		print peer, 'join.'

	def on_peer_leave(self, peer):
		print peer, 'leave.'

	def run(self):
		self.listener.run()

	def close(self):
		self.listener.close()

if __name__ == '__main__':
	b = Broadcaster('<broadcast>', 9001)
	b.run()
	l = ListenerUnitTest()
	l.run()
	for i in range(3):
		print l.listener.peers
		time.sleep(1.0)
	b.close()
	for i in range(3):
		print l.listener.peers
		time.sleep(1.0)
	l.close()

	

