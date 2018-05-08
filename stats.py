import matplotlib.pyplot as plt
import argparse, csv, numpy

def main(resultsFile, toolName):
    print 'Running for: %s\n' % toolName
    
    ELAPSED_TIME = []

    config = {
        'data-type-default' : int
    }

    # the aggregate functions to perform on each set. each is a function name.
    # user-defined functions at bottom of file
    stats = [len, min, q1, median, avg, q3, max]

    measurements = {
 # measurement configurations must appear in the order of the associated CSV columns      
 # --- sample ---       
 #       'stat_name' : {
 #               ['data-type' : float,]
 #               'data' : [],
 #               'title' : 'measurement title'
 #       },
 # --- end sample ---       
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
    
    with open(resultsFile, 'r') as fcsv:
        dataCsv = csv.reader(fcsv, delimiter=',')

        # Set the headerOrder and remove the time column header
        headerOrder = dataCsv.next()
        del headerOrder[0]
        
        firstTime = None
        for row in dataCsv:
            
            # Elapsed time
            if firstTime == None:
                firstTime = row[0]
            ELAPSED_TIME.append(float(row[0]) - float(firstTime))

            i = 1 # skip zero as its the time (as above)
            for measurement in headerOrder:
                if 'data-type' in measurements[measurement]:
                    measurements[measurement]['data'].append(measurements[measurement]['data-type'](row[i]))
                else:
                    measurements[measurement]['data'].append(config['data-type-default'](row[i]))
                i += 1

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

    print '\nFinished.'
        
def q1(seq):
    return numpy.percentile(seq, 25)

def median(seq):
    return numpy.percentile(seq, 50)

def avg(seq):
    return sum(seq) / len(seq)

def q3(seq):
    return numpy.percentile(seq, 75)

def funcName(func):
    return func.__name__

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Plotter for the Software Benchmarking Script')
    parser.add_argument('-f', help='Results file as input (in csv format)')
    parser.add_argument('-t', help='Name of tool', default=None)
    args = parser.parse_args()

    main(args.f, args.t)
