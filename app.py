#!usr/bin/env python
import argparse
import setting
from auctioneer import Auctioneer
from bidder import Bidder

def parse_args():
	# argument formats
	parser = argparse.ArgumentParser(description='AuctionTv')
	parser.add_argument('--script', required=False, help='script file')
	return parser.parse_args()
	

if __name__ == "__main__":
	auctioneer  = Auctioneer()
	bidder  = Bidder()
	auctioneer.start()
	bidder.start()
	try:
		while True:
			command = raw_input().lower()
			if not command or command == 'exit':
				break
			elif command == 'play':
				auctioneer.play(setting.PLAYER_URL)
			else:
				print "Usage :"
				print "\tplay [url]\tPlay a streaming."
				print "\texit\t\tExit."
	except KeyboardInterrupt:
		pass
	auctioneer.close()
	bidder.close()
	bidder.join()
	auctioneer.join()
