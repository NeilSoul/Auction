#!usr/bin/env python
import threading
import setting
import argparse
import log
from message import Message
from transport import Transport

class App(object):
	def __init__(self, args):
		mhost, mport, mbroadcast, thost, tport, dname = args
		log.log_sys('arguments:',mhost, mport, mbroadcast, thost, tport, dname)
		self.message_center = Message(mhost, mport, mbroadcast, self.message_response)
		self.transport_center = Transport(thost, tport, dname, self.transport_response)

	def message_response(self, data, address):
		print 'message', data, address

	def transport_response(self, address, filepath):
		print 'transport', address, filepath

	def console(self):
		while True:
			command = raw_input()
			if not command:
				break
			if command.lower() == 'exit':
				break
			if command.lower() == 'test':
				self.transport_center.transport('0.0.0.0', 'auction.jpg', 'http://www.johannesauction.com/img/upload/auction-pic-1.jpg')
			else:
				self.message_center.send(command.lower())

		self.close()

	def close(self):
		self.message_center.close()
		self.transport_center.close()
		#log.log_sys('Close.')

	def run(self):
		self.consoleThread = threading.Thread(target = self.console)
		self.consoleThread.start()
		self.message_center.start()
		self.transport_center.start()
		self.consoleThread.join()
		self.message_center.join()
		self.transport_center.join()


def parse_args():
	# argument formats
	parser = argparse.ArgumentParser(description='AuctionTv')
	parser.add_argument('--mhost', required=False, help='message host')
	parser.add_argument('--mport', type=int, required=False, help='message port')
	parser.add_argument('--mbroadcast', required=False, help='message broadcast address')
	parser.add_argument('--thost', required=False, help='transport host')
	parser.add_argument('--tport', type=int, required=False, help='transport port')
	parser.add_argument('--dname', required=False, help='data folder path')
	args = parser.parse_args()
	# parse arguments
	mhost = setting.MSG_HOST if not args.mhost else args.mhost
	mport = setting.MSG_PORT if not args.mport else args.mport
	mbroadcast = setting.MSG_BROADCAST if not args.mbroadcast else args.mbroadcast
	thost = setting.TRP_HOST if not args.thost else args.thost
	tport = setting.TRP_PORT if not args.tport else args.tport
	dname = setting.TRP_DIR if not args.dname else args.dname
	return mhost, mport, mbroadcast, thost, tport, dname

if __name__ == "__main__":
	args = parse_args()
	app = App(args)
	app.run()
