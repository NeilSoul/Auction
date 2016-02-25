#!usr/bin/env python
import socket
import select
import threading
import argparse
import setting
import aulog

class Server(object):
	def __init__(self, host=setting.HOST, port=setting.CTR_PORT):
		self.bindAddr = (host, port)
		self.broadAddr = (setting.BROADCAST, port)
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
		self.sendsock =socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.sendsock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
		while self.running:
			command = raw_input()
			if not command:
				break
			if command.lower() == 'exit':
				self.running = False
				print 'Bye bye~Message Center.'
			else:
				self.sendsock.sendto(command.lower(), self.broadAddr)

		self.running = False
		self.sendsock.close()

	def run(self):
		self.listenThread = threading.Thread(target = self.listen)
		self.consoleThread = threading.Thread(target = self.console)
		self.listenThread.start()
		self.consoleThread.start()
		self.listenThread.join()
		self.consoleThread.join()

def parse_args():
	parser = argparse.ArgumentParser(description='SRV')
	parser.add_argument('--host', required=True, help='host')
	parser.add_argument('--port', type=int, required=True, help='port')
	return parser.parse_args()

if __name__ == "__main__":
	#args = parse_args()
	#server = Server(args.host, args.port)
	server = Server()
	server.run()