import matplotlib.pyplot as plt
import argparse, csv, os, re

def cpuPercentToDecimal(val):
    return (float(val) / 100.0)

def byteToMegabyte(val):
    return (float(val) / 1024.0 / 1024.0)

def main(resultsFile, toolName, childProcessFile, outputPrefix):    
    
    filesToPlot = []
    plotTitles = []
    
    if os.path.isfile(resultsFile):
        # the user must have defined an exact file to plot
        filesToPlot.append(resultsFile)
        plotTitles.append(toolName)
    else:
        # check if there are multiple files matching the criteria
        dir = (os.sep).join(resultsFile.split(os.sep)[:-1])
        fileNameStart = resultsFile.split(os.sep)[-1]
        for (dirpath, dirnames, filenames) in os.walk(dir):
            for filename in filenames:
                reMatch = re.search('%s_((aggregate|system)|(\d)+)\\b' % fileNameStart, filename)
                if bool(reMatch):
                    filesToPlot.append(os.path.join(dirpath, filename))
                    plotTitles.append('%s %s' %(toolName, reMatch.group(1).title()))
    
    # start plotting
    i = 0
    while i < len(filesToPlot):
        plot(filesToPlot[i], plotTitles[i], None, outputPrefix)
        i = i + 1

def plot(resultsFile, toolName, childProcessFile, outputPrefix):
    print 'Running for: %s\n' % toolName
    
    ELAPSED_TIME = []

    config = {
        'x-data-default': ELAPSED_TIME,
        'x-label-default' : 'Elapsed Time (sec)',
        'y-data-type-default' : int
    }

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

    # due to dictionaries not being in order, we need to know the order the data appears and
    # match it with the associated plot configuration above.
    headerOrder = []
    
    firstTime = None
    with open(resultsFile, 'r') as fcsv:
        dataCsv = csv.reader(fcsv, delimiter=',')

        # Set the headerOrder and remove the time column header
        headerOrder = dataCsv.next()
        del headerOrder[0]
        
        for row in dataCsv:
            # Elapsed time
            if firstTime == None:
                firstTime = row[0]
            ELAPSED_TIME.append(float(row[0]) - float(firstTime))

            i = 1 # skip zero as its the time (as above)
            for plot in headerOrder:
                if 'y-data-calc' in plots[plot]:
                    yVal = plots[plot]['y-data-calc'](row[i])
                else:
                    yVal = row[i]
                
                if 'y-data-type' in plots[plot]:
                    plots[plot]['y-data'].append(plots[plot]['y-data-type'](yVal))
                else:
                    plots[plot]['y-data'].append(config['y-data-type-default'](yVal))
                i += 1

	# find child process start and end markers from file
	childStartMarker = []
	childEndMarker = []
    if childProcessFile != None:
        with open(childProcessFile, 'r') as fchpro:
            dataCsv = csv.reader(fchpro, delimiter=',')
            for row in dataCsv:
                childStartMarker.append(float(row[1]) - float(firstTime))
                childEndMarker.append(float(row[3]) - float(firstTime))
	
    # start generating plots
    for plot in headerOrder:
        fig = plt.figure()
        fig = fig.add_subplot(111)
        
        # plot data
        if 'x-data' in plots[plot]:
            fig.plot(plots[plot]['x-data'], plots[plot]['y-data'], linewidth=1)
        else:
            fig.plot(config['x-data-default'], plots[plot]['y-data'], linewidth=1)

        # plot title
        if toolName == None:
            fig.set_title(plots[plot]['title'])
        else:
            fig.set_title('%s : %s' % (toolName, plots[plot]['title']))
            
        # x axis label
        if 'x-label' in plots[plot]:
            fig.set_xlabel(plots[plot]['x-label'])
        else:
            fig.set_xlabel(config['x-label-default'])

        # y axis label    
        fig.set_ylabel(plots[plot]['y-label'])

		# draw on child process markers
        markers = ['.', '^', '>', '<', 's', 'p', '*', 'h', 'H', '+', 'x', 'D', 'd', '|', '_']
        for i in range(len(childStartMarker)):
            fig.plot(childStartMarker[i], 0, color='g', marker=markers[i])
            fig.plot(childEndMarker[i], 0, color='r', marker=markers[i])
        
        # save to file
        outFig = fig.get_figure()
        outFigFileName = '%s_%s.png' % (outputPrefix, plot)
        outFig.savefig(outFigFileName)
        print 'Wrote to: %s' % outFigFileName
        del fig
        #plt.show(block=False)

    print '\nFinished.'
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Plotter for the Software Benchmarking Script')
    parser.add_argument('-f', help='Results file as input (CSV)')
    parser.add_argument('-t', help='Name of tool to appear in graph titles', default=None)
    parser.add_argument('-c', help='[Broken!] File containing child spawning data (CSV)', default=None)
    parser.add_argument('-o', help='Output prefix (directory and file name prefix). Default is input provided in -f flag', default=None)
    parser.add_argument('--wincntxmnu', help='Indicates SBS plotter was launched from the Windows context menu. See README for help.', action='store_true')
    args = parser.parse_args()
    
    # adjust outputPrefix
    if args.o == None:
        args.o = args.f
        
    if args.wincntxmnu:
        args.t = raw_input('Enter the plot prefix: ')
    
    main(args.f, args.t, args.c, args.o)
