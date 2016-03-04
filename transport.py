#!usr/bin/env python
"""TODO
join or not join
write index on data, no save at auctioneer
because maybe multi sock at one ..
"""

import socket
import select
import threading
import time
import urllib2
import os
import log

FILE_BOF = 'B'.encode()
FILE_SEP = '#'.encode()

""" 
Transport Protocol
Include server and client.
"""
class Protocol(object):
	''' server callback '''
	def receive_successed(self, index, list, address):
		pass
	def receive_failed(self, index, list, address):
		pass
	''' client callback '''
	def send_successed(self, index):
		pass
	def send_failed(self, index):
		pass

"""
Transport Server
"""
class TransportServer(object):
	def __init__(self, host, port, protocol):
		self.running = 1 
		#create a socket
		self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		self.server.setblocking(False)
		#set option reused
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR  , 1)
		self.server_address= (host,port)
		self.server.bind(self.server_address)
		self.server.listen(10)

		self.inputs = [self.server]
		#buffer indexs (socket : buffer index)
		self.indexs = {}
		#buffer lists (socket : list)
		self.lists = {}

		#A optional parameter for select is TIMEOUT
		self.timeout = 3

		#Protocol 
		self.protocol = protocol

	'Server Methods'
	def transport_made(self, sock, data):
		sep = data.find(FILE_SEP)
		index = data[1:sep].decode()
		self.indexs[sock] = index
		self.lists[sock] = []
		self.lists[sock].append(data[sep+1:])

	def transport_clear(self, sock, sucess=True):
		if sock in self.lists:
			if sucess:
				self.protocol.receive_successed(self.indexs[sock], self.lists[sock], sock.getpeername())
			else:
				self.protocol.receive_failed(self.indexs[sock], self.lists[sock], sock.getpeername())
			del self.indexs[sock]
			del self.lists[sock]
		if sock in self.inputs:
			self.inputs.remove(sock)
		sock.close()

	def receive(self, sock, data):
		if not sock in self.lists:
			if data.startswith(FILE_BOF):
				self.transport_made(sock, data)
		else:
			self.lists[sock].append(data)

	def listen(self):
		while self.running and self.inputs:
			try:
				readable , writable , exceptional = select.select(self.inputs, [], self.inputs, self.timeout)
			except select.error,e:
				break
			# When timeout reached , select return three empty lists
			if not (readable or writable or exceptional) :
				continue 
			for s in readable :
				if s is self.server:
				    # A "readable" socket is ready to accept a connection
				    connection, client_address = s.accept()
				    connection.setblocking(0)
				    self.inputs.append(connection)
				else:
				    data = s.recv(1024)
				    if data :
				    	self.receive(s, data)
				    else:
				        #Interpret empty result as closed connection
				        self.transport_clear(s)
			 
			for s in exceptional:
				#stop listening for input on the connection
				self.transport_clear(s, False)
		self.server.close()

	'Loop Methods'
	def start(self):
		self.listenThread = threading.Thread(target = self.listen)
		self.listenThread.start()

	def join(self):
		self.listenThread.join()

	def close(self):
		self.running = 0

"""
Transport Client
"""
class TransportClient(object):
	def __init__(self, port, protocol):
		self.port = port
		self.protocol = protocol

	# block function, return size(bytes), duration
	def transport(self, ip, index, from_url):
		# connect to sock
		data_length = 0
		tbegin = time.time()
		try:
			sock =socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			sock.connect((ip, self.port))
			data = FILE_BOF + str(index) + FILE_SEP
			sock.sendall(data)
			# http task
			f = urllib2.urlopen(from_url)
			while 1:
				data = f.read(1024)
				if not data:
					break
				sock.send(data)
				data_length += len(data)
			sock.close()
			self.protocol.send_successed(index)
		except:
			self.protocol.send_failed(index)
		tend = time.time()
		return data_length, tend-tbegin#data_length /(tend - tbegin)/1024/1024

	# thread function
	def ttransport(self, ip, index, from_url):
		t = threading.Thread(target=self.sendto, args=(ip,index,from_url))
		t.start()

