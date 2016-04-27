#!/usr/bin/env python
# -*- coding : UTF-8 -*-
import os
import sys
import time
import vlc
from threading import Thread
from PyQt4 import QtGui, QtCore
from Queue import Queue
import setting

class QtvlcPlayer(QtGui.QMainWindow):
	"""A simple Media Player using VLC and Qt
	"""
	def __init__(self, master=None):
		# create app before
		self.app = QtGui.QApplication(sys.argv)
		QtGui.QMainWindow.__init__(self, master)
		self.setWindowTitle("Media Player")

		# creating a basic vlc instance
		self.instance = vlc.Instance()
		# creating an empty vlc media player
		self.mediaplayer = self.instance.media_player_new()
		self.isplaying = 0
		
		self.createUI()

		# the media player has to be 'connected' to the QFrame
		# (otherwise a video would be displayed in it's own window)
		# this is platform specific!
		# you have to give the id of the QFrame (or similar object) to
		# vlc, different platforms have different functions for this
		if sys.platform.startswith('linux'): # for Linux using the X Server
			self.mediaplayer.set_xwindow(self.videoframe.winId())
		elif sys.platform == "win32": # for Windows
			self.mediaplayer.set_hwnd(self.videoframe.winId())
		elif sys.platform == "darwin": # for MacOS
			self.mediaplayer.set_nsobject(self.videoframe.winId())

		# file source
		self.buffer_queue = Queue()

	def createUI(self):
		"""Set up the user interface, signals & slots
		"""
		self.widget = QtGui.QWidget(self)
		self.setCentralWidget(self.widget)

		# In this widget, the video will be drawn
		if sys.platform == "darwin": # for MacOS
			self.videoframe = QtGui.QMacCocoaViewContainer(0)
		else:
			self.videoframe = QtGui.QFrame()

		self.palette = self.videoframe.palette()
		self.palette.setColor (QtGui.QPalette.Window,
			QtGui.QColor(0,0,0))
		self.videoframe.setPalette(self.palette)
		self.videoframe.setAutoFillBackground(True)

		self.vboxlayout = QtGui.QVBoxLayout()
		self.vboxlayout.addWidget(self.videoframe)

		self.widget.setLayout(self.vboxlayout)

		self.timer = QtCore.QTimer(self)
		self.timer.setInterval(200)
		self.connect(self.timer, QtCore.SIGNAL("timeout()"),
			self.updateUI)

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
			if self.mediaplayer.play() == -1:
				self.isplaying = 0 # play failed
				'DEBUG', 'one play failed'
			else:
				self.isplaying = 1
				print 'DEBUG', 'one start'
		except Exception,e:
			print 'DEBUG', 'one get failed',e

	'Open API'
	def open_api_run(self):
		print 'INFO', 'player run'
		self.open_running = 1
		self.origin = set()
		self.cnt = 0
		self.timer.start()
		Thread(target=self.open_api_scan).start()
		# start app
		self.show()
		self.resize(954, 512)
		self.app.exec_()

	def open_api_exit(self):
		self.open_running = 0
		self.mediaplayer.stop()	
		self.timer.stop()
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

	'Override'
	def closeEvent(self, event):
		self.open_api_exit()
		event.accept()


# UNIT TEST
if __name__ == '__main__':
	player = QtvlcPlayer()
	player.open_api_run()




