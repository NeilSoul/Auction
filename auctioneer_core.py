#!usr/bin/env python

class AuctioneerCore(object):
	def __init__(self, factory, auctioneer_params):
		self.segment_number = auctioneer_params['segment']
		self.default_capacity = auctioneer_params['capacity']
		self.capacity = self.default_capacity
		self.cti = auctioneer_params['timecost']
		self.cda = auctioneer_params['cellular']
		self.cwda = auctioneer_params['wifi']
		self.factory = factory

	def estimate_capacity(self, capacity):
		self.capacity = capacity if capacity > 0 else self.default_capacity
		#print 'estimate', self.capacity

	def auction_message(self, index):
		inst = 'AUCTION'
		# Inefficient str() eval()
		return  ','.join([self.factory.peername, str(index), str(self.segment_number), str(self.capacity), 
			str(self.cti), str(self.cda), str(self.cwda)])

	# select bid @return {ip:(tasks, rate, payment)}
	def select_bid(self, bids):
		scores = {}
		payments = {}
		rates = {}
		p = {}
		k = 0
		for ip in bids:
			ra,pr,ga = eval(bids[ip])
			#print rates,prices,gains
			k = len(ra)
			rates[ip] = ra
			payments[ip] = pr
			scores[ip] = map(lambda i: ga[i] if i==0 else ga[i] - ga[i-1], range(k))
			p[ip] = 0 # assert (0,k-1)
		for i in range(k):
			ip = max(bids.keys(), key=lambda ip: scores[ip][p[ip]])
			p[ip] = p[ip] + 1
		result = {}
		for ip in p:
			if p[ip] > 0:
				result[ip] = (p[ip], rates[ip][p[ip]-1], payments[ip][p[ip]-1])
		return result

	# cost (assert capacity > 0)
	def cost(self, rate, k):
		kbr = k * DURATION * rate
		return self.cti *  kbr / self.capacity + self.cda * kbr + self.cwda * kbr

# unit test
if __name__=="__main__":
	auctioneer = 'Auctioneer()' #Auctioneer()
	core = AuctioneerCore(auctioneer)