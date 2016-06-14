#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# UDP Broadcast Address
UDP_BROADCAST = '<broadcast>'
#UDP_BROADCAST = '192.168.1.255'#specified network interface

# Discovery Protocols
DIS_HOST = '0.0.0.0'
DIS_AUC_PORT = 9010
DIS_BID_PORT = 9011

# Message Protocols
MSG_HOST = '0.0.0.0'
MSG_AUC_PORT = 9020
MSG_BID_PORT = 9021

# Transport Protocols
TRP_HOST = '0.0.0.0'
TRP_PORT = 9030


# Controller Protocols
CTR_HOST = ''
CTR_MASTER_BCAST_PORT = 9040
CTR_MASTER_PORT = 9041
CTR_SLAVE_PORT = 9042

# Logger Folder
LOG_DIR = 'log'

# Buffer Folder
BUFFER_DIR = 'buffer'


# About Player
#PLAYER_DEFAULT_URL = "http://devstreaming.apple.com/videos/wwdc/2015/413eflf3lrh1tyo/413/hls_vod_mvp.m3u8"
#PLAYER_DEFAULT_URL ="http://devimages.apple.com/iphone/samples/bipbop/bipbopall.m3u8"
#PLAYER_DEFAULT_URL ="http://115.28.222.35/fruit.m3u8"
#PLAYER_DEFAULT_URL = "http://115.28.222.35/fruit360P/fruit360P.m3u8"
#PLAYER_DEFAULT_URL = "http://166.111.138.117/blackEmpire/blackEmpire.m3u8"
#PLAYER_DEFAULT_URL = "http://166.111.138.34/ElephantsDream/variant.m3u8"
#PLAYER_DEFAULT_URL = "http://localhost/320/360.m3u8"
PLAYER_DEFAULT_URL = "http://192.168.1.100/ElephantsDream/variant.m3u8"
PLAYER_BUFFER = "video_buffer"
PLAYER_COMMAND = "mplayer"

# N(Auctioneer) Parameters
AUCTIONEER_SEG_NUM = 1 # segment number per auction
AUCTIONEER_DEFAULT_CAPACITY = 0.1 # default capacity
AUCTIONEER_COST_TI = 0.1 # cost rebuffer coefficients
AUCTIONEER_COST_DA = 0.2 # cost on cellular link
AUCTIONEER_COST_WDA = 0.03#0.03 # cost on WiFi link
AUCTIONEER_DOWNLOAD_TIMEOUT = 60 # timeout check of downloading task （1 minute）

# M(Bidder) parameters
BIDDER_BASIC_TH = 0.0 # basic preference
BIDDER_MAX_BUF = 50 # maximum buffer size
BIDDER_K_QV = 2.5
BIDDER_K_BUF = 0.005
BIDDER_K_THETA = 1
BIDDER_K_BR = 1.5
BIDDER_A_LINK = 0.5
BIDDER_A_BUF = 2
BIDDER_NUMBER = 1
BIDDER_PREVIOUS_RATE = 0.494

# Package
def default_auctioneer_params(peername):
	auctioneer_params = {}
	auctioneer_params['peer'] = peername
	auctioneer_params['segment'] = AUCTIONEER_SEG_NUM
	auctioneer_params['capacity'] = AUCTIONEER_DEFAULT_CAPACITY
	auctioneer_params['timecost'] = AUCTIONEER_COST_TI
	auctioneer_params['cellular'] = AUCTIONEER_COST_DA
	auctioneer_params['wifi'] = AUCTIONEER_COST_WDA
	auctioneer_params['delay'] = 100
	auctioneer_params['broadcast'] = UDP_BROADCAST
	return auctioneer_params 

def default_bidder_params(peername):
	bidder_params = {}
	bidder_params['peer'] = peername
	bidder_params['url'] = PLAYER_DEFAULT_URL
	bidder_params['silent'] = False
	bidder_params['theta'] = BIDDER_BASIC_TH
	bidder_params['kqv'] = BIDDER_K_QV
	bidder_params['kbuf'] = BIDDER_K_BUF
	bidder_params['ktheta'] = BIDDER_K_THETA
	bidder_params['kbr'] = BIDDER_K_BR
	bidder_params['mbuf'] = BIDDER_MAX_BUF
	bidder_params['kcapacity'] = 1.0
	bidder_params['broadcast'] = UDP_BROADCAST
	bidder_params['alink'] = BIDDER_A_LINK
	bidder_params['abuf'] = BIDDER_A_BUF
	bidder_params['bnumber'] = BIDDER_NUMBER
	bidder_params['prate'] = BIDDER_PREVIOUS_RATE
	return bidder_params
