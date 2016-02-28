#!usr/bin/env python
import socket
import select
import threading
import urllib2
import os
import log

FILE_BOF = 'B'.encode()
FILE_SEP = '#'.encode()

class FManager(object):
	@staticmethod 
	def start(filepath):
		try:
			fd = open(filepath, 'w')
			fd.close()
		except:
			log.log_trp('file create error', filepath)

	@staticmethod
	def append(data, filepath):
		try:
			fd = open(filepath, 'ab')
			fd.write(data)
			fd.close()
		except:
			log.log_trp('file append error', filepath)

class Transport(object):
	def __init__(self, host, port, dname, callback):
		self.running = True 
		#create a socket
		self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		self.server.setblocking(False)
		#set option reused
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR  , 1)
		self.server_address= (host,port)
		self.port = port
		self.server.bind(self.server_address)
		self.server.listen(10)

		self.inputs = [self.server]
		# (socket : filepath)
		self.files = {}

		#A optional parameter for select is TIMEOUT
		self.timeout = 5
		self.folder_path = dname
		self.callback = callback

	'Server Methods'
	def transport_made(self, sock, data):
		sep = data.find(FILE_SEP)
		file_name = data[1:sep].decode()
		file_path = os.path.join(self.folder_path, file_name)
		self.files[sock] = file_path
		FManager.start(file_path)
		FManager.append(data[sep+1:], file_path)
		return

	def transport_clear(self, sock):
		if sock in self.files:
			self.callback(sock.getpeername(), self.files[sock])
			del self.files[sock]
		if sock in self.inputs:
			self.inputs.remove(sock)
		sock.close()

	def receive(self, sock, data):
		if not sock in self.files:
			if data.startswith(FILE_BOF):
				self.transport_made(sock, data)
		else:
			file_path = self.files[sock]
			FManager.append(data, file_path)

	def listen(self):
		while self.running and self.inputs:
			try:
				readable , writable , exceptional = select.select(self.inputs, [], self.inputs, self.timeout)
			except select.error,e:
				break
			# When timeout reached , select return three empty lists
			if not (readable or writable or exceptional) :
				#log.log_trp("Time out ! ")
				continue
				#break;    
			for s in readable :
				if s is self.server:
				    # A "readable" socket is ready to accept a connection
				    connection, client_address = s.accept()
				    #log.log_trp("connection from ", client_address)
				    connection.setblocking(0)
				    self.inputs.append(connection)
				else:
				    data = s.recv(1024)
				    if data :
				    	self.receive(s, data)
				    else:
				        #Interpret empty result as closed connection
				        #log.log_trp("complete", s.getpeername())
				        self.transport_clear(s)
			 
			for s in exceptional:
				#log.log_trp("exception condition on ", s.getpeername())
				#stop listening for input on the connection
				self.transport_clear(s)
		self.server.close()

	'Client Methods'
	def transport(self, ip, filename, data_from_url):
		# connect to sock
		try:
			sock =socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			sock.connect((ip, self.port))
			data = FILE_BOF + filename.encode() + FILE_SEP
			sock.sendall(data)
			# http task
			f = urllib2.urlopen(data_from_url)
			while True:
				data = f.read(1024)
				if not data:
					break
				sock.send(data)
				#log.log_trp('downloading...', len(data))
			sock.close()
		except:
			log.log_trp('transport error')

	'Loop Methods'
	def start(self):
		self.listenThread = threading.Thread(target = self.listen)
		self.listenThread.start()

	def join(self):
		self.listenThread.join()

	def close(self):
		self.running = False
		#trick to active select. (without timeout)
		sock =socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		sock.connect(self.server_address)

def callback(from_address, file_path):
	print from_address, file_path

if __name__ == "__main__":
	transport_center = Transport('0.0.0.0', 9002, './O', callback)
	transport_center.start()