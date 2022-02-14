"""
Builds the speed table using the measured block data from LayoutBlocks.

Normally you'd do this with numpy and scipy for a SVD, but those are difficult
to integrate into Jython (see notes README.md).
"""
from math import log, exp
from Utils import median

class SpeedTableBuilder:
    def __init__(self, layoutBlocksInstance):
        self.layoutBlocksInstance = layoutBlocksInstance

    """
    Takes raw measurements from LayoutBlocks and outputs nested dicts of
    the following format:
    {'LS1' : { cvValue1 : measuredTime1, cvValue2 : measuredTime2, ...},
     'LS2' : { cvValue1 : measuredTime1, cvValue2 : measuredTime2, ...},
     ... }

    Note that each CV value generally has multiple time measurements for each
    block. We take the median time measurement, so as to filter out blocks
    where an engine stalled or other issues occur (only really effective if
    you have 3 or more datapoints per block).

    Also, if the forward and reverse times for a block are wildly different,
    this is typically because the block next to the block in question either
    had an ignored / faulty detector or no detector at all. Since block time
    is determined by time to the *next* block, that means block times will
    be very different depending on which direction the train drives. Accordingly,
    we remove these blocks from the final output of this method.
    """

    def preprocessCvToBlockTimeDataTables(self):
        # both of these in the nested dict format:
        # forwardMeasurements[cvValue][sensor]
        forwardMeasurements = self.layoutBlocksInstance.getForwardMeasurements()
        reverseMeasurements = self.layoutBlocksInstance.getReverseMeasurements()

        # restrict to sensors in both dicts, at every speed step
        sensorCount = {}
        for cv in forwardMeasurements.keys():
            forwardSensors = forwardMeasurements[ cv ].keys()
            reverseSensors = reverseMeasurements[ cv ].keys()
            commonSensors = [el for el in forwardSensors if el in reverseSensors]
            for sensor in commonSensors:
                if sensor in sensorCount.keys():
                    sensorCount[sensor] += 1
                else:
                    sensorCount[sensor] = 1
        sensorCountMax = max(sensorCount.values())
        sensors = [el for el in sensorCount.keys() if sensorCount[el] == sensorCountMax]

        # compute medians and filter blocks with different fwd / rev times
        self.processedMeasurementsForward = {}
        self.processedMeasurementsReverse = {}
        for sensor in sensors:
            forwardTimes = {}
            reverseTimes = {}
            saveFlag = True
            for cv in forwardMeasurements.keys():
                forwardMedianBlockTime = median(forwardMeasurements[cv][sensor])
                reverseMedianBlockTime = median(reverseMeasurements[cv][sensor])
                forwardTimes[cv] = forwardMedianBlockTime
                reverseTimes[cv] = reverseMedianBlockTime
                # Note: On some brass steam engines, especially at lower
                # speeds, you can really get a factor of 2 difference between
                # forward and reverse directions at the same speed table CV
                # value. Therefore, the check below has been disabled for now,
                # and comments have been added to README.md on finding a better
                # way of handling this plus computations for the forward and
                # reverse trim values.
                #
                # if times are sort of close
                #if ( (forwardMedianBlockTime / reverseMedianBlockTime < 1.25) and
                #     (forwardMedianBlockTime / reverseMedianBlockTime > 0.75) ):
                #    forwardTimes[cv] = forwardMedianBlockTime
                #    reverseTimes[cv] = reverseMedianBlockTime
                #else:
                #    # throw out this block
                #    saveFlag = False
                #    break

            if saveFlag:
                self.processedMeasurementsForward[sensor] = forwardTimes
                self.processedMeasurementsReverse[sensor] = reverseTimes

        return

    """
    Returns an estimated block time given a (CV value * trim)

    Linearly interpolates between data points, except at slow speeds.
    TODO: Better interpolation. Especially as the speed approaches
    zero, the time approaches infinity. This isn't a linear or even
    piecewise affine function. (Again, not done because of lack of
    numpy library)

    Note: Somewhat fixing the above issue by interpolating
    in log space. Since distance = speed * time,
    time is proportional to 1/speed.

    sensor: name of sensor for block time estimate
    cvValueTimesTrim: speed table CV value * decoder trim
    forward: forward if True; reverse otherwise

    returns: time in seconds
    """
    def _funcCvValueTimesTrimToTime(self, sensor, cvValueTimesTrim, forward):
        if forward:
            data = self.processedMeasurementsForward[sensor]
        else:
            data = self.processedMeasurementsReverse[sensor]

        measuredCvs = sorted(list(data.keys()))

        # if below or at minimum measurement
        if cvValueTimesTrim <= measuredCvs[0]:
            # linearly interpolate below lowest speed measurement
            # TODO: Could replace lower data value with "big honking number"
            slope = ( (log(data[measuredCvs[1]]) - log(data[measuredCvs[0]])) *
                      1.0 / (measuredCvs[1] - measuredCvs[0]) )
            run = measuredCvs[0] - cvValueTimesTrim
            belowMinMeasurement = exp(log(data[measuredCvs[0]]) - slope * run)
            # return belowMinMeasurement
            # Note: the above tends to result in CV values that are much
            # too small. Instead, we're going to return (big) here and then
            # linearly interpolate the CV values from the lowest nonchanging
            # CV value once the final table is built later.
            return 9999999999999999
        # if above max measurement
        elif cvValueTimesTrim > measuredCvs[-1]:
                # linearly interpolate based on slope of top two measurements
                # probably never hit this case
                slope = ( (log(data[measuredCvs[-1]]) - log(data[measuredCvs[-2]])) *
                          1.0 / (measuredCvs[-1] - measuredCvs[-2]) )
                run = cvValueTimesTrim - measuredCvs[-1]
                aboveMaxMeasurement = exp(slope * run + log(data[measuredCvs[-1]]))
                return aboveMaxMeasurement
        else:
            # we're between two points
            # find bottom point
            for i in range(len(measuredCvs)):
                if ( cvValueTimesTrim > measuredCvs[i] and
                     cvValueTimesTrim <= measuredCvs[i+1]):
                     lowCv = measuredCvs[i]
                     highCv = measuredCvs[i+1]
                     slope = ( (log(data[highCv]) - log(data[lowCv])) *
                                1.0 / (highCv - lowCv) )
                     run = cvValueTimesTrim - lowCv
                     betweenMeasurements = exp(slope * run + log(data[lowCv]))
                     return betweenMeasurements

    """
    Builds the engine CV 28 step speed table for one direction

    forward: forward if True; reverse otherwise
    sensor: name of sensor for this block
    maxSmphTime: time calculated to correspond with the calibration
                 to a maximum number of scale miles per hour. This is
                 based on the measured length of the block.

    TODO: Because of the horrible interpolation in
    _funcCvValueTimesTrimToTime, the first few speed steps may wind
    up being zero. We do some linear interpolation to the first nonzero
    CV value, but this could really be improved.

    returns: 28 element list of CV values
    """
    def _speedTableBuilderOneDirection(self, forward, sensor, maxSmphTime):
        # set desired block time for each step, 1-28
        steps = range(1,29)
        desiredTimes = [maxSmphTime * 28 * 1.0/step for step in steps ]
        tableCvs = []
        for i in range(len(steps)):
            # incrementing the CV value decreases the block time estimate
            for cvValueTimesTrim in range(1,256):
                newBlockTimeEstiamte = self._funcCvValueTimesTrimToTime(
                                       sensor, cvValueTimesTrim, forward)
                #print('step: ' + str(i) + " cvValueTimesTrim: " + str(cvValueTimesTrim) + " newBlockTimeEstimate: " + str(newBlockTimeEstiamte) + " desiredTimes[step]: " + str(desiredTimes[i]))
                if newBlockTimeEstiamte <= desiredTimes[i]:
                    # we're done - add nearest neighbor cv to table
                    oldBlockTimeEstimate = self._funcCvValueTimesTrimToTime(
                                           sensor, cvValueTimesTrim - 1, forward)
                    if ( abs(newBlockTimeEstiamte - desiredTimes[i]) <
                         abs(oldBlockTimeEstimate - desiredTimes[i]) ):
                         tableCvs.append(cvValueTimesTrim)
                    else:
                         tableCvs.append(cvValueTimesTrim - 1)
                    break
                elif cvValueTimesTrim == 255:
                    # we're at the top speed step, but still not moving
                    # quickly enough to hit the desiredTime target.
                    tableCvs.append(255)

        if not len(tableCvs) == 28:
            print("tableCvs: " + str(tableCvs))
            raise Exception("Not all CVs mapped.")

        # fix initial constants in the speed table. See comments above
        # about interpolation issues
        vStart = int(self.layoutBlocksInstance.data["vStart"])
        for i in range(28):
            if not tableCvs[i] == tableCvs[0]:
                break
        slope = (tableCvs[i] - vStart) * 1.0 / (i + 1)
        for cv in range(0,i):
            tableCvs[cv] = int(round(slope * (cv + 1)))

        return tableCvs

    """
    Builds the engine CV 28 step speed table based on data collected
    from one sensor.

    TODO: Note that you have a forward and reverse speed table based on the
    measurements from the block. However, the DCC standard only specifies one
    table and two trim values. The correct way to solve this is to create a
    rank-2 matrix of the two speed tables, then use a singular value
    decomposition to decompose that into one vector (the 28 step table) and
    two gain values (the trims). Unfortunately, we don't get numpy's SVD
    function due to use of Jython here. One could manually implement even
    a slow SVD method here.

    For now, we're going to average the forward and reverse tables and ignore
    the trim. Depending on how well engines actually run together in practice,
    this may be revised later.


    sensor: name of sensor for this block
    maxSmphTime: time calculated to correspond with the calibration
                 to a maximum number of scale miles per hour. This is
                 based on the measured length of the block.

    returns: 28 element list of CV values
    """
    def _blockSpeedTableBuilder(self, sensor, maxSmphTime):
        table_fwd = self._speedTableBuilderOneDirection(forward=True,
                                    sensor=sensor, maxSmphTime=maxSmphTime)
        table_rev = self._speedTableBuilderOneDirection(forward=False,
                                    sensor=sensor, maxSmphTime=maxSmphTime)
        table = []
        for i in range(len(table_fwd)):
            table.append(0.5 * (table_fwd[i] + table_rev[i]))

        return table

    """
    builds a 28 step seed table based on times for measured-length blocks

    returns: 28 element list of CV values
    """
    def buildSpeedTableForMeasuredBlocks(self):
        measuredBlockTimes = self.layoutBlocksInstance.getTopSpeedTimePerMeasuredBlock()
        measuredSensors = measuredBlockTimes.keys()
        processedSensors = self.processedMeasurementsForward.keys()

        # some measured sensors may be excluded from the processed data
        relevantSensors = [el for el in measuredSensors if el in processedSensors]

        speedTables = {}
        for sensor in relevantSensors:
            speedTables[sensor] = self._blockSpeedTableBuilder(sensor, measuredBlockTimes[sensor])

        # TODO: something better than averaging the speed tables
        # TODO: Also return trim values (see comments on SVD above)
        numTables = len(list(speedTables.keys()))
        finalTable = []
        # 28 steps
        for cv in range(len(speedTables[relevantSensors[0]])):
            val = 0
            for sensor in speedTables.keys():
                val += speedTables[sensor][cv] * 1.0 / numTables
            finalTable.append(int(round(val)))

        return finalTable
