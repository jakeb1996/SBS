import psutil, time, argparse, os, signal, sys
from subprocess import PIPE

# https://stackoverflow.com/a/11325249
class Tee(object):
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush() # If you want the output to be visible immediately
    def flush(self) :
        for f in self.files:
            f.flush()

def main(cmd, outFile, sleepTime, loggable):

    # check if file exists
    if os.path.exists(outFile):
        if raw_input('Output file exists. Overwrite? (y/n): ') == 'n':
            print 'Goodbye.'
            quit()        

    with open(outFile, 'w+') as f:
        # write CSV headers
        f.write('time,num_threads,cpu_percent,mem_rss,mem_vms,io_read_count,io_read_bytes,io_write_count,io_write_bytes,child_process_count\n')
        
        # Launch process
        print '\nLaunching process...'
        try:
            p = psutil.Popen(cmd.split(' ')) #["python", "C:\git\SBS\hold.py"])
        except Exception as e:
            print e
            print '\nFailed to launch process. Exiting.'
            quit()

        print '\nProcess launched: %s' % (p)
        
        # Monitor process.
        progressIndicator = 0
        while p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
			measurements = []
			with p.oneshot():
				mem = p.memory_full_info()
				io = p.io_counters()

				measurements = [time.time(), # current time
					p.num_threads(), # number of threads for p
					p.cpu_percent(interval=0), # >100% indicates multi-core
					mem.rss, # Resident Set Size (physical mem)
					mem.vms, # Virtual Memory Size (phy+vir mem),
					io.read_count,
					io.read_bytes,
					io.write_count,
					io.write_bytes,
					len(p.children())
				]
				
				for child in p.children(recursive=True):
					child = psutil.Process(child.pid)
					if child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
						with child.oneshot():
							# We will rought it with some hard code
							print child.name
							temp = measurements[2]
							mem = child.memory_full_info()
							io = child.io_counters()
							print 'sys cpu: %s\n' % psutil.cpu_percent()
							print 'child cpu: %s\n' % child.cpu_percent(interval=0)
							measurements[1] = measurements[1] + child.num_threads()
							measurements[2] = measurements[2] + child.cpu_percent(interval=0)
							measurements[3] = measurements[3] + mem.rss
							measurements[4] = measurements[4] + mem.vms
							measurements[5] = measurements[5] + io.read_count
							measurements[6] = measurements[6] + io.read_bytes
							measurements[7] = measurements[7] + io.write_count
							measurements[8] = measurements[8] + io.write_bytes
							measurements[9] = measurements[9] + len(child.children())
							print 'CPU before: %s\nCPU after: %s' % (temp, measurements[2])
				
				f.write('%s\n' % (','.join(map(str, measurements))))
				
				# f.write('%s\n' % () % (
					# time.time(), # current time
					# p.num_threads(), # number of threads for p
					# p.cpu_percent(interval=0), # >100% indicates multi-core
					# mem.rss, # Resident Set Size (physical mem)
					# mem.vms, # Virtual Memory Size (phy+vir mem),
					# io.read_count,
					# io.read_bytes,
					# io.write_count,
					# io.write_bytes,
					# len(p.children()) # child processes
				# ))

			if loggable == 'y':
				f.flush()

			# sleep for desired time
			print '.' * ((progressIndicator) % 11)
			progressIndicator += 1
			time.sleep(sleepTime)

        print 'Process exited. Exiting.'
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Software Benchmarking Script')
    parser.add_argument('-c', help='Command to run')
    parser.add_argument('-o', help='Output file name')
    parser.add_argument('-s', help='Time to sleep (sec) (default=1)', type=int, default=1)
    parser.add_argument('-l', help='Flush output buffer on each poll (allows output to be tail\'able) (y/n) (default=n)', type=str, default='n')
    args = parser.parse_args()

    fstd = open(('%s.log' % args.o), 'w')
    original = sys.stdout
    sys.stdout = Tee(sys.stdout, fstd)

    try:
        print 'Initialising at %s with args: %s' % (time.time(), args)
        main(args.c, args.o, args.s, args.l)
    except KeyboardInterrupt:
        # tidy up
        print '\n\nInterrupted. Tidying up...'
        print 'Output file closes on exit.\n'
        parent = psutil.Process(os.getpid())
        children = parent.children(recursive=True)
        for p in children:
            print 'Killing child process: %s' % p
            p.send_signal(signal.SIGTERM)

        print 'All child processes ended at: %s' % time.time()
        print '\nKilling self: %s' % parent
        parent.send_signal(signal.SIGTERM)

        print '\nGoodbye.\n'
        
    sys.stdout = original
    fstd.close()