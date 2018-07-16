import matplotlib.pyplot as plt
import argparse, csv, numpy, time, os, re

# if a process contains any of these, then ignore it
termsToIgnore = ['/bin/bash', 'sh -c']

PLOT_OUTPUT_DPI = 150
 
def main(args):
    configFile = args.c
    termsFile = args.t
    outputDirectory = args.o
    generateListCmds = args.listCommands
    plotData = args.plot
    
    terms = []
    ### Process the terms file
    terms = processTermsFile(termsFile)
    data = []
    ### Read the configuration file
    with open(configFile, 'r') as fConfig:
        fConfig = fConfig.read()
        for configLine in fConfig.split('\n'):
            ### Each configuration line is a different test
            configLineSplit = configLine.split(',')
                
            if generateListCmds:
                print '\n'.join(generateListOfCommands(configLineSplit[4]))
            
            else:
                print '\n=== Running for %s %s' % (configLineSplit[0], configLineSplit[1])

                ### make sure this "test" is worthy of processing
                if len(configLineSplit) > 0:
                    pids = getListOfCommandsForTestAsDict(configLineSplit[4])
                    
                    ### process data
                    results = calculateChildrenStatistics(pids, terms)
                    results['totalParentTime'] = getMainProcessRunTime(configLineSplit[4])
                    results['totalCpuTime'] = results['totalParentTime'] + results['totalUnclassifiedChildTime'] + results['totalClassifiedChildTime']
                    #results['unknownParentTime'] = results['totalParentTime'] - results['totalUnclassifiedChildTime'] - results['totalClassifiedChildTime']
                    results['testInfo'] = configLineSplit
                    data.append(results)
                    if plotData:
                        filePrefix = '%s_%s' % (configLineSplit[0], configLineSplit[1])
                        plotTitlePrefix = '%s %s' % (configLineSplit[0], configLineSplit[1])
                        
                        # Pie: one chart per tool. each slice is a unique process.
                        plotChildProcessWallTimesPie(outputDirectory, filePrefix, plotTitlePrefix, results)
                        
        
        if plotData:
            # Bar: one chart per process type (terms). x-axis: tool name, y-axis: time
            plotTimeInClassifiedChildBar(outputDirectory, data, terms)

def plotChildProcessWallTimesPie(outputDirectory, filePrefix, plotTitlePrefix, results):
    fig = plt.figure(figsize=(8, 8))
    fig = fig.add_subplot(111)
    fig.set_title('Wall Time Distribution %s' % plotTitlePrefix)
    legend = results['classifiedChildTimes'].keys()
    data = results['classifiedChildTimes'].values()
    
    # make it a percentage
    data = [x / results['totalCpuTime'] for x in data]
    
    if len(legend) > 0:
        legend.append('Unknown')
        data.append((results['totalCpuTime'] - results['totalClassifiedChildTime']) / results['totalCpuTime'])
        fig.pie(data)
        fig.legend(legend)
        
        # save to file
        outFig = fig.get_figure()
        outFigFileName = '%spie_cpu_time_%s.png' % (outputDirectory, filePrefix)
        outFig.savefig(outFigFileName, dpi=PLOT_OUTPUT_DPI)
        print 'Wrote to: %s' % outFigFileName
        plt.clf()
                        
def plotTimeInClassifiedChildBar(filePrefix, inputData, terms):
    for testSize in ['500k', '1m', '5m', 'full']:
        for term in terms:
            legend = []
            data = []
            
            for result in inputData:
                if result['testInfo'][2] == testSize:
                    # check if the term was used by the tool
                    if term in result['classifiedChildTimes'].keys():
                        legend.append('%s-%s' % (result['testInfo'][0], result['testInfo'][2]))
                        data.append(result['classifiedChildTimes'][term])
            if len(legend) > 1:
                ### Bar chart
                plot = plt.figure(figsize=(16, 8))
                fig = plot.add_subplot(111)
                fig.set_ylabel('Run Time (seconds)')
                fig.set_xlabel('Tool Name')
                fig.set_title('Run Time in %s for %s input' % (term, testSize))
                fig.bar(legend, data)  
                
                # save to file
                outFig = fig.get_figure()
                outFigFileName = '%sbar_cmd_%s_%s.png' % (filePrefix, testSize, term.replace('/', '-'))
                outFig.savefig(outFigFileName, dpi=PLOT_OUTPUT_DPI)
                print 'Wrote to: %s' % outFigFileName
                plt.clf()
                plt.close(plot)
        
def generateListOfCommands(sbsBaseFile):
    ### open the child commands log files.
    
    # keep a record of all commands
    commands = []
    
    # the commands list file
    fChildCmdsListURL = '%s_child_cmds' % sbsBaseFile

    ### Open child_cmds file to get a list of commands
    with open(fChildCmdsListURL, 'r') as fChildCmdsList:
        fChildCmdsList = fChildCmdsList.read()

        for cmdListLine in fChildCmdsList.split('\n')[1::2]:
            # Every even line contains the command that was ran
            commands.append(cmdListLine.strip())

    return commands
    
def getMainProcessRunTime(sbsBaseFile):
    # calculates the run time for the entire test using the data in the
    # aggregate file.
    with open('%s_aggregate' % sbsBaseFile) as aggFile:
        aggFile = aggFile.read().split('\n')
        
        firstDataLine = aggFile[1].split(',')
        lastDataLine = aggFile[-2].split(',')
        
        return float(lastDataLine[0]) - float(firstDataLine[0])
    
    
def processTermsFile(termsFile):
    # extracts each term defined in the terms file
    # each term should represent a unique command that would be ran
    # eg: notepad.exe OR paint.exe OR chmod
    terms = []
    with open(termsFile, 'r') as fTerms:
        fTerms = fTerms.read()
        
        for termsLine in fTerms.split('\n'):
            terms.append(termsLine)
    return terms
    
