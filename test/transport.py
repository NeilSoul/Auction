#!usr/bin/env python
import socket
import select
import Queue
import setting
import aulog

class Transport(object):
	def __init__(self, host=setting.TRP_HOST, port=setting.TRP_PORT):
		self.running = True 
		#create a socket
		self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		self.server.setblocking(False)
		#set option reused
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR  , 1)
		self.server_address= (host,port)
		self.server.bind(self.server_address)
		 
		self.server.listen(10)
		#sockets from which we except to read
		self.inputs = [self.server]
		 
		#sockets from which we expect to write
		self.outputs = []
		 
		#Outgoing message queue (socket:Queue)
		self.message_queues = {}
		 
		#A optional parameter for select is TIMEOUT
		self.timeout = 0

	def listen(self):
		while self.running and inputs:
			print "waiting for next event"
			readable , writable , exceptional = select.select(inputs, outputs, inputs, timeout)

			# When timeout reached , select return three empty lists
			if not (readable or writable or exceptional) :
		    	print "Time out ! "
		    	break;    
			for s in readable :
		    	if s is self.server:
			        # A "readable" socket is ready to accept a connection
			        connection, client_address = s.accept()
			        print "    connection from ", client_address
			        connection.setblocking(0)
			        self.inputs.append(connection)
			        self.message_queues[connection] = Queue.Queue()
			    else:
			        data = s.recv(1024)
			        if data :
			            print " received " , data , "from ",s.getpeername()
			            self.message_queues[s].put(data)
			            # Add output channel for response    
			            if s not in self.outputs:
			                self.outputs.append(s)
			        else:
			            #Interpret empty result as closed connection
			            print "  closing", client_address
			            if s in self.outputs :
			                self.outputs.remove(s)
			            self.inputs.remove(s)
			            s.close()
			            #remove message queue 
			            del self.message_queues[s]
			for s in writable:
			    try:
			        next_msg = self.message_queues[s].get_nowait()
			    except Queue.Empty:
			        print " " , s.getpeername() , 'queue empty'
			        outputs.remove(s)
			    else:
			        print " sending " , next_msg , " to ", s.getpeername()
			        s.send(next_msg)
			 
			for s in exceptional:
			    print " exception condition on ", s.getpeername()
			    #stop listening for input on the connection
			    inputs.remove(s)
			    if s in outputs:
			        outputs.remove(s)
			    s.close()
			    #Remove message queue
			    del message_queues[s]
	def sendfile(self, address, fname):
		sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		sock.setblocking(False) #TODO
		sock.connect(address)
		self.outputs.append(sock)

	def run(self):
		self.listenThread = threading.Thread(target = self.listen)
		self.listenThread.start()
		self.listenThread.join()

if __name__ == "__main__":
	#args = parse_args()
	#server = Server(args.host, args.port)
	server = Server()
	server.run()