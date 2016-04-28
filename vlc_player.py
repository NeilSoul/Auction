#!/usr/bin/env python
# -*- coding : UTF-8 -*-
import os
import sys
import time
import vlc
from threading import Thread
from Queue import Queue
import setting

class VlcPlayer(object):
	"""A simple Media Player using VLC
	"""
	def __init__(self, master=None):
		# creating a basic vlc instance
		self.instance = vlc.Instance()
		# creating an empty vlc media player
		self.mediaplayer = self.instance.media_player_new()
		self.isplaying = 0
		# file source
		self.buffer_queue = Queue()

	def main_loop(self):
		while True:
			try:
				self.updateUI()
				time.sleep(0.2)
			except KeyboardInterrupt:
				break

	def updateUI(self): #0.2s
		"""updates the user interface"""
		if self.isplaying and not self.mediaplayer.is_playing():
			# no need to call this function if nothing is played
			self.isplaying = 0
			#self.mediaplayer.stop()#TO REMOVE
			print 'DEBUG', 'one end'
		"""scan file changes"""
		self.cnt = self.cnt + 1
		if self.cnt >= 5:
			# see if player is idle
			if not self.isplaying:
				self.play_media_if_prepared()
			# clear counter
			self.cnt = 0
			
			

	def buffer_media(self, filename):
		# create the media
		if sys.version < '3':
			filename = unicode(filename)
		media = self.instance.media_new(filename)
		media.parse()
		self.buffer_queue.put(media)
		print 'buffer media', filename

	def play_media_if_prepared(self):
		try:
			media = self.buffer_queue.get_nowait()
			self.mediaplayer.set_media(media)
			# play
			self.mediaplayer.play()
			time.sleep(1.0)#wating time..
			self.isplaying = 1
			print 'DEBUG', 'one start'
		except Exception,e:
			print 'DEBUG', 'one get failed',e

	'Open API'
	def open_api_run(self):
		print 'INFO', 'player run'
		self.open_running = 1
		self.origin = set()
		Thread(target=self.open_api_scan).start()
		# start app
		self.cnt = 0
		self.main_loop()
		self.open_api_exit()

	def open_api_exit(self):
		self.open_running = 0
		self.mediaplayer.stop()	
		print 'INFO', 'player exit'

	def open_api_scan(self):
		while self.open_running:
			# update sources
			current = set([_f[2] for _f in os.walk(setting.BUFFER_DIR)][0])
			delta = list(current.difference(self.origin))
			delta.sort()
			for fname in delta:
				if fname.endswith('.ts'):
					self.buffer_media(os.path.join(setting.BUFFER_DIR,fname))
			self.origin = current
			# tick
			time.sleep(1.0)


# UNIT TEST
if __name__ == '__main__':
	player = VlcPlayer()
	player.open_api_run()




