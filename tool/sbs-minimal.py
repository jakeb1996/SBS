import psutil, time, argparse, os, signal, sys
from subprocess import PIPE


def main():

	print '\nLaunching process...'
	try:
		p = psutil.Popen(["python", "C:\git\SBS\\tool\cas-designer.py", "config"]) #["python", "C:\git\SBS\tool\cas-designer.py", "config"])
		print 'Start time: %s ' % time.time()
	except Exception as e:
		print e
		print '\nFailed to launch process. Exiting.'
		quit()

	print '\nProcess launched: %s' % (p)
	
	# Monitor process
	while p.is_running():
		time.sleep(1)
	
	print 'End time: %s' % time.time()
	print 'Process exited. Exiting.'
        
if __name__ == "__main__":
    main()