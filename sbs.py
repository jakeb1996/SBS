import psutil, time, argparse, os, signal, sys, re
from subprocess import PIPE

MEASUREMENT_TYPE_INSTANT = 1
MEASUREMENT_TYPE_CUMULATIVE = 2
MEASUREMENT_TYPE_NO_CALC = 3
LAST_UPDATE_MEASUREMENTS = None

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
            
class SbsMeasurement():
    def __init__(self, inName, inType, outFileName=None):
        self.name = inName
        self.lastValue = 0
        self.delta = 0
        self.cumulative = 0
        self.type = inType # MEASUREMENT_TYPE_CUMULATIVE, MEASUREMENT_TYPE_INSTANT
        
        self._outFileName = outFileName
        self._values = []
        self._times = []
        
    def update(self, newValue):
        global LAST_UPDATE_MEASUREMENTS
        # even though some of this data may be meaningless for some measurements,
        # we will keep it anyway.
        self.delta = newValue - self.lastValue
        self.lastValue = newValue
        self.cumulative = self.cumulative + self.delta
        
        self._values.append(newValue)
        self._times.append(LAST_UPDATE_MEASUREMENTS)
        
    def __del__(self):
        if self._outFileName != None:
            try:
                with open(self._outFileName, 'w+') as fcsv:
                    i = 0
                    while i < len(self._values):
                        fcsv.write('%s,%s\n' % (self._times[i], self._values[i]))
                        i = i + 1
            except Exception as e:
                print e
                print 'Failed to write to: %s' % self._outFileName
            print 'Wrote to: %s' % (self._outFileName)
                
class SbsProcess(psutil.Process):
    # private
    _process = None
    _cmd = None
    _launchTime = None
    _stdout = None
    
    # public
    name = None

    def __init__(self, pid, outputMeasurementsToFile=True, *args, **kwargs):
        super(SbsProcess, self).__init__(*args, **kwargs)
        self._process = psutil.Process(pid, stdout=self._stdout)
        self.name = getProcessName(self._process)
        self.measurements = []
        self._cmd = ' '.join(self._process.cmdline())
        self._launchTime = self._process.create_time()
        
        mName = [
            'time',
            'num_threads',
            'cpu_percent',
            'mem_rss',
            'mem_vms',
            'io_read_count',
            'io_read_bytes',
            'io_write_count',
            'io_write_bytes',
            'child_process_count'
        ]
        mType = [
            MEASUREMENT_TYPE_NO_CALC,
            MEASUREMENT_TYPE_INSTANT,
            MEASUREMENT_TYPE_INSTANT,
            MEASUREMENT_TYPE_INSTANT,
            MEASUREMENT_TYPE_INSTANT,
            MEASUREMENT_TYPE_CUMULATIVE,
            MEASUREMENT_TYPE_CUMULATIVE,
            MEASUREMENT_TYPE_CUMULATIVE,
            MEASUREMENT_TYPE_CUMULATIVE,
            MEASUREMENT_TYPE_INSTANT
        ]

        i = 0
        while i < len(mName):
            if outputMeasurementsToFile:
                fileName = '%s_%s_%s' % (OUTPUT_FIL, self._process.pid, mName[i])
            self.measurements.append(SbsMeasurement(mName[i], mType[i], fileName))
            i = i + 1
            
        print 'Process launched [PID: %s, Start: %s]: %s\n' % (pid, self._launchTime, self._cmd)

    def updateMeasurements(self):
        global LAST_UPDATE_MEASUREMENTS
        if self.isRunning():
            with self._process.oneshot():
                mem = self._process.memory_info()
                io = self._process.io_counters()
                
                self.measurements[0].update(LAST_UPDATE_MEASUREMENTS)
                self.measurements[1].update(self._process.num_threads())
                self.measurements[2].update(self._process.cpu_percent())
                self.measurements[3].update(mem.rss)
                self.measurements[4].update(mem.vms)
                self.measurements[5].update(io.read_count)
                self.measurements[6].update(io.read_bytes)
                self.measurements[7].update(io.write_count)
                self.measurements[8].update(io.write_bytes)
                self.measurements[9].update(len(self._process.children()))
                
                print self._process.stdout.readline()
    def getMeasurements(self):
        return self.measurements

    def getCmd(self):
        return self._cmd
    
    def getLaunchTime(self):
        return self._launchTime
    
    def getMeasurementNamesList(self):
        return [m.name for m in self.measurements]
        
    def isRunning(self):
        if self._process.is_running() and self._process.status() != psutil.STATUS_ZOMBIE:
            return True
        return False

    def getPid(self):
        return self._process.pid
        
    def __del__(self):
        for m in self.measurements:
            del m
        print 'SbsProcess deconstructor triggered: %s ' % self.name   
        
