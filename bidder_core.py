#!usr/bin/env python
import setting 
import math

# TODO thread safe (dict)
class BidderCore(object):
	""" init with factory pattern , bider_params {param : values}"""
	def __init__(self, factory, bidder_params):
		self.factory = factory
		# M parameters
		self.basic_preference = setting.BIDDER_BASIC_TH if not 'theta' in bidder_params else bidder_params['theta']
		self.valuation_kqv = setting.BIDDER_K_QV if not 'kqv' in bidder_params else bidder_params['kqv']
		self.valuation_kbuf = setting.BIDDER_K_BUF if not 'kbuf' in bidder_params else bidder_params['kbuf']
		self.k_theta = bidder_params['ktheta']
		self.k_br = bidder_params['kbr']
		self.k_capacity = bidder_params['kcapacity']
		self.max_buffer_size = setting.BIDDER_MAX_BUF if not 'mbuf' in bidder_params else bidder_params['mbuf']
		self.current_buffer_size = 0
		self.previous_bitrate = 0

	""" event handler """
	# bid to auction @return bid : [a_peer, a_index, bid_details]
	def bid2auction(self, auction):
		if self.factory.buffer_size() > self.max_buffer_size:
			#print '[buffered]', self.factory.buffer_size()
			return None
		auction_peer,auction_index,segments,capacity,cti,cda,cwda = auction.split(',')
		auction_index = auction_index
		segments = int(segments)
		capacity = float(capacity) * self.k_capacity
		cti = float(cti)
		cda = float(cda)
		cwda = float(cwda)
		#print capacity,cti,cda,cwda
		bitrates = []
		prices = []
		gains = []
		for k in range(segments):
			rk = max(self.factory.rate_list, key =lambda r : self.utility(r, k+1, capacity, cti) - self.cost(r,k+1,capacity, cti, cda, cwda))
			bitrates.append(rk)
			price = self.utility(rk, k+1, capacity, cti)
			prices.append(price)
			gains.append(price - self.cost(rk,k+1,capacity, cti, cda, cwda))
		return (auction_peer, auction_index, (bitrates, prices, gains))

	def update_previous(self, rate):
		self.previous_bitrate = rate/1024/1024

	# functions
	# utility (assert capacity > 0)
	def utility(self, rate, k, capacity, cti):
		mrate = float(rate) / 1024 / 1024 
		kb =  k*self.factory.average_duration
		#depracated 1.0 : a = kb * math.log(1+self.preference()*self.valuation[rate])
		a = kb * math.log(1+math.sqrt(self.preference())*self.valuation(rate, cti))
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
		# deprecated 1.0 : return self.basic_preference + self.factory.buffer_size() / self.max_buffer_size
		return self.basic_preference + self.k_theta * self.factory.buffer_size() / self.max_buffer_size

	# valuation f(r)
	''' valuation depracated 1.0
		self.valuation = {}
		val = 1
		for rate in self.factory.rate_list:
			self.valuation[rate] = val
			val = val + 1
	'''
	def valuation(self, rate, cti):
		r = float(rate) / 1024 / 1024
		return self.k_br / math.sqrt(self.basic_preference + 0.5*self.k_theta) * math.exp(r *cti + r*r - 1)
# unit test
if __name__=="__main__":
	bidder = 'Bidder()' #Bidder()
	core = BidderCore(bidder)