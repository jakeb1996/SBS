import matplotlib.pyplot as plt
import argparse, csv, numpy, time

def main(resultsFile, toolName):
    print 'Running for: %s\n' % toolName
    
    TIME_ELAPSED = []
    TIME_GAPS = []
    
    config = {
        'data-type-default' : int
    }

    # the aggregate functions to perform on each set. each is a function name.
    # user-defined functions at bottom of file
    stats = [len, min, q1, median, mean, q3, max, std]

    measurements = {
 # measurement configurations must appear in the order of the associated CSV columns      
 # --- sample ---       
 #       'stat_name' : {
 #               ['data-type' : float,]
 #               'data' : [],
 #               'title' : 'measurement title'
 #       },
 # --- end sample ---
        'time' : {
                'data' : [],
                'data-type' : float,
                'title' : 'Time'
        },
        'num_threads' : {
                'data' : [],
                'title' : 'Number of Threads'
        },
        'cpu_percent' : {
                'data' : [],
                'data-type' : float,
                'title' : 'CPU Utilisation'
        },
        'mem_rss' : {
                'data' : [],
                'data-type' : float,
                'title' : 'Resident Set Size (RSS) Memory Utilisation'
        },
        'mem_vms' : {
                'data' : [],
                'title' : 'Virtual Memory Size (VMS) Memory Utilisation'
        },
        'io_read_count' : {
                'data' : [],
                'title' : 'Disk IO Read Count'
        },
        'io_read_bytes' : {
                'data' : [],
                'title' : 'Disk IO Read Volume'
        },
        'io_write_count' : {
                'data' : [],
                'title' : 'Disk IO Write Count'
        },
        'io_write_bytes' : {
                'data' : [],
                'title' : 'Disk IO Write Volume'
        },
        'child_process_count' : {
                'data' : [],
                'title' : 'Child Process Spawning'
        }
    }
    
    # due to dictionaries not being in order, we need to know the order the data appears and
    # match it with the associated plot configuration above.
    headerOrder = []
    
    # put all the times in a list
    timeRecords = []
    
    with open(resultsFile, 'r') as fcsv:
        dataCsv = csv.reader(fcsv, delimiter=',')

        # Set the headerOrder and remove the time column header
        headerOrder = dataCsv.next()
        
        firstTime = None
        for row in dataCsv:
            
            # Elapsed time
            
            timeRecords.append(float(row[0]))
            TIME_ELAPSED.append(float(row[0]) - float(timeRecords[0]))
    
            if firstTime == False:
                TIME_GAPS.append(float(row[0]) - measurements['time']['data'][-1])
            
            i = 0 # skip zero as its the time (as above)
            for measurement in headerOrder:
                if 'data-type' in measurements[measurement]:
                    measurements[measurement]['data'].append(measurements[measurement]['data-type'](row[i]))
                else:
                    measurements[measurement]['data'].append(config['data-type-default'](row[i]))
                i += 1
            
            firstTime = False
            
    resultsFileName = '%s_stats.csv' % resultsFile
    with open(resultsFileName, 'w') as scsv:
        print 'Writing to file: %s' % resultsFileName

        # write headers line
        scsv.write('measurement,%s\n' % ','.join(map(funcName, stats)))

        for measurement in headerOrder:
            line = '%s' % measurement
            for stat in stats:
                line = ('%s,%s' % (line, stat(measurements[measurement]['data'])))
            scsv.write('%s\n' % line)

        # now, because the time gaps were calculated separately, run the stats on them tool
        # messy, I know. sorry!
        line = '%s' % 'time_gaps'
        for stat in stats:
            line = ('%s,%s' % (line, stat(TIME_GAPS)))
        scsv.write('%s\n' % line)
   
        # write start and end time
        scsv.write('start_time,%s,"%s"\nend_time,%s,"%s"\nTIME_ELAPSED,%s,sec,%s,min' % (timeRecords[0], time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timeRecords[0])), timeRecords[-1], time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timeRecords[-1])), (timeRecords[-1] - timeRecords[0]), ((timeRecords[-1] - timeRecords[0]) / 60)))
        
    print '\nFinished.'
        
def q1(seq):
    return numpy.percentile(seq, 25)

def median(seq):
    return numpy.percentile(seq, 50)

def mean(seq):
    return sum(seq) / len(seq)

def q3(seq):
    return numpy.percentile(seq, 75)

def std(seq):
    return numpy.std(seq)

def funcName(func):
    return func.__name__


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Plotter for the Software Benchmarking Script')
    parser.add_argument('-f', help='Results file as input (in csv format)')
    parser.add_argument('-t', help='Name of tool', default=None)
    args = parser.parse_args()

    main(args.f, args.t)
