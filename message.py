#!usr/bin/env python
# -*- coding: UTF-8 -*-
import socket
import select
import threading
import struct

'''
Message Protocol
'''
class MessageProtocol(object):
	def on_msg_from_peer(self, data, peer):
		pass
'''
Message
'''
class Message(object):

	def __init__(self, host, iport, oport, protocol):
		# properties
		self.host = host
		self.iport = iport
		self.oport = oport
		self.protocol = protocol
		self.socks = {} # {peer:sock}

	def message(self):
		# sockets
		self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		self.server.setblocking(False)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.bind((self.host, self.iport))
		self.server.listen(10)
		self.inputs = [self.server]
		self.peers = {} # {sock:peer}
		self.messages = {} # {sock:message}
		self.lengths = {} # {sock:length}
		self.timeout = 1.0
		while self.running:
			try:
				readable , writable , exceptional = select.select(self.inputs, [], self.inputs, self.timeout)
			except select.error,e:
				break
			# When timeout reached , select return three empty lists
			if not (readable or writable or exceptional) :
				continue 
			for s in readable:
				if s is self.server:
				    # A "readable" socket is ready to accept a connection
				    connection, address = s.accept()
				    connection.setblocking(0)
				    self.inputs.append(connection)
				    self.peers[connection] = address[0]
				elif s in self.peers:
					try:
						if not s in self.messages:
							bytes = s.recv(4)
							l, = struct.unpack('!i', bytes)
							bytes = s.recv(l)
							if len(bytes) == l:
								self.protocol.on_msg_from_peer(bytes, self.peers[s])
							else:
								self.messages[s] = bytes
								self.lengths[s] = l - len(bytes)
						else:
							l = self.lengths[s]
							bytes = s.recv(l)
							self.messages[s] = self.messages[s].append(bytes)
							if len(bytes) == l:
								self.protocol.on_msg_from_peer(bytes, self.peers[s])
								del self.messages[s]
								del self.lengths[s]
							else:
								self.lengths[s] = l - len(bytes)
					except:
						s.close()
						del self.peers[s]
						if s in self.messages:
							del self.messages[s]
							del self.lengths[s]
						self.inputs.remove(s)
					'''
				    bytes = s.recv(1024)
				    if bytes :
				    	self.protocol.on_msg_from_peer(bytes, self.peers[s])
				    else:
				        #Interpret empty result as closed connection
						del self.peers[s]
						self.inputs.remove(s)
					'''
			for s in exceptional:
				if s in self.peers:
					s.close()
					del self.peers[s]
					self.inputs.remove(s)
		self.server.close()

	def run(self):
		self.running = 1
		threading.Thread(target=self.message).start()

	def close(self):
		for peer in self.socks.keys():
			self.disconnect_peer_if_need(peer)
		self.running = 0

	# Open API
	def connect_peer_if_need(self, peer):
		if not peer in self.socks:
			try:
				# create a socket
				sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
				sock.connect((peer, self.oport))
				# TODO timeout, setblocking
				# save the socket
				self.socks[peer] = sock
			except:
				#print 'error when connect to peer', peer
				pass

	def disconnect_peer_if_need(self, peer):
		if peer in self.socks:
			sock = self.socks[peer]
			# delete socket 
			del self.socks[peer]
			# close socket
			sock.close()

	def sendto(self, peer, data):
		# TODO timeout or nonblocking
		self.connect_peer_if_need(peer)
		try:
			sock = self.socks[peer]
			pack = struct.pack('!i%ds' % len(data), len(data), data)
			sock.sendall(pack)
		except:
			sock.close()
			try:
				# renew the socket
				sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
				sock.connect((peer, self.port))
				self.socks[peer] = sock
				sock.sendall(pack)
			except:
				self.disconnect_peer_if_need(peer)

'''
Message Client
'''
class MessageClient(object):
	def __init__(self, port, protocol):
		# properties
		self.port = port
		self.protocol = protocol
		# sockets
		self.socks = {} # {peer:sock}

	# Open API
	def connect_peer_if_need(self, peer):
		if not peer in self.socks:
			try:
				# create a socket
				sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
				sock.connect((peer, self.port))
				# TODO timeout, setblocking
				# save the socket
				self.socks[peer] = sock
			except:
				#print 'error when connect to peer', peer
				pass

	def disconnect_peer_if_need(self, peer):
		if peer in self.socks:
			sock = self.socks[peer]
			# delete socket 
			del self.socks[peer]
			# close socket
			sock.close()

	def sendto(self, peer, data):
		# TODO timeout or nonblocking
		self.connect_peer_if_need(peer)
		try:
			sock = self.socks[peer]
			sock.sendall(data)
		except:
			sock.close()
			try:
				# renew the socket
				sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
				sock.connect((peer, self.port))
				self.socks[peer] = sock
				sock.sendall(data)
			except:
				self.disconnect_peer_if_need(peer)

	def close(self):
		for peer in self.socks.keys():
			self.disconnect_peer_if_need(peer)

'''
Message Server
'''
class MessageServer(object):

	def __init__(self, host, port, protocol):
		# properties
		self.host = host
		self.port = port
		self.protocol = protocol
		# sockets
		self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		self.server.setblocking(False)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.bind((host,port))
		self.server.listen(10)
		self.inputs = [self.server]
		self.peers = {} # {sock:peer}
		self.timeout = 1.0

	def listen(self):
		while self.running:
			try:
				readable , writable , exceptional = select.select(self.inputs, [], self.inputs, self.timeout)
			except select.error,e:
				break
			# When timeout reached , select return three empty lists
			if not (readable or writable or exceptional) :
				continue 
			for s in readable:
				if s is self.server:
				    # A "readable" socket is ready to accept a connection
				    connection, address = s.accept()
				    connection.setblocking(0)
				    self.inputs.append(connection)
				    self.peers[connection] = address[0]
				elif s in self.peers:
				    data = s.recv(1024)
				    if data :
				    	self.protocol.on_msg_from_peer(data, self.peers[s])
				    else:
				        #Interpret empty result as closed connection
						del self.peers[s]
						self.inputs.remove(s)
			for s in exceptional:
				if s in self.peers:
					del self.peers[s]
					self.inputs.remove(s)

	def run(self):
		self.running = 1
		threading.Thread(target=self.listen).start()

	def close(self):
		self.running = 0
