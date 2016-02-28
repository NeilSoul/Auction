#!usr/bin/env python
import socket
import select
import Queue
import threading
import log


""" 
Message Protocol
"""
class Protocol(object):
	def data_received(self, data, address):
		pass

"""
Message
"""
class Message(object):
	def __init__(self, lhost, lport, bhost, bport, protocol):
		self.running = True 
		#create a listenning socket
		self.server = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.server.setblocking(False)
		#set option reused
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.server_address= (lhost,lport)
		self.server.bind(self.server_address)
		#create a sending socket
		self.sender = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.sender.setblocking(False)
		self.sender.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
		self.bhost = bhost
		self.bport = bport
		 
		#Outgoing message queue
		self.message_queue = Queue.Queue()
		 
		#A optional parameter for select is TIMEOUT
		self.timeout = 3

		#Protocol of message
		self.protocol = protocol 

	def listen(self):
		while self.running:
			try:
				#print 'select block'
				readable , writable , exceptional = select.select([self.server], [], [], self.timeout)
			except select.error,e:
				#print 'select error'
				break
			# When timeout reached , select return three empty lists
			if not (readable or writable or exceptional) :
				#log.log_msg('TIMEOUT')
				continue
				#break;  
			#print 'select pass'  
			for s in readable :
				if s is self.server:
					# Receive message from broadcast
					data, address=s.recvfrom(1024)
					self.protocol.data_received(data, address)
		self.server.close()

	def receive(self, data, address):
		pass

	def message(self):
		while self.running:
			next_msg, next_ip = self.message_queue.get()
			try:
				self.sender.sendto(next_msg, (next_ip, self.bport))
			except:
				log.log_msg('send error')
		self.sender.close()
		del self.message_queue

	def sendto(self, ip, message):
		self.message_queue.put((message, ip))

	def broadcast(self, message):
		self.message_queue.put((message, self.bhost))

	def start(self):
		self.listenThread = threading.Thread(target = self.listen)
		self.messageThread = threading.Thread(target = self.message)
		self.listenThread.start()
		self.messageThread.start()

	def join(self):
		self.listenThread.join()
		self.messageThread.join()

	def close(self):
		self.running = False
		self.broadcast('EXIT')#important!
