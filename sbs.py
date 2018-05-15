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

def listToCsv(list):
	return ','.join(map(str,list))
			
def main(cmd, outFile, sleepTime, loggable):

    # check if file exists
    if os.path.exists(outFile):
        if raw_input('Output file exists. Overwrite? (y/n): ') == 'n':
            print 'Goodbye.'
            quit()        

    with open(outFile, 'w+') as f, open(('%s_children' % (outFile)), 'w+') as fChild:
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
        cpuInterval = 0.1
        childProcessHistory = [] # all time history
        while p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
			# start time of this iteration
			iterTime = time.time()
			
			# on the current iteration. cleared every iteration.
			childProcessHistoryCurrent = [] 
			
			# measurement data. start fresh every iteration.
			measurements = []
			
			# start monitoring parent process
			try:
				with p.oneshot():
					mem = p.memory_info()
					io = p.io_counters()

					measurements = [iterTime,
						p.num_threads(), # number of threads for p
						0, # >100% indicates multi-core
						mem.rss, # Resident Set Size (physical mem)
						mem.vms, # Virtual Memory Size (phy+vir mem),
						io.read_count,
						io.read_bytes,
						io.write_count,
						io.write_bytes,
						len(p.children())
					]
					
				# measure CPU usage outside of the context manager so that we get an accurate reading	
				measurements[2] = p.cpu_percent(interval=cpuInterval)
				
			except Exception as e:
				print e
			
			# start monitoring children too
			
			# keep a record of the number of active children so that we can subtract an 
			# appropriate amount of time from the sleep duration at the end of this iteration
			activeChildCount = 0 
			try:
				for child in p.children(recursive=True):
					if child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
						activeChildCount = activeChildCount + 1
						
						# record any new child processes that have not been seen yet
						childVector = [child.pid, child.create_time(), '"%s"'%(' '.join(child.cmdline()))]
						if childVector not in childProcessHistory:
							childProcessHistory.append(childVector)
							
						# keep a record of every child process that has been seen in this iteration	
						childProcessHistoryCurrent.append(childVector)
						
						# get the system utilisation by the child
						child = psutil.Process(child.pid)
						with child.oneshot():
							# We will rought it with some hard code
							mem = child.memory_info()
							io = child.io_counters()

							measurements[1] = measurements[1] + child.num_threads()
							
							measurements[3] = measurements[3] + mem.rss
							measurements[4] = measurements[4] + mem.vms
							measurements[5] = measurements[5] + io.read_count
							measurements[6] = measurements[6] + io.read_bytes
							measurements[7] = measurements[7] + io.write_count
							measurements[8] = measurements[8] + io.write_bytes
							measurements[9] = measurements[9] + len(child.children())
							
						# measure CPU usage outside of the context manager so that we get an accurate reading
						foo = child.cpu_percent(interval=cpuInterval)
						measurements[2] = measurements[2] + foo
				
				# check for any child processes we've seen so far, that did not appear in this iteration
				# (ie: processes that must have ended). we need the end time for that process.
				# this is only an estimate as the process may have ended after the start of the 
				# last iteration, but before now. see example timeline below.
				# lastIter ------ endTime ------------------- now (now is recorded as the end time)
				for i in childProcessHistory:
					if i not in childProcessHistoryCurrent:
						i.append(iterTime)
				
			except Exception as e:
				print e
			
			# monitoring of parent and children complete. write data to file.
			f.write('%s\n' % (','.join(map(str, measurements))))

			# flush the write buffer if the user desires
			if loggable == 'y':
				f.flush()

			# show an indicator that the script is alive and sleep for desired time
			print '.' * ((progressIndicator) % 11)
			progressIndicator += 1
			time.sleep(sleepTime - activeChildCount * cpuInterval)

        # write child process history to file
        fChild.write('\n'.join(map(listToCsv, childProcessHistory)))
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