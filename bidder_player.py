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
		self.fname_of_buffer = factory.fname_of_buffer
		self.command_of_player = factory.command_of_player

	def prepare2play(self):
		print '[m3u8 parsing]... url = ', self.url
		self.descriptor_list = parse_m3u8(self.url)
		self.rate_list = sorted(self.descriptor_list[0][1].keys())
		# streaming parameters
		self.segment_number = len(self.descriptor_list)
		self.segment_duration = self.descriptor_list[0][0]
		self.max_rate = self.rate_list[-1]
		print '[m3u8 parsed] segments = ', len(self.descriptor_list),'duration = ', self.segment_duration, 
		print '(s), rates = ', map(lambda r:float(r)/1024/1024, self.rate_list), '(mbps)'
		# clear player
		self.clear_player()
		# mark for real streaming 
		self.had_actually_played = 0

	def clear_player(self):
		try:
			os.remove(self.fname_of_buffer)
		except:
			pass

	def play(self):
		self.running = 1
		# streaming engine
		self.played_queue = Queue() # [(index, bytes_of_data)]
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
				index, bytes = self.played_queue.get(timeout=1)
			except:
				continue
			# record rebuffer
			delay = time.time() - playing_mark
			rebuffer += delay
			duration = self.descriptor_list[index][0]
			print '[playing ]No.', index, ', duration = ', duration, '(s), delay = ', round(delay,3), '(s), buffer =', self.get_buffer(), '(s), rebuffer = ', round(rebuffer,3) ,'(s)'
			# write into real file
			if not self.silent:
				wstart = time.time()
				try:
					with open(self.fname_of_buffer, 'ab') as f:
						#buffered
						f.write(bytes)
						if not self.had_actually_played :
							threading.Thread(target = self.realstreaming).start()
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

	def realstreaming(self):
		self.had_actually_played = 1
		p = subprocess.Popen(self.command_of_player.split() + [self.fname_of_buffer],stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		p.wait()
		self.factory.close()

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
	def segment_received(self, index, data):
		played_entry = (index, data)
		self.played_queue.put(played_entry)




