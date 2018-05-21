import psutil, time, argparse, os, signal, sys
from subprocess import PIPE

MEASUREMENT_TYPE_INSTANT = 1
MEASUREMENT_TYPE_CUMULATIVE = 2

class SbsMeasurement():
    def __init__(self, inName, inType, outFileName=None):
        self.name = inName
        self.lastValue = 0
        self.delta = 0
        self.cumulative = 0
        self.type = inType # MEASUREMENT_TYPE_CUMULATIVE, MEASUREMENT_TYPE_INSTANT
        
        if outFileName != None:
            self._outCsv = open(outFileName, 'w+')
        self._values = []
        
    def update(self, newValue):
        # even though some of this data may be meaningless for some measurements,
        # we will keep it anyway.
        self.delta = newValue - self.lastValue
        self.lastValue = newValue
        self.cumulative = self.cumulative + self.delta
        
        self._values.append(newValue)
        self._outCsv.write('%s\n' % newValue)    
    
def main():
    i = 0
    test = SbsMeasurement('testMeasurement', MEASUREMENT_TYPE_CUMULATIVE, 'testMeasurement.csv')
    while i < 10:
        print i
        test.update(i)
        i = i + 1
        
if __name__ == "__main__":

    main()