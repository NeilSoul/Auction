#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# UDP Message Protocols
UDP_HOST = ''
UDP_BROADCAST = '<broadcast>'#'192.168.1.255'
UDP_AUCTION_PORT = 9000
UDP_BID_PORT = 9001

# TCP Transport Protocols
TRP_HOST = '0.0.0.0'
TRP_PORT = 9002

# Logger
LOG_HOST = ''
LOG_BROADCAST = '<broadcast>'#'192.168.1.255'
LOG_PORT = 9008
LOG_DIR = 'log'

# Player Buffer
#PLAYER_DEFAULT_URL = "http://devstreaming.apple.com/videos/wwdc/2015/413eflf3lrh1tyo/413/hls_vod_mvp.m3u8"
PLAYER_DEFAULT_URL ="http://devimages.apple.com/iphone/samples/bipbop/bipbopall.m3u8"
PLAYER_BUFFER = "video_buffer"
PLAYER_COMMAND = "mplayer"

# Auction Parameters
AUCTIONEER_SEG_NUM = 1 # segment number per auction
AUCTIONEER_DEFAULT_CAPACITY = 1 # default capacity