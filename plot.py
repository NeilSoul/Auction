#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import matplotlib.pyplot as plt


'Open API'
def create_rate_plot(materials, filename):
	# get data
	x = []
	y = []
	r = 0.0
	t = 0.0
	for item in materials:
		rate, duration, delay = item
		# 1.
		y.append(r)
		x.append(t)
		# 2.0
		t = t + delay
		y.append(r)
		x.append(t)
		# 3.0
		y.append(rate)
		x.append(t)
		#4.0
		t = t + duration
		y.append(rate)
		x.append(t)
		#5.0
		r = rate
	# plot 
	line, = plt.plot(x, y, '--', linewidth=2)
	dashes = [10, 5, 100, 5]  # 10 points on, 5 off, 100 on, 5 off
	line.set_dashes(dashes)
	plt.title('Plot of rate vs. t')# give plot a title
	plt.xlabel('t axis')# make axis labels
	plt.ylabel('rate axis')
	plt.savefig(filename)