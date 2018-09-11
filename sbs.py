import psutil, time, argparse, os, signal, sys, re, random
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
        
    def update(self, newValue):
        global LAST_UPDATE_MEASUREMENTS
        # even though some of this data may be meaningless for some measurements,
        # we will keep it anyway.
        self.delta = newValue - self.lastValue
        self.lastValue = newValue
        self.cumulative = self.cumulative + self.delta
        
        self._values.append(newValue)
     
    def getValueByIndex(self, index):
        return self._values[index]
                
class SbsProcess(psutil.Process):
    # private
    _process = None
    _cmd = None
    _launchTime = None
    _stdout = None
    _numberOfMeasurementUpdates = 0
    _last_isRunning = None
    _processIsRunning = False
    _processID = None
    _sbsProcessID = None
    # public
    name = None

    def __init__(self, pid, outputMeasurementsToFile=True, isSbsProcessTheParent=False, isCmdBash=False, *args, **kwargs):
        super(SbsProcess, self).__init__(*args, **kwargs)
        try:
            self._process = psutil.Process(pid)
            self._cmd = ' '.join(self._process.cmdline())
            self._launchTime = self._process.create_time()
            self._processID = self._process.pid
        except psutil.NoSuchProcess as e:
            # the process ended already and we could not get an accurate start time
            # so we will just use the next best thing
            self._launchTime = time.time()
            self._processIsRunning = False
        self._sbsProcessID = int(time.time() / 1000) * random.randint(0, 1000)
        self.name = getProcessName(self._process)
        self.measurements = []
        self.isSbsProcessTheParent = isSbsProcessTheParent
        self.isCmdBash = isCmdBash
        self._processIsRunning = True
        
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

        # Setup SbsMeasurement objects for each set of data we're collecting
        # ie: for all those defined in mName. This is where it gets messy
        # because it is hard coded.
        i = 0
        while i < len(mName):
            if outputMeasurementsToFile:
                fileName = '%s_%s_%s' % (OUTPUT_FIL, self.getPid(), mName[i])
            self.measurements.append(SbsMeasurement(mName[i], mType[i], fileName))
            i = i + 1
            
        print 'Process launched [PID: %s, IsRunning: %s, Start: %s]: %s\n' % (self.getPid(), self._processIsRunning, self._launchTime, self._cmd)

    def updateMeasurements(self):
        global LAST_UPDATE_MEASUREMENTS
        if self.isRunning():
            # Catch any PSUtil exceptions
            try:
                with self._process.oneshot():
                    mem = self._process.memory_info()
                    io = self._process.io_counters()
                    
                    childProcessCount = len(self._process.children())
                    threadCount = self._process.num_threads()
                    
                    # in the case that the command SBS has launched is simply
                    # a bash script then we don't want the process & thread count
                    # to be artificially high by one, so reduce it as necessary.
                    if self.isSbsProcessTheParent and self.isCmdBash:
                        childProcessCount = childProcessCount - 1
                        threadCount = threadCount - 1
                    
                    # hard coded: fix this one day please.
                    self.measurements[0].update(LAST_UPDATE_MEASUREMENTS)
                    self.measurements[1].update(threadCount)
                    self.measurements[2].update(self._process.cpu_percent())
                    self.measurements[3].update(mem.rss)
                    self.measurements[4].update(mem.vms)
                    self.measurements[5].update(io.read_count)
                    self.measurements[6].update(io.read_bytes)
                    self.measurements[7].update(io.write_count)
                    self.measurements[8].update(io.write_bytes)
                    self.measurements[9].update(childProcessCount)
                    
                    self._numberOfMeasurementUpdates = self._numberOfMeasurementUpdates + 1
                    self._last_isRunning = LAST_UPDATE_MEASUREMENTS
            except psutil.NoSuchProcess:
                # Edge case however if the psutil.NoSuchProcess exception is not
                # caught by SbsProcess.isRunning() then we might have to catch it
                # here too. Some times this occurs because the process has ended
                # in between checking (hmm). 
                self._processIsRunning = False
            except Exception as e: # (should this be an else clause?)
                # Catch a generic exception
                self._processIsRunning = False
                print 'Failed to update measurements for: %s' % self.getPid()
        else:
            self._processIsRunning = False
            
    def getMeasurements(self):
        return self.measurements

    def getCmd(self):
        return self._cmd
    
    def getLaunchTime(self):
        return self._launchTime
    
    def getMeasurementNamesList(self):
        return [m.name for m in self.measurements]
        
    def isRunning(self):
        try:
            self._processIsRunning = (self._process.is_running() and self._process.status() != psutil.STATUS_ZOMBIE)
        except (psutil.NoSuchProcess, AttributeError) as e:
            self._processIsRunning = False
        
        return self._processIsRunning

    def getPid(self):
        if self._processID == None:
            return self._sbsProcessID 
        return self._processID
    
    def getLastIsRunningTime(self):
        if self._last_isRunning == None:
            return self.getLaunchTime()
        return self._last_isRunning
    
    def __del__(self):
        try:
            fileName = '%s_%s' % (OUTPUT_FIL, self.getPid())
            with open(fileName, 'w+') as fcsv:
                fcsv.write('%s\n' % (','.join(self.getMeasurementNamesList())))
                for i in xrange(self._numberOfMeasurementUpdates):
                    tempRow = []
                    for m in self.measurements:
                        tempRow.append(m.getValueByIndex(i))

                    fcsv.write('%s\n' % (','.join(map(str,tempRow))))
                    i = i + 1
                    
        except Exception as e:
            print e
            print 'Failed to write to: %s' % fileName
            return 0
        print 'Wrote to: %s' % (fileName)

