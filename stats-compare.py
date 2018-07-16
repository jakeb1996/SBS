import matplotlib.pyplot as plt
import argparse, csv, numpy, time, os, re

def byteToMegabyte(val):
    return (float(val) / 1024.0 / 1024.0)

def cpuPercentToDecimal(val):
    return (float(val) / 100.0)
    
SBS_STATS_NUMBER_MEASUREMENTS = 10
FULL_INPUT_SIZE_INTEGER = 61431566 
SCATTER_LINE_WIDTH = 0.75
PLOT_OUTPUT_DPI = 150
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
    def __init__(self, configFile, outputDirectory):
        self.init = True
        self.outputDir = outputDirectory
        self.tests = []
        self.toolNames = []

        if os.path.exists(configFile):
            print 'Reading configuration file: %s' % configFile
            with open(configFile, 'r') as configFile:
                configFileRaw = configFile.read()
                
                for line in configFileRaw.split('\n'):
                    lineSplit = line.split(',')
                    self.tests.append(Test(lineSplit[0], lineSplit[1], lineSplit[2], lineSplit[3], lineSplit[4]))
                    
                    if lineSplit[0] not in self.toolNames:
                        self.toolNames.append(lineSplit[0])
        else:
            print 'configFile does not exist: %s' % configFile
            exit()
    
    
    
    
    
    def drawSystemResourcesBoxScatterPerTool(self):
        for testSize in VALID_TEST_INPUT_SIZES:
            for measurement in PLOTTABLE_MEASUREMENTS:
                
                data = []
                timePoints = []
                legend = []
                
                for test in self.tests:
                    if test.inputSize == testSize and test.toolName in ['CRISPR-ERA', 'CasFinder', 'CHOP-CHOP', 'mm10-CRISPR-Database']:
                        if 'y-data-calc' in plots[measurement]:
                            data.append(map(plots[measurement]['y-data-calc'],test.measurements[measurement]))
                        else:
                            data.append(test.measurements[measurement])
                        legend.append(test.toolName)
                        timePoints.append(test.elapsedTimePoints)
                
                ### Box plot (x-axis: tool-name, y-axis: system resource measurement)
                fig = plt.figure(figsize=(18, 6))
                fig = fig.add_subplot(111)
                #plt.yscale('log')
                fig.boxplot(data, labels=legend, showfliers=False)
                fig.set_title('%s - %s' % (plots[measurement]['title'], testSize))
                fig.set_ylabel(plots[measurement]['y-label'])
                
                
                outFig = fig.get_figure()
                outFigFileName = '%s/box_%s_%s.png' % (self.outputDir, testSize, measurement)
                outFig.savefig(outFigFileName, dpi=PLOT_OUTPUT_DPI)
                print 'Wrote to: %s' % outFigFileName
                plt.clf()
                
                ### Scatter plot (x-axis: tool-name, y-axis: system resource measurement)
                fig = plt.figure(figsize=(18, 6))
                fig = fig.add_subplot(111)
                i = 0
                while i < len(data):
                    fig.plot(timePoints[i], data[i], linewidth=SCATTER_LINE_WIDTH)
                    i = i + 1
                fig.set_title('%s - %s' % (plots[measurement]['title'], testSize))
                fig.set_ylabel(plots[measurement]['y-label'])
                fig.set_xlabel('Elapsed Time (seconds)')
                fig.legend(legend, loc='center left', bbox_to_anchor=(1, 0.5)) 
                
                # save to file
                outFig = fig.get_figure()
                outFigFileName = '%s/scatter_%s_%s.png' % (self.outputDir, testSize, measurement)
                outFig.savefig(outFigFileName, dpi=PLOT_OUTPUT_DPI)
                print 'Wrote to: %s' % outFigFileName
                plt.clf()

            ### Run Time (bar graph - x: tool name, y: run time)
            legend = []
            data = []
            for test in self.tests:
                if test.inputSize == testSize:
                    data.append(max(test.measurements['time']) - min(test.measurements['time']))
                    legend.append(test.toolName)
                    
            data, legend = self.sortDataAndLabelsDescending(legend, data)

            fig = plt.figure(figsize=(18, 6))
            fig = fig.add_subplot(111)
            fig.bar(legend, data)
            fig.set_title('%s - %s' % ('Runtime', testSize))
            fig.set_ylabel('Run Time (seconds)')
            
            # save to file
            outFig = fig.get_figure()
            outFigFileName = '%s/bar_run-time_test-size-%s.png' % (self.outputDir, testSize)
            outFig.savefig(outFigFileName, dpi=PLOT_OUTPUT_DPI)
            print 'Wrote to: %s' % outFigFileName
            plt.clf()
    
    def drawRunTimeBoxLogLinearPerInputSize(self):
        ### Run time (box plot - x: input size, y: run time) 
        legend = VALID_TEST_INPUT_SIZES
        data = [] #[[]] * len(VALID_TEST_INPUT_SIZES) # [[], [], []]
        for i in VALID_TEST_INPUT_SIZES:
            data.append([])
        
        for test in self.tests:
            data[VALID_TEST_INPUT_SIZES.index(test.inputSize)].append(test.elapsedTimePoints[-1]) 
        # linear y scale
        fig = plt.figure(figsize=(18, 6))
        fig = fig.add_subplot(111)
        fig.boxplot(data, labels=legend, showfliers=False)
        fig.set_title('Run time vs Input size')
        fig.set_ylabel('Run Time (seconds)')
        fig.set_xlabel('Input Size')
        plt.grid(True, which='both', axis='both', color='#e8e8e8')
        
        outFig = fig.get_figure()
        outFigFileName = '%s/box_run-time_all-tools_linear.png' % (self.outputDir)
        outFig.savefig(outFigFileName, dpi=PLOT_OUTPUT_DPI)
        print 'Wrote to: %s' % outFigFileName
        plt.clf()
        
        # same plot, log y scale
        fig = plt.figure(figsize=(18, 6))
        fig = fig.add_subplot(111)
        fig.boxplot(data, labels=legend, sym='+')
        fig.set_title('Run time vs Input size')
        fig.set_ylabel('Run Time (seconds)')
        fig.set_xlabel('Input Size')
        plt.yscale('log')
        plt.grid(True, axis='y', color='#e8e8e8')
        
        outFig = fig.get_figure()
        outFigFileName = '%s/box_run-time_all-tools_log.png' % (self.outputDir)
        outFig.savefig(outFigFileName, dpi=PLOT_OUTPUT_DPI)
        print 'Wrote to: %s' % outFigFileName
        plt.clf()
    
    def drawRunTimeScatterOfAllTools(self):
        ### Run time (scatter - x: input size, y: run time)
        fig = plt.figure(figsize=(18, 6))
        fig = fig.add_subplot(111)
        fig.set_title('Run Time')
        fig.set_ylabel('Run Time (seconds)')
        fig.set_xlabel('Input Size')
        #fig.set_xscale("log")
        legend = []
        for tool in self.toolNames:
            x = []
            y = []
            for test in self.tests:
                if test.toolName == tool:
                    y.append(max(test.measurements['time']) - min(test.measurements['time']))
                    x.append(test.intInputSize)
            
            
            if True: #tool in ['CRISPR-ERA', 'CasFinder', 'CHOP-CHOP', 'mm10-CRISPR-Database']: #['CT-Finder', 'CRISPR-DO', 'CHOP-CHOP', 'mm10-CRISPR-Database']: #len(y) == 4 and tool not in ['GuideScan']:# and tool not in ['sgRNA Scorer 2.0', 'GT-Scan', 'CRISPOR', 'CT-Finder']:
                legend.append(tool)
                fig.plot(x, y, marker='.', linewidth=SCATTER_LINE_WIDTH)
        fig.legend(legend, loc='center left', bbox_to_anchor=(1, 0.5))   
        # save to file
        outFig = fig.get_figure()
        outFigFileName = '%s/scatter_run-time_all-tools.png' % (self.outputDir)
        outFig.savefig(outFigFileName, dpi=PLOT_OUTPUT_DPI)
        print 'Wrote to: %s' % outFigFileName
        plt.clf()
    
    def drawSbsPlotterForAllTools(self):
        for test in self.tests:
            toolName = '%s_%s' % (test.toolName, test.inputSize)
            outputPrefix = '%s/tool_%s' % (self.outputDir, toolName)
            os.system("python plotter.py -f %s -t %s -o %s" % (test.aggregateFileURL, toolName, outputPrefix))
    
    def drawInterToolPlots(self):
        # [comparing tools (ie: x-axis: tool name)]  
        self.drawSystemResourcesBoxScatterPerTool()
        
        # [comparing input size (ie: x-axis: input size)]
        #self.drawRunTimeBoxLogLinearPerInputSize()
        
        #self.drawRunTimeScatterOfAllTools()
        
        
        #self.drawSbsPlotterForAllTools()
        
        
        
        
        
    def drawIntraToolPlots(self):
        # [per tool]
        for tool in self.toolNames:
            
            ### Run Time (scatter - x: input size, y: run time)
            x = []
            y = []
            
            for test in self.tests:
                if test.toolName == tool:
                    y.append(max(test.measurements['time']) - min(test.measurements['time']))
                    x.append(test.intInputSize)

            ### Scatter plot
            fig = plt.figure(figsize=(18, 6))
            fig = fig.add_subplot(111)
            fig.plot(x, y, marker='o', linewidth=SCATTER_LINE_WIDTH)
            fig.set_title('%s - %s' % ('Runtime', tool))
            fig.set_ylabel('Run Time (seconds)')
            fig.set_xlabel('Input Size')
            
            # save to file
            outFig = fig.get_figure()
            outFigFileName = '%s/scatter_run-time_%s.png' % (self.outputDir, tool)
            outFig.savefig(outFigFileName, dpi=PLOT_OUTPUT_DPI)
            print 'Wrote to: %s' % outFigFileName
            plt.clf()

    def sortDataAndLabelsDescending(self, xLabels, yData):
        return (list(t) for t in zip(*sorted(zip(yData, xLabels), reverse=True)))
    
