"""
This file contains logic for measuring the length of each block in a
railroad.

We presume that the blocks are on a loop that is part of a
model railroad mainline, which is to say that each block could be straight,
curved, on a grade, or otherwise have different characteristics. Accordingly,
we use a locomotive set at a steady throttle setting to calibrate the
length of each block, with the user supplying one measured block (in inches)
to facilitate calculations in scale miles per hour.
"""
import jmri
import java
import pickle
import os
from os.path import expanduser

from Utils import RedirectStdErr

class LayoutBlocks:
    def __init__(self, speedMatchInstance, throttleInstance, data):
        self.speedMatchInstance = speedMatchInstance
        self.throttle = throttleInstance
        self.data = data
        self.topSpeedTimeSecPerBlock = None
        self.timeSecPerBlockMeasurementsForward = None
        self.timeSecPerBlockMeasurementsReverse = None
        foldername = (expanduser("~") + "\\.SpeedMatchLocoTables\\")
        if not os.path.exists(foldername):
            os.mkdir(foldername)
        self.filename = ( foldername
                        + str(self.data["DCC Address"])
                        + str(self.data["Filename Suffix"])
                        + ".mbt" )

    def computeMeasuredBlockTopSpeedTime(self):
        self.topSpeedTimeSecPerBlock = {}
        for i in range(len(self.data["Measured Block Sensors"])):
            sensor = self.data["Measured Block Sensors"][i]
            length_inches = self.data["Measured Block Lengths (Inches)"][i]

            # in / sec = (mph * 1/scale * 1hr / 3600 sec * 5280ft / 1 mile * 12in / 1ft)
            inchesPerSecond = (self.data["Maximum Speed"] *
                1.0 / self.data["Scale"] *
                1.0 / (60 * 60) *
                5280 *
                12)

            # time in seconds
            # lower times are faster speeds - so stop measuring once you
            # get below the times in this dict
            self.topSpeedTimeSecPerBlock[sensor] = length_inches / inchesPerSecond

        print("Maximum Speed Times (sec) in Each Block: ", self.topSpeedTimeSecPerBlock)
        return

    """
    In this method, we measure the time in each block. Since a block should
    be active from when the front of an engine enters to when the rear of
    an engine leaves, we don't measure time from on until off. Instead, we watch
    for the activation of the first sensor - say LS1 - and then establish the
    block travel time as when the next sensor - say LS2 - becomes active,
    thereby measuring from the front of the engine to the front of the engine.

    If the block detector has non-deterministic delays from actual engine entry
    to sensor activation, this approach may cause problems. Dirty wheel pickups
    may cause these sorts of issues as well. For this reason, we sample the
    travel time on each block multiple times. Also see comments in the writeup
    about how, if you have "similar" blocks (i.e. all curves, all the same
    length, in a circle), then the velocity in each block should be the same
    for a given throttle setting, and accordingly you can use least squares
    across all the blocks to get a better time estimate. This won't work if
    the blocks are different (i.e. on your railroad mainline) and therefore
    the speed of the engine changes due to hills, curves, etc.

    One can optionall save to or load from disk, as this method is what takes
    most of the time in the SpeedMatch routine, waiting for the train to run
    around in circles.
    """
    def measureBlockTimes(self, minimumSamples=2, saveToFile=True):
        if self.data["Load Measurements"]:
            self._loadBlockTimes()
            return

        #cvValuesToMeasure = [16, 32, 48, 64, 80, 96, 112, 128,
        #                     144, 160, 176, 192, 208, 224, 240, 255]
        cvValuesToMeasure = [16, 32, 56, 80, 112, 144, 176, 208, 240, 255]

        self.timeSecPerBlockMeasurementsForward = {}
        self.timeSecPerBlockMeasurementsReverse = {}
        # Start with faster speeds, because you'll probably want to
        # watch the engine as it goes flying around on your twisty, hilly
        # mountain raiload. Maybe follow it with a net so it doesn't fall on
        # the floor. Conversely, the slower speeds will take forever and can
        # be unattended at lower risk.
        #fastCvValuesToMeasure = [el for el in cvValuesToMeasure if el > 200]
        #slowCvValuesToMeasure = [el for el in cvValuesToMeasure if el not in fastCvValuesToMeasure]

        #cvValuesToMeasure need to be in ascending order for the below
        #for forward in [True, False]:
        #    for cvValue in fastCvValuesToMeasure:
        #        maxSpeedFlag = self._measureBlockTime(forward, cvValue, minimumSamples)
        #        if maxSpeedFlag:
        #            break

        #for forward in [True, False]:
        #    for cvValue in slowCvValuesToMeasure:
        #        maxSpeedFlag = self._measureBlockTime(forward, cvValue, minimumSamples)
        #        if maxSpeedFlag:
        #            break

        for forward in [True, False]:
            for cvValue in cvValuesToMeasure:
                maxSpeedFlag = self._measureBlockTime(forward, cvValue, minimumSamples)
                if maxSpeedFlag:
                    break

        # save the table to disk
        if self.data["Save Measurements"]:
            self._saveBlockTimes()

        # stop the locomotive
        self.throttle.driveCv(cvValue=0, forward=True)

        return


    def _measureBlockTime(self, forward, cvValue, minimumSamples):
        self.throttle.driveCv(cvValue, forward=forward, speedTableStep=14)
        self.speedMatchInstance.waitMsec(300) # wait for momentum #TODO make 3000

        # do the measuring
        maxSpeedFlag = False
        measurements = {}

        def addMeasurement(sensor, time):
            if sensor not in measurements.keys():
                measurements[sensor] = [time, ]
            else:
                measurements[sensor].append(time)
            return

        oldSensor = None
        newTime = 0
        while True:
            # drive around by modifying speed table cv's
            self.throttle.driveCv(cvValue=cvValue, forward=forward)

            # wait for sensor changes and measure time
            newSensor = self._waitForBlockSensor()

            # update times and add measurement
            oldTime = newTime
            newTime = java.lang.System.currentTimeMillis()

            if oldSensor and not (oldTime == 0):
                # stop if we have collected enough samples
                if oldSensor in measurements.keys():
                    samplesThisSensor = len(measurements[oldSensor]) + 1
                    if samplesThisSensor > minimumSamples:
                        break
                else:
                    samplesThisSensor = 1

                # add the new sample
                timeSec = (newTime - oldTime) * 1.0/1000.0
                addMeasurement(oldSensor, timeSec)
                dirString = 'Fwd' if forward else 'Rev'
                print("Speed-" + dirString + " " + str(cvValue) +
                      ". Adding " + str(oldSensor) + " / " + str(timeSec) +
                      ". Block has " + str(samplesThisSensor) + " samples.")

                # only if this is a measured block - check speed constraints
                if oldSensor in self.topSpeedTimeSecPerBlock.keys():
                    # fast enough - stop checking higher speeds
                    if self.topSpeedTimeSecPerBlock[oldSensor] > timeSec:
                        maxSpeedFlag = True

                    # engine can't go fast enough - throw exception
                    if cvValue > 252:
                        if self.topSpeedTimeSecPerBlock[oldSensor] < timeSec:
                            raise Exception("Locomotive cannot reach top speed in smph at full voltage. Try a lower smph calibration speed.")

            oldSensor = newSensor

        if forward:
            self.timeSecPerBlockMeasurementsForward[cvValue] = measurements
        else:
            self.timeSecPerBlockMeasurementsReverse[cvValue] = measurements

        return maxSpeedFlag

    """
    returns name of the new sensor that became active
    """
    def _waitForBlockSensor(self):
        numChangedSensors = 0
        oldActiveSensors = self._pollActiveSensors()

        # JMRI fires a sensor change on either going active or non-active.
        # We only want the active ones, hence this loop.
        while numChangedSensors == 0:
            self.speedMatchInstance.waitChange(self.data["JMRI Sensors"].values())
            newActiveSensors = self._pollActiveSensors()

            recentlyActivatedSensors = []
            for sensor in oldActiveSensors.keys():
                if (oldActiveSensors[sensor] == True) and (newActiveSensors[sensor] == False):
                    continue
                if (oldActiveSensors[sensor] == False) and (newActiveSensors[sensor] == True):
                    recentlyActivatedSensors.append(sensor)
                    #print("oldActiveSensors[sensor]: ", oldActiveSensors[sensor])
                    #print("newActiveSensors[sensor]: ", newActiveSensors[sensor])
            #print("numChangedSensors: ", numChangedSensors)
            #print("recentlyActivatedSensors: ", recentlyActivatedSensors)
            numChangedSensors = len(recentlyActivatedSensors)
            #print('numChangedSensors: ', numChangedSensors)

        if not numChangedSensors == 1:
            print("oldActiveSensors: ", oldActiveSensors)
            print("newActiveSensors: ", newActiveSensors)
            print("recentlyActivatedSensors: ", str(recentlyActivatedSensors))
            raise Exception("More than one sensor changed state. Try ignoring broken sensors. Changed blocks include: ", str(recentlyActivatedSensors))

        newSensor = recentlyActivatedSensors[0]
        #print("newSensor: ", newSensor)
        return newSensor

    """
    polls the jmri sensors to see which one are active
    """
    def _pollActiveSensors(self):
        activeSensors = {}
        for sensor in self.data["JMRI Sensors"].keys():
            activeSensors[sensor] = (self.data["JMRI Sensors"][sensor].knownState == self.data["JMRI Sensor Active Const"] )
        return activeSensors

    def _saveBlockTimes(self):
        pickle.dump([self.timeSecPerBlockMeasurementsForward, self.timeSecPerBlockMeasurementsReverse],
                    open(self.filename, "wb" ))
        print("Time measurements written to disk at: " + self.filename)

    def _loadBlockTimes(self):
        r = pickle.load( open(self.filename, "rb") )
        self.timeSecPerBlockMeasurementsForward = r[0]
        self.timeSecPerBlockMeasurementsReverse = r[1]

    def getForwardMeasurements(self):
        return self.timeSecPerBlockMeasurementsForward

    def getReverseMeasurements(self):
        return self.timeSecPerBlockMeasurementsReverse

    def getTopSpeedTimePerMeasuredBlock(self):
        return self.topSpeedTimeSecPerBlock
