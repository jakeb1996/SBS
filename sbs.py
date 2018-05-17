import psutil, time, argparse, os, signal, sys
from subprocess import PIPE


MEASUREMENT_TYPE_INSTANT = 1
MEASUREMENT_TYPE_CUMULATIVE = 2

class SbsMeasurement():
    def __init__(self, inName, inType):
        self.name = inName
        self.lastValue = 0
        self.delta = 0
        self.cumulative = 0
        self.type = inType # MEASUREMENT_TYPE_CUMULATIVE, MEASUREMENT_TYPE_INSTANT
        
    def update(self, newValue):
        # even though some of this data may be meaningless for some measurements,
        # we will keep it anyway.
        self.delta = newValue - self.lastValue
        self.lastValue = newValue
        self.cumulative = self.cumulative + self.delta

        
class SbsProcess(psutil.Process):
    # private
    _process = None
    
    # public
    name = None

    def __init__(self, pid, *args, **kwargs):
        super(SbsProcess, self).__init__(*args, **kwargs)
        self._process = psutil.Process(pid)
        
        self.measurements = [
            SbsMeasurement('num_threads', MEASUREMENT_TYPE_INSTANT),
            SbsMeasurement('cpu_percent', MEASUREMENT_TYPE_INSTANT),
            SbsMeasurement('mem_rss', MEASUREMENT_TYPE_INSTANT),
            SbsMeasurement('mem_vms', MEASUREMENT_TYPE_INSTANT),
            SbsMeasurement('io_read_count', MEASUREMENT_TYPE_CUMULATIVE),
            SbsMeasurement('io_read_bytes', MEASUREMENT_TYPE_CUMULATIVE),
            SbsMeasurement('io_write_count', MEASUREMENT_TYPE_CUMULATIVE),
            SbsMeasurement('io_write_bytes', MEASUREMENT_TYPE_CUMULATIVE),
            SbsMeasurement('child_process_count', MEASUREMENT_TYPE_INSTANT)
        ]
        
        self.name = getProcessName(self._process)
   
    def updateMeasurements(self):
        if self._process.is_running() and self._process.status() != psutil.STATUS_ZOMBIE:
            with self._process.oneshot():
                mem = self._process.memory_info()
                io = self._process.io_counters()
                
                self.measurements[0].update(self._process.num_threads())
                self.measurements[1].update(self._process.cpu_percent())
                self.measurements[2].update(mem.rss)
                self.measurements[3].update(mem.vms)
                self.measurements[4].update(io.read_count)
                self.measurements[5].update(io.read_bytes)
                self.measurements[6].update(io.write_count)
                self.measurements[7].update(io.write_bytes)
                self.measurements[8].update(len(self._process.children()))

    def getMeasurements(self):
        return self.measurements

    def getMeasurementNamesList(self):
        return [m.name for m in self.measurements]
        
        
class SbsOutputRow():
    def __init__(self, parentMeasurements):
        # the output row should be initialised with some data.
        # this data is typically the data from the parent process.
        self._values = []
        for measurement in parentMeasurements:
            self._values.append(measurement.lastValue)

    def addChildData(self, childMeasurements):
        # now we need to start add on values (whether that be the total used (in the case of IO counts) or lastValue (in the case of cpu usage))
        i = 0
        for measurement in childMeasurements:
            if measurement.type == MEASUREMENT_TYPE_INSTANT:
                self._values[i] = self._values[i] + measurement.lastValue
            
            if measurement.type == MEASUREMENT_TYPE_CUMULATIVE:
                self._values[i] = self._values[i] + measurement.cumulative
            i = i + 1
            
    def toCsv(self):
        # we also want the time of this
        return '%s,%s\n' % (time.time(), ','.join(map(str, self._values)))
    
    def getValues(self):
        return self._values
  
  
def getProcessName(objPsutilProcess):
    return '%s%s%s' % (objPsutilProcess.pid, objPsutilProcess.create_time(), '"%s"'%(' '.join(objPsutilProcess.cmdline())))

	