def getListOfCommandsForTestAsDict(sbsBaseFile):
    ### open the child commands log files. there are two, described
    ### below. we need both!
    
    # keep a record of everything we are about to read
    pids = {}
    
    # what the actual command was
    fChildCmdsListURL = '%s_child_cmds' % sbsBaseFile
    
    # contains how long it ran for
    fChildCmdsListPlotURL = '%s_child_cmds_plot' % sbsBaseFile
    
    ### Open child_cmds file to get a list of commands
    with open(fChildCmdsListURL, 'r') as fChildCmdsList:
        fChildCmdsList = fChildCmdsList.read()
        
        # This file is not CSV and is messy... (TODO: update the format!)
        i = 1
        lastPid = 0
        for cmdListLine in fChildCmdsList.split('\n'):
            
            # Every odd line contains a PID (it will be the second value)
            if i % 2 == 1:
                cmdListLineSplit = cmdListLine.split(' ')
                if len(cmdListLineSplit) > 1:
                    pids[cmdListLineSplit[1]] = {}
                    pids[cmdListLineSplit[1]]['runTime'] = float(cmdListLineSplit[4])
                    lastPid = cmdListLineSplit[1]
                
            # Every even line contains the command that was ran
            if i % 2 == 0:
                pids[lastPid]['command'] = cmdListLine.strip()
                
            i = i + 1
            
    ### Open child_cmds_plit to get how long each command ran for
    with open(fChildCmdsListPlotURL, 'r') as fChildCmdsListPlot:
        fChildCmdsListPlot = fChildCmdsListPlot.read()
        
        for childCmdsListLine in fChildCmdsListPlot.split('\n'):
            childCmdsListLineSplit = childCmdsListLine.split(',')
            if len(childCmdsListLineSplit) > 1:
                if childCmdsListLineSplit[0] in pids:
                    if childCmdsListLineSplit[1] == 'None' or childCmdsListLineSplit[2] == 'None':
                        pids[childCmdsListLineSplit[0]]['run_time'] = 0
                    else:
                        pids[childCmdsListLineSplit[0]]['run_time'] = float(childCmdsListLineSplit[2]) - float(childCmdsListLineSplit[1])
                else:
                    print 'Unknown PID %s\n' % childCmdsListLineSplit[0]
    
    return pids
    
def calculateChildrenStatistics(pids, terms):
    results = { 'totalUnclassifiedChildTime' : 0, 
                'totalChildrenRan' : len(pids), 
                'totalNonIgnoredChildsRan' : 0, 
                'totalUniqueChildsRan' : 0, 
                'totalUnclassifiedChildCount' : 0, 
                'totalIgnoredChilds' : 0,
                'classifiedChildTimes' : {},
                'classifiedChildCounts' : {}
            }
    
    termsWeHaveMatchedWith = []
    
    # occurrs in any process...
    for pid in pids:
        process = pids[pid]
        didNotMatchAnyTerms = True
        containsIgnorableTerms = False
        
        # check if we want to ignore this command because it contained an ignorable term
        for termToIgnore in termsToIgnore:
            if termToIgnore in process['command']:
                containsIgnorableTerms = True
                results['totalIgnoredChilds'] = results['totalIgnoredChilds'] + 1
    
        # it did not contain an ignorable term
        if containsIgnorableTerms == False:
            
            results['totalNonIgnoredChildsRan'] = results['totalNonIgnoredChildsRan'] + 1
            
            # check each valid term...
            for term in terms:
                
                if term in process['command']:
                    # it just matched this term
                    didNotMatchAnyTerms = False
                    if term not in results:
                        results['classifiedChildTimes'][term] = process['run_time']
                        results['classifiedChildCounts'][term] = 1
                    else:
                        results['classifiedChildTimes'][term] = results['classifiedChildTimes'][term] + process['run_time']
                        results['classifiedChildCounts'][term] = results['classifiedChildCounts'][term] + 1
                    
                    if term not in termsWeHaveMatchedWith:
                        # assume that each term is unique
                        termsWeHaveMatchedWith.append(termsWeHaveMatchedWith)
                        results['totalUniqueChildsRan'] = results['totalUniqueChildsRan'] + 1
                        
            # if it didnt match any terms
            if didNotMatchAnyTerms:
                results['totalUnclassifiedChildTime'] = results['totalUnclassifiedChildTime'] + process['run_time']
                results['totalUnclassifiedChildCount'] = results['totalUnclassifiedChildCount'] + 1
                
    results['totalClassifiedChildTime'] = sum(results['classifiedChildTimes'].values())
    return results
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'SBS Child Process Analysis')
    parser.add_argument('-c', help='Configuration file (csv formatted: [toolName,testNumber,inputSize,sbsPollingInterval,statsFileURL])', required=True)
    parser.add_argument('-t', help='Terms file (to classify each process)', required=True)
    parser.add_argument('-o', help='Output directory (default: current)', required=False)
    parser.add_argument('-dpi', help='Output plot DPI (default: %s)' % (PLOT_OUTPUT_DPI))
    parser.add_argument('--listCommands', help='Prints a list of commands in the _child_cmds files', action='store_true')
    parser.add_argument('--plot', help='Plots the data', action='store_true')
    args = parser.parse_args()
    
    if args.dpi != None:
        PLOT_OUTPUT_DPI = int(args.dpi)
    
    if os.path.exists(args.c) == False:
        print 'Cannot open config file: %s' % args.c
        exit()
        
    if os.path.exists(args.t) == False:
        print 'Cannot open terms file: %s' % args.t
        exit()
        
    main(args) # top of file