class SbsSystemStatus():

    _numberOfMeasurementUpdates = 0
    
    def __init__(self, outputMeasurementsToFile=True, *args, **kwargs):
        self.measurements = []
        
        mName = [
            'time',
            'cpu_percent',
            'mem_used',
            'mem_avai',
            'io_read_count',
            'io_read_bytes',
            'io_write_count',
            'io_write_bytes',
            'process_count',
        ]
        mType = [
            MEASUREMENT_TYPE_NO_CALC,
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
                fileName = '%s_%s_%s' % (OUTPUT_FIL, 'system', mName[i])
            self.measurements.append(SbsMeasurement(mName[i], mType[i], fileName))
            i = i + 1

    def updateMeasurements(self):
        global LAST_UPDATE_MEASUREMENTS
        mem = psutil.virtual_memory()
        io = psutil.disk_io_counters()
        
        self.measurements[0].update(LAST_UPDATE_MEASUREMENTS)
        self.measurements[1].update(psutil.cpu_percent())
        self.measurements[2].update(mem.used)
        self.measurements[3].update(mem.available)
        self.measurements[4].update(io.read_count)
        self.measurements[5].update(io.read_bytes)
        self.measurements[6].update(io.write_count)
        self.measurements[7].update(io.write_bytes)
        self.measurements[8].update(len(psutil.pids()))

        self._numberOfMeasurementUpdates = self._numberOfMeasurementUpdates + 1
        
    def getMeasurements(self):
        return self.measurements

    def getMeasurementNamesList(self):
        return [m.name for m in self.measurements]

    def __del__(self):
        try:
            fileName = '%s_%s' % (OUTPUT_FIL, 'system')
            with open(fileName, 'w+') as fcsv:
                fcsv.write('%s\n' % (','.join(self.getMeasurementNamesList())))
                for i in xrange(self._numberOfMeasurementUpdates):
                    tempRow = []
                    for m in self.measurements:
                        tempRow.append(m.getValueByIndex(i))

                    fcsv.write('%s\n' % (','.join(map(str,tempRow))))
                    i = i + 1
                    
        except Exception as e:
            print e
            print 'Failed to write to: %s' % fileName
        print 'Wrote to: %s' % (fileName)
        
class SbsProcessHandlerClass():
    # there should only be one instance of this class (why doesn't python support static classes)
    def __init__(self, parentPid, cmdIsBash):
        self._parent = SbsProcess(parentPid, isSbsProcessTheParent=True, isCmdBash=cmdIsBash)
        self._children = []
        self._system = SbsSystemStatus()
        self._cmdIsBash = cmdIsBash
        
    def addChild(self, childPid):
        self._children.append(SbsProcess(childPid))
    
    def getChildren(self):
        return self._children
    
    def getParent(self):
        return self._parent
    
    def getSystem(self):
        return self._system
    
    def __del__(self):
        # now that we're ending the handler, write to file how each process was launched
        with open(('%s_child_cmds' % OUTPUT_FIL), 'w+') as fCmdLog, open(('%s_child_cmds_plot' % OUTPUT_FIL), 'w+') as fCmdLogPlot:
            if len(self.getChildren()) > 0:
                print '\nDeleting children SbsProcess...'
                for child in self.getChildren():
                    print child.getPid()                    
                    try:
                        fCmdLog.write('PID %s launched at %s\n\t%s\n' % (child.getPid(), child.getLaunchTime(), child.getCmd()))
                        fCmdLogPlot.write('%s,%s,%s\n' % (child.getPid(), child.getLaunchTime(), child.getLastIsRunningTime()))
                        del child
                    except Exception as e:
                        print e
                        print 'Failed to end a child SbsProcess...'
        print 'Wrote to: %s\nand: %s' % (('%s_child_cmds' % OUTPUT_FIL), ('%s_child_cmds_plot' % OUTPUT_FIL))
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
    # to begin, assume the process has ended. assign it a random number
    processName = int(time.time())
    try:
        processName = '%s%s%s' % (objPsutilProcess.pid, objPsutilProcess.create_time(), '"%s"'%(' '.join(objPsutilProcess.cmdline())))
    except Exception as e:
        pass # as above
    return processName

	
def main(cmd, sleepTime, loggable, cmdIsBash):
    global SbsProcessHandler
    global LAST_UPDATE_MEASUREMENTS
    # check if file exists. It'd be terrible to overwrite experiment data.
    if os.path.exists(OUTPUT_FIL):
        if raw_input('Output file exists. Overwrite? (y/n): ') == 'n':
            print 'Goodbye.'
            quit()   
        print 'SBS will only overwrite the aggregate file and not the associated CSV files.'
        
    parentStdOutFile = open('%s_parent_stdout' % (OUTPUT_FIL), 'w+')
    try:
        # using psutil, start the process. 
        parentProcess = psutil.Popen(cmd.split(' '), stdout=parentStdOutFile)
    except Exception as e:
        # oops, something went wrong.
        print e
        print '\nFailed to launch process. Exiting.'
        quit()
    
    try:
        # now that the parent process has started, lets have the SbsProcessHandler take control.
        # this is globally declared so that we can safely destroy everything when needed.
        SbsProcessHandler = SbsProcessHandlerClass(parentProcess.pid, cmdIsBash)
        print 'SbsProcessHandler Parent ID: %s ' % SbsProcessHandler.getParent().getPid()
    except Exception as e:
        print e
        print '\n Failed to create SbsProcessHandler object. Exiting.'
        quit()
    # There was no issues creating the handler. Destroy the parentProcess variable now so it isn't accidentally used.
    del parentProcess
    
    print 'SBS Process Handler started...\n'
    
    # start monitoring. open output file to write to.
    with open(('%s_aggregate' % OUTPUT_FIL), 'w+') as fData:
        # we want to keep track of all child processes, forever.
        childProcessHistory = []
        
        fData.write('%s\n' % (','.join(SbsProcessHandler.getParent().getMeasurementNamesList())))
        
        # make sure the parent is still running. if so, monitor it and its children.
        while SbsProcessHandler.getParent().isRunning():

            # find all children of parent (grandchildren too, etc)
            for child in SbsProcessHandler.getParent().children(recursive=True):
            
                # we're using psutil methods here, prepare for an exception!
                try:
                    # make sure the child is still running and is not a zombie
                    # we cannot call SbsProcess.isRunning() because this is still a native psutil class,
                    # and not a SbsProcess. We will convert it soon. (instead, use the psutil.Process.is_running() method)
                    if child.is_running() and child.status() != psutil.STATUS_ZOMBIE and child.pid != SbsProcessHandler.getParent().getPid():
                    
                        # check to see if we've seen this child before
                        # note: we're going to miss any children that are launched and end between this check. Notably, we sleep for 1 sec
                        # before analysing again.      
                        seenChildAlready = False
                        for existChild in SbsProcessHandler.getChildren():
                            if existChild.name == getProcessName(child):
                                # we have seen it before, don't worry about it. move onto next child.
                                seenChildAlready = True
                                break
                                
                        # only reach here if we have not seen the child yet. make a record of it
                        if seenChildAlready == False:
                            SbsProcessHandler.addChild(child.pid)
                except psutil.NoSuchProcess as e:
                    pass # the child ended, move to the next one
                    
            # Now we need to achieve the following:
            #   - update the measurements for the parent process and all children
            #   - using the parents data as a basis, start aggregating with child measurements
            # To achieve this, we will use the handy SbsOutputRow class, which does the
            # work for us. See class implementation above.
            
            LAST_UPDATE_MEASUREMENTS = time.time()
            
            SbsProcessHandler.getParent().updateMeasurements()
            SbsProcessHandler.getSystem().updateMeasurements()
            
            outputMeasurements = SbsOutputRow(SbsProcessHandler.getParent())

            for child in SbsProcessHandler.getChildren():
                child.updateMeasurements()
                outputMeasurements.addChildData(child)
                    
            print outputMeasurements.toCsv()

            fData.write('%s\n' % outputMeasurements.toCsv())
            
            # flush the write buffer if the user desires
            if loggable == 'y':
                fData.flush()

            # sleep for some time before going again.
            time.sleep(sleepTime)
		
        # seems like the parent process has ended.
        print 'Parent process ended (or became a zombie). Exiting.'
        
        print 'Writing parent STDOUT to file...'
        parentStdOutFile.flush()
        parentStdOutFile.close()
        
        print '\n\nStarting cleanup...'
        
        
if __name__ == "__main__":
    global SbsProcessHandler
    parser = argparse.ArgumentParser(description = 'Software Benchmarking Script3')
    parser.add_argument('-c', help='Command to run', default=None, required=True)
    parser.add_argument('-o', help='Output file location and name', default=None, required=True)
    parser.add_argument('-s', help='Time to sleep (sec) (default=1)', type=float, default=1)
    parser.add_argument('-l', help='Flush output buffer on each poll (allows output to be tail\'able) (y/n) (default=n)', type=str, default='n')
    parser.add_argument('--cmdIsBash', help='The command passed into -c is a shell script. This will cause the thread and process count to be 1 above actual.', const=True, default=False, nargs='?')
    args = parser.parse_args()

    OUTPUT_FIL = args.o
    
    fstd = open(('%s_stdout_log' % args.o), 'w+')
    original = sys.stdout
    sys.stdout = Tee(sys.stdout, fstd)
    
    try:
        print '\nSBS initialising at %s (PID = %s)\nwith args:\n%s\n' % (time.time(), os.getpid(), args)
        SbsProcessHandler = None # just initialise this for now
        main(args.c, args.s, args.l, args.cmdIsBash)
    except KeyboardInterrupt:
        # tidy up
        print '\n\nInterrupted. Tidying up...'
        print 'Output file(s) close on exit.\n'

        del SbsProcessHandler
        
        print '\nGoodbye.\n'
        
    sys.stdout = original
    fstd.close()