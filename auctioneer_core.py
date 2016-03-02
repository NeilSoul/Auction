#!usr/bin/env python
# M parameters
AUCTIONEER_DEFAULT_CAPACITY = 1 # default capacity
AUCTIONEER_COST_TI = 0.15 # cost coefficients
AUCTIONEER_COST_DA = 0.15
AUCTIONEER_COST_WDA = 0.01

class AuctioneerCore(object):
	def __init__(self, factory):
		self.segment_number = factory.segment_number
		self.capacity = AUCTIONEER_DEFAULT_CAPACITY
		self.cti = AUCTIONEER_COST_TI
		self.cda = AUCTIONEER_COST_DA
		self.cwda = AUCTIONEER_COST_WDA
		self.factory = factory

	def estimate_capacity(self, capacity):
		self.capacity = capacity if capacity > 0 else AUCTIONEER_DEFAULT_CAPACITY

	def auction_message(self):
		inst = 'AUCTION'
		# Inefficient str() eval()
		return  ','.join([self.factory.peername, str(self.segment_number), str(self.capacity), 
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