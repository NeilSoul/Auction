#!usr/bin/env python
import socket
import select
import Queue
import threading

""" 
Message Protocol
Include sever and client.
"""
class Protocol(object):
	''' server callback '''
	def data_received(self, data, ip):
		pass
	''' client callback '''
	def send_sucessed(self, data, ip):
		pass
	def send_failed(self, data, ip):
		pass

"""
Message Server & Message Client
"""
class MessageServer(object):
	def __init__(self, host, port, protocol):
		self.running = 1 
		#create a listenning socket
		self.server = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.server.setblocking(False)
		#set option reused
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.server_address= (host,port)
		self.server.bind(self.server_address)
		#A optional parameter for select  is TIMEOUT
		self.timeout = 1
		#Protocol of message
		self.protocol = protocol 

	def listen(self):
		while self.running:
			try:
				readable , writable , exceptional = select.select([self.server], [], [], self.timeout)
			except select.error,e:
				break
			# When timeout reached , select return three empty lists
			if not (readable or writable or exceptional) :
				continue
			for s in readable :
				if s is self.server:
					# Receive message from broadcast
					data, address=s.recvfrom(1024)
					self.protocol.data_received(data, address[0])
		self.server.close()

	def start(self):
		self.listenThread = threading.Thread(target = self.listen)
		self.listenThread.start()

	def join(self):
		self.listenThread.join()

	def close(self):
		self.running = 0

class MessageClient(object):
	def __init__(self, broadcast, port, protocol):
		self.running = 1
		#create a sending socket
		self.sender = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.sender.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
		self.sender.setblocking(False)
		self.broadhost = broadcast
		self.port = port
		#Outgoing message queue
		self.message_queue = Queue.Queue()
		#A optional parameter for  queue is TIMEOUT
		self.timeout = 1
		#Protocol of message
		self.protocol = protocol 

	def message(self):
		while self.running:
			try:
				next_msg, next_ip = self.message_queue.get(timeout=self.timeout)
			except:
				# When timeout reached , Queue raise an Empty Error
				continue
			try:
				self.sender.sendto(next_msg, (next_ip, self.port))
			except:
				self.protocol.send_failed(next_msg, next_ip)
		self.sender.close()
		#del self.message_queue

	def sendto(self, ip, message):
		self.message_queue.put((message, ip))

	def broadcast(self, message):
		self.message_queue.put((message, self.broadhost))

	def start(self):
		self.messageThread = threading.Thread(target = self.message)
		self.messageThread.start()

	def join(self):
		self.messageThread.join()

	def close(self):
		self.running = 0
		#self.message_queue.put(("EXIT", "ERROR_IP"))#important!
