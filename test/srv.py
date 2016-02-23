#!usr/bin/env python
import socket
import select
import threading
import setting
import aulog

class Server(object):
	def __init__(self):
		self.bindAddr = (setting.HOST, setting.CTR_PORT)
		self.broadAddr = (setting.BROADCAST, setting.CTR_PORT)
		self.running = True 

	def listen(self):
		self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
		self.sock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
		self.sock.bind(self.bindAddr)
		while self.running:
			readable , writable , exceptional = select.select([self.sock], [], [], 0)
			for s in readable:
				if s is self.sock:
					data,addr=s.recvfrom(1024)
					aulog.ctrinfo(data,addr)
					#s.sendto("broadcasting",addr)
		self.sock.close()

	def console(self):
		while self.running:
			command = raw_input()
			if not command:
				break
			if command.lower() == 'exit':
				self.running = False
				print 'Bye bye~Message Center.'
			else:
				self.sock.sendto(command.lower(), self.broadAddr)

		self.running = False

	def run(self):
		self.listenThread = threading.Thread(target = self.listen)
		self.consoleThread = threading.Thread(target = self.console)
		self.listenThread.start()
		self.consoleThread.start()
		self.listenThread.join()
		self.consoleThread.join()

if __name__ == "__main__":
    server = Server()
    server.run()