def log_msg(*messages):
	print '---[MSG] ', ', '.join([str(message) for message in messages])

def log_trp(*messages):
	print '---[TRP] ', ', '.join([str(message) for message in messages])

def log_sys(*messages):
	print '---[SYS] ', ', '.join([str(message) for message in messages])