import jmri
import os
import sys
import java #needed?
import javax.swing #needed?

# This package needs to be placed in the JMRI scripts directory
# set subdirectory as appropriate below
package_subdirectory = "SpeedMatch-JMRI"
package_path = jmri.util.FileUtil.getExternalFilename("scripts:" + package_subdirectory)

# add directory to the package search path as needed
if package_path not in sys.path:
    sys.path.insert(0, package_path)


from GUI import GUI
from Throttle import Throttle, EngineWarmer, Program
from LayoutBlocks import LayoutBlocks
from SpeedTableBuilder import SpeedTableBuilder
from Utils import RedirectStdErr


class SpeedMatch(jmri.jmrit.automat.AbstractAutomaton):
    def __init__(self):
        self.data = None
        self.gui = None
        self.measuredBlocks = {"Measured Block Sensors" : ["LS235", "LS221", "LS254"],
                               "Measured Block Lengths (Inches)" : [20.4375, 30.5, 13.0625]}
        self.ignoredSensors = ["LS253", "LS264"] # faulty sensors to ignore

        self._sensorSetup()
        return

    @RedirectStdErr
    def _sensorSetup(self):
        self.completeSensorList = list(range(1,512)) # we want to watch any block,
                                                     # but the JMRI API asks us to
                                                     # list the block names. So
                                                     # just list a lot of them here
        self.completeSensorList = ["LS" + str(el) for el in self.completeSensorList]
        self.monitoredSensors = [el for el in self.completeSensorList
                                 if not el in self.ignoredSensors ]
        self.jmriSensors = {}
        for sensor in self.monitoredSensors:
            self.jmriSensors[sensor] = sensors.provideSensor(sensor)

    @RedirectStdErr
    def main(self):
        def runTest(guiInstance):
            self.data = guiInstance.getData()
            # TODO move measured blocks to a config file or the GUI
            self.data = dict(self.data.items() + self.measuredBlocks.items())
            self.data["JMRI Sensors"] = self.jmriSensors
            self.data["JMRI Sensor Active Const"] = ACTIVE
            self.start() #calls self.handle() via JMRI

        self.gui = GUI(runTest)
        self.gui.displayGui()
        return

    """
    This method runs when the user clicks the 'start' button
    """
    @RedirectStdErr
    def handle(self):
        print(self.data)

        # get throttle
        self.addressedProgrammers = addressedProgrammers #TODO: Not very elegant
        t = Throttle(speedMatchInstance=self, dccaddress=self.data["DCC Address"])
        p = Program(speedMatchInstance=self, throttleInstance = t)
        # turn on layout power
        jmri.InstanceManager.getDefault(jmri.PowerManager).setPower(jmri.PowerManager.ON)

        # set momentum CVs to 1 for measurements
        p.programCv(cvNumber=3, cvValue=1)
        p.programCv(cvNumber=4, cvValue=1)
        p.disableTrim()
        p.disableManufacturerSpeedTables()

        # warm up engine
        ew = EngineWarmer(speedMatchInstance=self, throttleInstance=t)
        if not self.data["Load Measurements"]:
            ew.warmUp(minutes=5)

        # measure layout blocks
        p.enableSpeedTable()
        lb = LayoutBlocks(speedMatchInstance=self, throttleInstance=t, data=self.data)
        lb.computeMeasuredBlockTopSpeedTime()
        lb.measureBlockTimes()

        # Compute speed table
        stb = SpeedTableBuilder(layoutBlocksInstance = lb)
        stb.preprocessCvToBlockTimeDataTables()
        table28Steps = stb.buildSpeedTableForMeasuredBlocks()
        print("Computed Speed Table: ", table28Steps)

        # Program speed table and requested momentum cvs
        p.programSpeedTable(table28Steps)
        p.programCv(cvNumber=3, cvValue=self.data["CV3"])
        p.programCv(cvNumber=4, cvValue=self.data["CV4"])
        print("Table programming complete")

        # Turn off layout power
        jmri.InstanceManager.getDefault(jmri.PowerManager).setPower(jmri.PowerManager.OFF)



        print("Speed Match Script Done")
        self.gui.closeWindow()

        # handle() runs in a loop until false is returned
        return False


s = SpeedMatch()
s.main()
