#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# UDP Message Protocols
UDP_HOST = ''
UDP_BROADCAST = '192.168.1.255'#'<broadcast>'#
UDP_AUCTION_PORT = 9000
UDP_BID_PORT = 9001

# TCP Transport Protocols
TRP_HOST = '0.0.0.0'
TRP_PORT = 9002

# Logger
LOG_HOST = ''
LOG_PORT = 9008
LOG_DIR = 'log'

# Script
SCRIPT_HOST = ''
SCRIPT_PORT = 8990


# Player Buffer
#PLAYER_DEFAULT_URL = "http://devstreaming.apple.com/videos/wwdc/2015/413eflf3lrh1tyo/413/hls_vod_mvp.m3u8"
#PLAYER_DEFAULT_URL ="http://devimages.apple.com/iphone/samples/bipbop/bipbopall.m3u8"
#PLAYER_DEFAULT_URL ="http://115.28.222.35/fruit.m3u8"
#PLAYER_DEFAULT_URL = "http://115.28.222.35/fruit360P/fruit360P.m3u8"
#PLAYER_DEFAULT_URL = "http://166.111.138.117/blackEmpire/blackEmpire.m3u8"
PLAYER_DEFAULT_URL = "http://166.111.138.34/ElephantsDream/variant.m3u8"
PLAYER_BUFFER = "video_buffer"
PLAYER_COMMAND = "mplayer"

# N(Auctioneer) Parameters
AUCTIONEER_SEG_NUM = 1 # segment number per auction
AUCTIONEER_DEFAULT_CAPACITY = 0.1 # default capacity
AUCTIONEER_COST_TI = 0.15 # cost rebuffer coefficients
AUCTIONEER_COST_DA = 0.15 # cost on cellular link
AUCTIONEER_COST_WDA = 0.0#0.03 # cost on WiFi link
AUCTIONEER_DOWNLOAD_TIMEOUT = 60 # timeout check of downloading task （1 minute）
# M(Bidder) paramters
BIDDER_BASIC_TH = 0.1 # basic preference
BIDDER_MAX_BUF = 40 # maximum buffer size
BIDDER_K_QV = 0.2
BIDDER_K_BUF = 0.01
BIDDER_K_THETA = 10
BIDDER_K_BR = 1.5
