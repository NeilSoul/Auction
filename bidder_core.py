#!usr/bin/env python
import math
# M paramters
BIDDER_BASIC_TH = 1.0 # basic preference
BIDDER_MAX_BUF = 50 # maximum buffer size
BIDDER_K_QV = 0.1
BIDDER_K_BUF = 0.002

# TODO thread safe
class BidderCore(object):
	def __init__(self, factory):
		self.factory = factory
		# M parameters
		self.valuation_kqv = BIDDER_K_QV
		self.valuation_kbuf = BIDDER_K_BUF
		self.current_buffer_size = 0
		self.previous_bitrate = 0
		self.max_buffer_size = BIDDER_MAX_BUF
		# valuation
		self.valuation = {}
		val = 1
		for rate in self.factory.rate_list:
			self.valuation[rate] = val
			val = val + 1
	""" event handler """
	# auction @return auction_peer, bid
	def handle_auction(self, auction):
		if self.factory.buffer_size() > self.max_buffer_size:
			#print '[buffered]', self.factory.buffer_size()
			return None, None
		auction_peer,segments,capacity,cti,cda,cwda = auction.split(',')
		segments = int(segments)
		capacity = float(capacity)
		cti = float(cti)
		cda = float(cda)
		cwda = float(cwda)
		#print capacity,cti,cda,cwda
		bitrates = []
		prices = []
		gains = []
		for k in range(segments):
			rk = max(self.factory.rate_list, key =lambda r : self.utility(r, k+1, capacity) - self.cost(r,k+1,capacity, cti, cda, cwda))
			bitrates.append(rk)
			price = self.utility(rk, k+1, capacity)
			prices.append(price)
			gains.append(price - self.cost(rk,k+1,capacity, cti, cda, cwda))
		return auction_peer, (bitrates, prices, gains)

	def update_previous(self, rate):
		self.previous_bitrate = rate/1024/1024

	# functions
	# utility (assert capacity > 0)
	def utility(self, rate, k, capacity):
		mrate = float(rate) / 1024 / 1024 
		kb =  k*self.factory.average_duration
		a = kb * math.log(1+self.preference()*self.valuation[rate])
		b = self.valuation_kqv*(self.previous_bitrate - mrate) if self.previous_bitrate - rate > 0 else 0
		T = k*self.factory.max_rate /1024/1024/capacity
		buffer_current = self.factory.buffer_size() 
		c1 = buffer_current - T if buffer_current-T > 0 else 0
		c = self.valuation_kbuf*(2*kb*(self.max_buffer_size - c1) - kb*kb)
		return a  - b + c

	# cost (assert capacity > 0)
	def cost(self, rate, k, capacity, cti, cda, cwda):
		mrate = float(rate) / 1024 / 1024
		kbr = k * self.factory.average_duration * mrate
		return cti *  kbr / capacity + cda * kbr + cwda * kbr

	# preference
	def preference(self):
		return BIDDER_BASIC_TH + self.factory.buffer_size() / self.max_buffer_size

# unit test
if __name__=="__main__":
	bidder = 'Bidder()' #Bidder()
	core = BidderCore(bidder)