class SbsProcessHandlerClass():
    # there should only be one instance of this class (why doesn't python support static classes)
    def __init__(self, parentPid):
        self._parent = SbsProcess(parentPid)
        self._children = []
    
    def addChild(self, childPid):
        self._children.append(SbsProcess(childPid))
    
    def getChildren(self):
        return self._children
    
    def getParent(self):
        return self._parent
    
    def __del__(self):
        with open(('%s_child_cmds' % OUTPUT_FIL), 'w+') as fCmdLog:
            if len(self.getChildren()) > 0:
                print '\nDeleting children SbsProcess...'
                for child in self.getChildren():
                    print child.getPid()
                    try:
                        fCmdLog.write('PID %s launched at %s\n\t%s' % (child.getPid(), child.getLaunchTime(), child.getCmd()))
                        del child
                    except Exception as e:
                        print e
                        print 'Failed to end a child SbsProcess...'
        print 'Wrote to: %s' % ('%s_child_cmds' % OUTPUT_FIL)
        print '\nDeleting parent SbsProcess...'
        try:
            del self._parent
        except Exception as e:
            print e
            print 'Failed to end parent SbsProcess...'
        
class SbsOutputRow():
    def __init__(self, parent):
        # the output row should be initialised with some data.
        # this data is typically the data from the parent process.
        self._values = []
        for measurement in parent.getMeasurements():
            self._values.append(measurement.lastValue)

    def addChildData(self, child):
        # now we need to start add on values (whether that be the total used (in the case of IO counts) or lastValue (in the case of cpu usage))
        i = 0
        for measurement in child.getMeasurements():
            # only add instantaneous measurements if the process is still running
            if measurement.type == MEASUREMENT_TYPE_INSTANT and child.isRunning():
                self._values[i] = self._values[i] + measurement.lastValue
            
            # because the measurement is cumulative, we want to know its usage even after it has ended
            if measurement.type == MEASUREMENT_TYPE_CUMULATIVE:
                self._values[i] = self._values[i] + measurement.cumulative
				
            if measurement.type == MEASUREMENT_TYPE_NO_CALC:
                self._values[i] = self._values[i]
                
            i = i + 1
            
    def toCsv(self):
        # we also want the time of this
        return '%s' % (','.join(map(str, self._values)))
    
    def getValues(self):
        return self._values
  
  
def getProcessName(objPsutilProcess):
    return '%s%s%s' % (objPsutilProcess.pid, objPsutilProcess.create_time(), '"%s"'%(' '.join(objPsutilProcess.cmdline())))

	
