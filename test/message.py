#!usr/bin/env python
import socket
import select
import Queue
import threading
import setting
import aulog

class Message(object):
	def __init__(self, host=setting.MSG_HOST, port=setting.MSG_PORT):
		self.running = True 
		#create a listenning socket
		self.server = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.server.setblocking(False)
		#set option reused
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.server_address= (host,port)
		self.server.bind(self.server_address)
		#create a sending socket
		self.sender = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.sender.setblocking(False)
		self.sender.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
		self.sender_address = (setting.MSG_BROADCAST, port)
		#sockets from which we except to read
		self.inputs = [self.server]
		 
		#sockets from which we expect to write
		self.outputs = [self.sender]
		 
		#Outgoing message queue
		self.message_queue = Queue.Queue()
		 
		#A optional parameter for select is TIMEOUT
		self.timeout = 0

	def listen(self):
		while self.running:
			#print "waiting for next event"
			readable , writable , exceptional = select.select(self.inputs, self.outputs, self.inputs, self.timeout)

			# When timeout reached , select return three empty lists
			if not (readable or writable or exceptional) :
				print "Time out ! "
				break;    
			for s in readable :
				if s is self.server:
					# Receive message from broadcast
					data, address=s.recvfrom(1024)
					aulog.ctrinfo(data, address)
			for s in writable:
				if s is self.sender:
				    try:
				        next_msg = self.message_queue.get_nowait()
				    except Queue.Empty:
				    	#aulog.ctrinfo('braodcasting error', 'queue empty')
				    	continue
				    else:
				    	aulog.ctrinfo('broadcasting', next_msg)
				        s.sendto(next_msg, self.sender_address)
			 
			for s in exceptional:
				print " exception condition on ", s.getpeername()
				#stop listening for input on the connection
				if s in inputs:
					inputs.remove(s)
				if s in outputs:
				    outputs.remove(s)
				s.close()
		self.server.close()
		self.sender.close()
		del self.message_queue

	def console(self):
		while self.running:
			command = raw_input()
			if not command:
				break
			if command.lower() == 'exit':
				self.running = False
				print 'Bye bye~Message Center.'
			else:
				self.message_queue.put(command.lower())
		# Mark to break
		self.running = False
		
	def run(self):
		self.listenThread = threading.Thread(target = self.listen)
		self.consoleThread = threading.Thread(target = self.console)
		self.listenThread.start()
		self.consoleThread.start()
		self.listenThread.join()
		self.consoleThread.join()

if __name__ == "__main__":
	message_center = Message()
	message_center.run()