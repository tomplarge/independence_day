import os
import time
def forktest():
	pid = os.fork()
	if pid == 0:
		os.system('say Hey how are you doing? I hope that things are printing to the screen. That would mean this example is working.')
		exit()	
	else:
		return [1,2,3,4,5,6,7]

if __name__ == "__main__":
	x = forktest()
	for i in x:
		time.sleep(0.2)
		print i