class Test():
    def __init__(self, toolName, testNumber, inputSize, sbsPollingInterval, sbsBaseFileName):
        self.toolName = toolName
        self.testNumber = testNumber
        self.inputSize = inputSize
        self.intInputSize = self._humanInputSizeToInteger(self.inputSize)
        self.sbsPollingInterval = sbsPollingInterval
        self.aggregateFileURL = '%s_%s' % (sbsBaseFileName, 'aggregate')
        
        self.measurements = {}
        self.elapsedTimePoints = []
        self.loadRawDataFile()
        
    def loadRawDataFile(self):
        if os.path.exists(self.aggregateFileURL):
            print 'Reading data file: %s' % self.aggregateFileURL
            with open(self.aggregateFileURL, 'r') as rawDataFile:
                rawDataFile = rawDataFile.read()
                
                # setup measurement raw data arrays
                for measurement in MEASUREMENTS_IN_RAW_DATA_FILES:
                    self.measurements[measurement] = []
                
                # extract data line by line from CSV (skip header line)
                firstTimePoint = 0
                for line in rawDataFile.split('\n')[1:]:
                    if len(line) > 0:
                        lineSplit = line.split(',')
                        i = 0
                        for measurement in MEASUREMENTS_IN_RAW_DATA_FILES:
                            self.measurements[measurement].append(float(lineSplit[i]))
                            i = i + 1
                        if firstTimePoint == 0:
                            firstTimePoint = float(lineSplit[0])
                        self.elapsedTimePoints.append(float(lineSplit[0]) - firstTimePoint)
                        
        else:
            print 'rawDataFile does not exist: %s' % self.aggregateFileURL
            exit()

    def _humanInputSizeToInteger(self, humanInputSize):
        if humanInputSize == 'full':
            return FULL_INPUT_SIZE_INTEGER
        suffixes = {'k' : 1000, 'm' : 1000000, 'g': 1000000000}
        return int(humanInputSize[:-1]) * suffixes[humanInputSize[-1]]
        
        
        
def main(configFile, outputDirectory):    
    
    statsHandler = StatsHandlerClass(configFile, outputDirectory)

    print 'Drawing inter-tool plots...'
    statsHandler.drawInterToolPlots()
    
    #print 'Drawing intra-tool plots...'
    statsHandler.drawIntraToolPlots()
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Aggregate Plotter for the Software Benchmarking Script')
    parser.add_argument('-c', help='Configuration file (csv formatted: [toolName,testNumber,inputSize,sbsPollingInterval,sbsOutputBaseFileName])', required=True)
    parser.add_argument('-m', help='Inter-tool (comparing same size test from different tools), Intra-tool (comparing different size tests from same tool) [inter|intra]')
    parser.add_argument('-o', help='Output directory (default: current)', required=True)
    parser.add_argument('-dpi', help='Output plot DPI (default: %s)' % (PLOT_OUTPUT_DPI))
    parser.add_argument('--wincntxmnu', help='Indicates SBS stats was launched from the Windows context menu. See README for help.', action='store_true')
    args = parser.parse_args()
    
    if args.dpi != None:
        PLOT_OUTPUT_DPI = int(args.dpi)
    
    main(args.c, args.o)
