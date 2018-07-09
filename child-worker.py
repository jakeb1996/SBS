import psutil, time, argparse, os, signal, sys
from subprocess import PIPE

def main(n, g):
	parents = []
	for i in range(1, n + 1):
		try:
			newArgs = map(str, ['python', os.path.realpath(__file__), '-n', (n - 1), '-g', (g + 1)])
			pTemp = psutil.Popen(newArgs, stdout=PIPE)
		except Exception as e:
			print '\nFailed to launch process (g = %s, n = %s of %s)\n%s\n' % (g, i, n, e)
			break

		print '%s launched child %s' % (os.getpid(), pTemp.pid)
		parents.append(pTemp)
			
	print 'Launched child processes (g = %s, n = %s of %s)\n' % (g, len(parents), n)
	
	test = None
	while True:
		test = None
	

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description = 'Software Benchmarking Script')
	parser.add_argument('-n', help='Number of children to spawn')
	parser.add_argument('-g', help='Generation number (start at zero)', default=0)
	args = parser.parse_args()
	try:
		print 'Initialising at %s with args: %s' % (time.time(), args)
		main(int(args.n), int(args.g))
	except KeyboardInterrupt:
	
		print '\n\nInterrupted. Tidying up...'
		parent = psutil.Process(os.getpid())
		children = parent.children(recursive=True)
		for p in children:
			print 'Killing child process: %s' % p
			p.send_signal(signal.SIGTERM)

		print 'All child processes ended at: %s' % time.time()
		print '\nKilling self: %s' % parent
		parent.send_signal(signal.SIGTERM)
		print 'Goodbye.'
		exit()