def main(cmd, outFile, sleepTime, loggable):
    # check if file exists. It'd be terrible to overwrite experiment data.
    if os.path.exists(outFile):
        if raw_input('Output file exists. Overwrite? (y/n): ') == 'n':
            print 'Goodbye.'
            quit()   

    try:
        # using psutil, start the process. then hand it to an SbsProcess object.
        parentProcess = psutil.Popen(cmd.split(' '))
        parentProcess = SbsProcess(parentProcess.pid)
    except Exception as e:
        # oops, something went wrong.
        print e
        print '\nFailed to launch process. Exiting.'
        quit()
    
    print 'Parent process launched.\n'
    
    # start monitoring. open output file to write to.
    with open(outFile, 'w+') as fData:
        # we want to keep track of all child processes, forever.
        childProcessHistory = []
        
        firstFileWrite = True
        
        # make sure the parent is still running. if so, monitor it and its children.
        while parentProcess.is_running() and parentProcess.status() != psutil.STATUS_ZOMBIE:

            # find all children of parent (grandchildren too, etc)
            for child in parentProcess.children(recursive=True):
            
                # make sure the child is still running and is not a zombie (for ubuntus sake)
                if child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
                
                    # check to see if we've seen this child before
                    seenChildAlready = False
                    
                    for existChild in childProcessHistory:
                        if existChild.name == getProcessName(child):
                            # we have, don't worry about it. move onto next child.
                            seenChildAlready = True
                            break
                            
                    # only reach here if we have not seen the child yet. make a record of it
                    if seenChildAlready == False:
                        childProcessHistory.append(SbsProcess(child.pid))
            
            # Now we need to achieve the following:
            #   - update the measurements for the parent process and all children
            #   - using the parents data as a basis, start aggregating the measurements
            # To achieve this, we will use the handy SbsOutputRow class, which does the
            # work for us. See class implementation above.
            outputMeasurements = None
            for child in childProcessHistory:
                if outputMeasurements == None:
                    # for some reason, the first child is the parent process. start there.
                    parentProcess.updateMeasurements()
                    outputMeasurements = SbsOutputRow(parentProcess.getMeasurements())
                else:
                    # now we've reached the children and grandchildren, keep going.
                    child.updateMeasurements()
                    outputMeasurements.addChildData(child.getMeasurements())
                    
            
            print '\n'
            print outputMeasurements.toCsv()
            # monitoring of parent and children complete for this iteration. write data to file.
            if firstFileWrite == True:
                # write CSV headers
                fData.write('time,%s\n' % (','.join(parentProcess.getMeasurementNamesList())))
                firstFileWrite = False
                
            fData.write(outputMeasurements.toCsv())
            
            # flush the write buffer if the user desires
            if loggable == 'y':
                fData.flush()

            # sleep for some time before going again.
            time.sleep(sleepTime)
		
        # seems like the parent process has ended.
        print 'Parent process ended (or became a zombie). Exiting.'
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Software Benchmarking Script3')
    parser.add_argument('-c', help='Command to run', default=None)
    parser.add_argument('-o', help='Output file name', default=None)
    parser.add_argument('-s', help='Time to sleep (sec) (default=1)', type=int, default=1)
    parser.add_argument('-l', help='Flush output buffer on each poll (allows output to be tail\'able) (y/n) (default=n)', type=str, default='n')
    args = parser.parse_args()

    try:
        print 'SBS initialisating at %s with args: %s' % (time.time(), args)
        main(args.c, args.o, args.s, args.l)
    except KeyboardInterrupt:
        # tidy up
        print '\n\nInterrupted. Tidying up...'
        print 'Output file closes on exit.\n'
        parent = psutil.Process(os.getpid()) # os.getpid() gets this scripts process ID
        children = parent.children(recursive=True)
        for p in children:
            print 'Killing child process: %s' % p
            p.send_signal(signal.SIGTERM)

        print 'All child processes terminated at (if any): %s' % time.time()
        print '\nKilling self: %s' % parent
        parent.send_signal(signal.SIGTERM)

        print '\nGoodbye.\n'