def main(cmd, sleepTime, loggable):
    global SbsProcessHandler
    global LAST_UPDATE_MEASUREMENTS
    # check if file exists. It'd be terrible to overwrite experiment data.
    if os.path.exists(OUTPUT_FIL):
        if raw_input('Output file exists. Overwrite? (y/n): ') == 'n':
            print 'Goodbye.'
            quit()   
        print 'SBS will only overwrite the aggregate file and not the associated CSV files.'
        
    try:
        # using psutil, start the process. 
        parentProcess = psutil.Popen(cmd.split(' '))
    except Exception as e:
        # oops, something went wrong.
        print e
        print '\nFailed to launch process. Exiting.'
        quit()
    
    try:
        # now that the parent process has started, lets have the SbsProcessHandler take control.
        # this is globally declared so that we can safely destroy everything when needed.
        SbsProcessHandler = SbsProcessHandlerClass(parentProcess.pid)
        print 'SbsProcessHandler Parent ID: %s ' % SbsProcessHandler.getParent().getPid()
    except Exception as e:
        print e
        print '\n Failed to create SbsProcessHandler object. Exiting.'
        quit()
    # There was no issues creating the handler. Destroy the parentProcess variable now so it isn't accidentally used.
    del parentProcess
    
    print 'SBS Process Handler started...\n'
    
    # start monitoring. open output file to write to.
    with open(OUTPUT_FIL, 'w+') as fData:
        # we want to keep track of all child processes, forever.
        childProcessHistory = []
        
        firstFileWrite = True
        
        # make sure the parent is still running. if so, monitor it and its children.
        while SbsProcessHandler.getParent().isRunning():

            # find all children of parent (grandchildren too, etc)

            for child in SbsProcessHandler.getParent().children(recursive=True):
                # make sure the child is still running and is not a zombie
                # we cannot call SbsProcess.isRunning() because this is a native psutil class still,
                # and not a SbsProcess. We will convert it soon. (instead, use the psutil.Process.is_running() method)
                if child.is_running() and child.status() != psutil.STATUS_ZOMBIE and child.pid != SbsProcessHandler.getParent().getPid():
                
                    # check to see if we've seen this child before
                    seenChildAlready = False
                    
                    for existChild in SbsProcessHandler.getChildren():
                        if existChild.name == getProcessName(child):
                            # we have, don't worry about it. move onto next child.
                            seenChildAlready = True
                            break
                            
                    # only reach here if we have not seen the child yet. make a record of it
                    if seenChildAlready == False:
                        SbsProcessHandler.addChild(child.pid)
            
            # Now we need to achieve the following:
            #   - update the measurements for the parent process and all children
            #   - using the parents data as a basis, start aggregating with child measurements
            # To achieve this, we will use the handy SbsOutputRow class, which does the
            # work for us. See class implementation above.
            
            LAST_UPDATE_MEASUREMENTS = time.time()
            
            SbsProcessHandler.getParent().updateMeasurements()
            outputMeasurements = SbsOutputRow(SbsProcessHandler.getParent())

            for child in SbsProcessHandler.getChildren():
                child.updateMeasurements()
                outputMeasurements.addChildData(child)
                    
            print outputMeasurements.toCsv()
            
            # monitoring of parent and children complete for this iteration. write data to file.
            if firstFileWrite == True:
                # write CSV headers
                fData.write('%s\n' % (','.join(SbsProcessHandler.getParent().getMeasurementNamesList())))
                firstFileWrite = False
                
            fData.write('%s\n' % outputMeasurements.toCsv())
            
            # flush the write buffer if the user desires
            if loggable == 'y':
                fData.flush()

            # sleep for some time before going again.
            time.sleep(sleepTime)
		
        # seems like the parent process has ended.
        print 'Parent process ended (or became a zombie). Exiting.'
        
        print '\n\nStarting cleanup...'
        
        
if __name__ == "__main__":
    global SbsProcessHandler
    parser = argparse.ArgumentParser(description = 'Software Benchmarking Script3')
    parser.add_argument('-c', help='Command to run', default=None, required=True)
    parser.add_argument('-o', help='Output file location and name', default=None, required=True)
    parser.add_argument('-s', help='Time to sleep (sec) (default=1)', type=int, default=1)
    parser.add_argument('-l', help='Flush output buffer on each poll (allows output to be tail\'able) (y/n) (default=n)', type=str, default='n')
    args = parser.parse_args()

    OUTPUT_FIL = args.o
    
    fstd = open(('%s_stdout_log' % args.o), 'w+')
    original = sys.stdout
    sys.stdout = Tee(sys.stdout, fstd)
    
    try:
        print '\nSBS initialising at %s (PID = %s)\nwith args:\n%s\n' % (time.time(), os.getpid(), args)
        SbsProcessHandler = None # just initialise this for now
        main(args.c, args.s, args.l)
    except KeyboardInterrupt:
        # tidy up
        print '\n\nInterrupted. Tidying up...'
        print 'Output file(s) close on exit.\n'

        del SbsProcessHandler
        
        print '\nGoodbye.\n'
        
    sys.stdout = original
    fstd.close()