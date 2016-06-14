#!/usr/bin/env python
# -*- coding : UTF-8 -*-
import os
import time
import pyglet
from Queue import Queue
import setting

class PygletPlayer(pyglet.window.Window):

	def __init__(self,caption):
		super(PygletPlayer,self).__init__(caption=caption,resizable=True)
		self.player = None
		self.source_queue = Queue()
		self.width = 320
		self.height = 207

	def on_draw(self):
		self.clear()
		if self.player and self.player.source and self.player.source.video_format:
			texture = self.player.get_texture()
			if texture:
				texture.blit(0,0, width=self.width, height=self.height)
			else:
				self.player.pause()
				self.player = None
				print 'DEBUG', 'texture failed'
		elif self.player:
			self.player.pause()
			self.player = None
			print 'DEBUG', 'source failed'

	'Open API'
	def open_api_run(self):
		self.open_running = 1
		self.origin = set()
		self.cnt = 0
		pyglet.clock.schedule_interval(self.open_api_scan, 1/60.0)
		pyglet.app.run()

	def open_api_exit(self):
		self.open_running = 0
		pyglet.app.exit()	

	def open_api_scan(self, sec):
		self.cnt = self.cnt + 1
		if self.cnt >= 60:
			# update sources
			current = set([_f[2] for _f in os.walk(setting.BUFFER_DIR)][0])
			delta = list(current.difference(self.origin))
			delta.sort()
			for fname in delta:
				if fname.endswith('.ts'):
					source = pyglet.media.load(os.path.join(setting.BUFFER_DIR, fname))
					#self.player.queue(source)
					print 'add', fname
					self.source_queue.put(source)
			self.origin = current
			# clear counter
			self.cnt = 0
		elif self.cnt % 10 == 0:
			# see if need to set player
			if not self.player:
				try:
					source = self.source_queue.get_nowait()
					self.player = source.play()
					print 'DEBUG', 'update player'
				except:
					pass

# UNIT TEST
if __name__ == '__main__':
	a = PygletPlayer('MyPlayer') 
	print 'INFO', 'player run'
	a.open_api_run()
	print 'INFO', 'player exit'
	a.open_api_exit()




