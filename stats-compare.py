import matplotlib.pyplot as plt
import argparse, csv, numpy, time, os, re

def byteToMegabyte(val):
    return (float(val) / 1024.0 / 1024.0)

def cpuPercentToDecimal(val):
    return (float(val) / 100.0)
    
SBS_STATS_NUMBER_MEASUREMENTS = 10

VALID_TEST_INPUT_SIZES = ['500k', '1m', '5m', 'full']

MEASUREMENTS_IN_RAW_DATA_FILES = ['time',
            'num_threads',
            'cpu_percent',
            'mem_rss',
            'mem_vms',
            'io_read_count',
            'io_read_bytes',
            'io_write_count',
            'io_write_bytes',
            'child_process_count']

PLOTTABLE_MEASUREMENTS = [
            'num_threads',
            'cpu_percent',
            'mem_rss',
            'mem_vms',
            'child_process_count']
            
plots = {
# plot configurations must appear in the order of the associated CSV columns      
# --- sample ---       
#       'plot_name' : {
#               ['x-data' : [],]
#               ['y-data-type' : float,]
#               ['x-label': 'X-axis label',]
#               ['y-data-calc' : funcName,]
#       
#               'y-data' : [],
#               'title' : 'Plot Title',
#               'y-label' : 'Y-axis label'
#       },
# --- end sample ---      
    ### START CHILD PROCESS PLOTS ###
    'num_threads' : {
            'y-data' : [],
            'title' : 'Number of Threads',
            'y-label' : 'Thread Count'
    },
    'cpu_percent' : {
            'y-data' : [],
            'y-data-type' : float,
            'y-data-calc' : cpuPercentToDecimal,
            'title' : 'CPU Utilisation',
            'y-label' : 'CPU Usage'
    },
    'mem_rss' : {
            'y-data' : [],
            'y-data-type' : float,
            'y-data-calc' : byteToMegabyte,
            'title' : 'Resident Set Size (RSS) Memory Utilisation',
            'y-label' : 'Resident Set Size (megabytes)'
    },
    'mem_vms' : {
            'y-data' : [],
            'title' : 'Virtual Memory Size (VMS) Memory Utilisation',
            'y-label' : 'Virtual Memory Size (megabytes)',
            'y-data-calc' : byteToMegabyte,
    },
    'io_read_count' : {
            'y-data' : [],
            'title' : 'Disk IO Read Count',
            'y-label' : 'Number of IO read operations'
    },
    'io_read_bytes' : {
            'y-data' : [],
            'title' : 'Disk IO Read Volume',
            'y-label' : 'Volume of IO read operations (megabytes)',
            'y-data-calc' : byteToMegabyte,
    },
    'io_write_count' : {
            'y-data' : [],
            'title' : 'Disk IO Write Count',
            'y-label' : 'Number of IO write operations'
    },
    'io_write_bytes' : {
            'y-data' : [],
            'title' : 'Disk IO Write Volume',
            'y-label' : 'Number of IO write operations (megabytes)',
            'y-data-calc' : byteToMegabyte,
    },
    'child_process_count' : {
            'y-data' : [],
            'title' : 'Child Process Count',
            'y-label' : 'Number of Child Processes'
    },
    
    ### START SYSTEM PLOTS ###
    # if the plot was defined above, then don't define it again
    'mem_used' : {
            'y-data' : [],
            'y-data-type' : float,
            'y-data-calc' : byteToMegabyte,
            'title' : 'Physical Memory Used',
            'y-label' : 'Memory Used (megabytes)'
    },
    'mem_avai' : {
            'y-data' : [],
            'title' : 'Physical Memory Available',
            'y-label' : 'Memory Available (megabytes)',
            'y-data-calc' : byteToMegabyte,
    },
    'process_count' : {
            'y-data' : [],
            'title' : 'System Process Count',
            'y-label' : 'Number of Processes'
    }        
}
    
