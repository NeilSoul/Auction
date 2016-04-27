#!usr/bin/env python
# -*- coding: utf-8 -*-
import os
import threading
import subprocess
import time
from Queue import Queue
from parser import parse_m3u8

class BidderPlayer(object):
	def __init__(self, factory):
		self.factory = factory
		self.url = factory.streaming_url
		self.silent = factory.silent
		self.buffer_folder = factory.buffer_folder

	def prepare2play(self):
		print '[B  parsing m3u8] url = %s ...' % self.url
		self.descriptor_list = parse_m3u8(self.url)
		self.rate_list = sorted(self.descriptor_list[0][1].keys())
		# streaming parameters
		self.segment_number = len(self.descriptor_list)
		self.segment_duration = self.descriptor_list[0][0]
		self.max_rate = self.rate_list[-1]
		print '[B  parsing finished] segments=%d, duration=%0.2f(s), rates=%s (mbps)' % (len(self.descriptor_list), self.segment_duration, str(map(lambda r:float(r)/1024/1024, self.rate_list)))
		# clear player
		self.clear_player()
		# mark for real streaming 
		self.had_actually_played = 0

	def clear_player(self):
		files = os.listdir(self.buffer_folder)
		try:
			for f in files:
				filePath = os.path.join(self.buffer_folder, f)
				if os.path.isfile(filePath):
					os.remove(filePath)
		except Exception, e:
			print e

	def play(self):
		self.running = 1
		# streaming engine
		self.played_queue = Queue() # [(index, bytes_of_data)]
		'''if self.silent:# at first full buffer , SPECIAL
			buffer_num = self.factory.bidder_params['mbuf'] / self.segment_duration
			for i in range(int(buffer_num)):
				self.played_queue.put((0, None))'''
		self.played_cond = threading.Condition()
		threading.Thread(target = self.streaming).start()

	def close(self):
		self.played_cond.acquire()
		self.played_cond.notify()
		self.played_cond.release()
		self.clear_player()
		self.running = 0

	def streaming(self):
		rebuffer = 0
		playing_mark = time.time()
		while self.running:
			try:
				index, segment = self.played_queue.get(timeout=1)
				f_rate, bytes = segment
			except:
				continue
			# record rebuffer
			delay = time.time() - playing_mark
			rebuffer += delay
			duration = self.descriptor_list[index][0]
			print '[B    playing] No.%d, rate=%0.2f(mbps), duration=%0.2f(s), delay=%0.2f(s), buffer=%0.2f(s), rebuffer=%0.2f(s)' % (index, f_rate, duration, delay, self.get_buffer(), rebuffer)
			#logging
			self.factory.logger.slave_play([f_rate, duration, delay])
			# write into real file
			if not self.silent:
				wstart = time.time()
				try:
					fname = os.path.join(self.buffer_folder, str(index).zfill(3)+".ts")
					with open(fname, 'w') as f:
						f.write(bytes)
						f.close()
				finally:
					duration -= time.time() - wstart
					if duration < 0:
						duration = 0.0
			#time.sleep(duration)
			self.played_cond.acquire()
			self.played_cond.wait(duration)
			self.played_cond.release()
			# mark 
			playing_mark = time.time()
			# if the end?
			if index >= self.segment_number - 1:
				break 

	''' descriptor info '''
	def get_segment_number(self):
		return self.segment_number

	def get_segment_duration(self):
		return self.segment_duration

	def get_segment_url(self, index, rate):
		descriptor = self.descriptor_list[index]
		duration = descriptor[0]
		url = descriptor[1][rate]
		return url

	def get_rate_list(self):
		return self.rate_list

	def get_max_rate(self):
		return self.max_rate

	''' player info '''
	def get_buffer(self):
		return self.played_queue.qsize() * self.segment_duration

	''' control '''
	def segment_received(self, index, segment):
		played_entry = (index, segment)
		self.played_queue.put(played_entry)




