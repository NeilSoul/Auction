import socket
import select
import setting

class LogServer(object):
	def __init__(self):
		self.server_address = (setting.LOG_HOST, setting.LOG_PORT)
		self.server = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.server.setblocking(False)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self.server.bind(self.server_address)
		self.timeout = 3

	def run(self):
		while True:
			try:
				readable , writable , exceptional = select.select([self.server], [], [], self.timeout)
			except select.error,e:
				break
			# When timeout reached , select return three empty lists
			if not (readable or writable or exceptional) :
				continue  
			for s in readable :
				if s is self.server:
					data, address=s.recvfrom(1024)
					self.receive(data, address)

		self.server.close()

	def receive(self, data, address):
		print data, address

class LogClient(object):
	def __init__(self, code):
		self.code = code
		self.sender = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.sender.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
		self.sender_address = (setting.LOG_BROADCAST, setting.LOG_PORT)

	def send(self, message):
		self.sender.sendto(message, self.sender_address)

if __name__=="__main__":
	server = LogServer()
	server.run()