class StatsHandlerClass():
    def __init__(self, configFile):
        self.init = True
        
        self.tests = []
        
        if os.path.exists(configFile):
            with open(configFile, 'r') as configFile:
                configFileRaw = configFile.read()
                
                for line in configFileRaw.split('\n'):
                    lineSplit = line.split(',')
                    self.tests.append(Test(lineSplit[0], lineSplit[1], lineSplit[2], lineSplit[3], lineSplit[4], lineSplit[5]))
        else:
            print 'configFile does not exist: %s' % configFile
    
    def drawInterToolPlots(self):
        for testSize in [VALID_TEST_INPUT_SIZES[0]]:
            for measurement in PLOTTABLE_MEASUREMENTS:
                
                data = []
                legend = []
                
                for test in self.tests:
                    if test.inputSize == testSize:
                        if 'y-data-calc' in plots[measurement]:
                            data.append(map(plots[measurement]['y-data-calc'],test.measurements[measurement]))
                        else:
                            data.append(test.measurements[measurement])
                        legend.append(test.toolName)
                
                ### Box plot
                fig = plt.figure(figsize=(16, 6))
                fig = fig.add_subplot(111)
                fig.boxplot(data, labels=legend, showfliers=False)
                fig.set_title(plots[measurement]['title'])
                fig.set_ylabel(plots[measurement]['y-label'])
                
                
                outFig = fig.get_figure()
                outFigFileName = 'box_%s_%s.png' % (testSize, measurement)
                outFig.savefig(outFigFileName)
                print 'Wrote to: %s' % outFigFileName
                del fig
                
                ### Scatter plot
                fig = plt.figure(figsize=(16, 6))
                fig = fig.add_subplot(111)
                for temp in data:
                    fig.plot(temp)
                fig.set_title(plots[measurement]['title'])
                fig.set_ylabel(plots[measurement]['y-label'])
                
                # save to file
                outFig = fig.get_figure()
                outFigFileName = 'scatter_%s_%s.png' % (testSize, measurement)
                outFig.savefig(outFigFileName)
                print 'Wrote to: %s' % outFigFileName
                del fig
                
class Test():
    def __init__(self, toolName, testNumber, inputSize, sbsPollingInterval, statsFileURL, rawDataFileURL):
        self.toolName = toolName
        self.testNumber = testNumber
        self.inputSize = inputSize
        self.sbsPollingInterval = sbsPollingInterval
        self.statsFileURL = statsFileURL
        self.rawDataFileURL = rawDataFileURL
        
        self.measurements = {}
        
        self.loadRawDataFile()
        
    def loadRawDataFile(self):
        if os.path.exists(self.rawDataFileURL):
            with open(self.rawDataFileURL, 'r') as rawDataFile:
                rawDataFile = rawDataFile.read()
                
                # setup measurement raw data arrays
                for measurement in MEASUREMENTS_IN_RAW_DATA_FILES:
                    self.measurements[measurement] = []
                
                # extract data line by line from CSV (skip header line)
                for line in rawDataFile.split('\n')[1:]:
                    if len(line) > 0:
                        lineSplit = line.split(',')
                        i = 0
                        for measurement in MEASUREMENTS_IN_RAW_DATA_FILES:
                            self.measurements[measurement].append(float(lineSplit[i]))
                            i = i + 1
        else:
            print 'rawDataFile does not exist: %s' % self.rawDataFileURL


class SbsStats():
    def __init__(self, inLen, inMin, inQ1, inMed, inAvg, inQ3, inMax, inStd):
        self.valLen = inLen
        self.valMin = inMin
        self.valQ1 = inQ1
        self.valMed = inMed
        self.valAvg = inAvg
        self.valQ3 = inQ3
        self.valMax = inMax
        self.valStd = inStd

def main(configFile, mode):    
    
    statsHandler = StatsHandlerClass(configFile)

    statsHandler.drawInterToolPlots()
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Aggregate Plotter for the Software Benchmarking Script')
    parser.add_argument('-c', help='Configuration file (csv formatted: [toolName,testNumber,inputSize,sbsPollingInterval,statsFileURL])')
    parser.add_argument('-m', help='Inter-tool (comparing same size test from different tools), Intra-tool (comparing different size tests from same tool) [inter|intra]')
    parser.add_argument('--wincntxmnu', help='Indicates SBS stats was launched from the Windows context menu. See README for help.', action='store_true')
    args = parser.parse_args()
    
    main(args.c, args.m)
