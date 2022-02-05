"""
Runs throttle and programming operations for the JMRI.
The speedMatchInstance is needed because we need a subclass of
jmri.jmrit.automat.AbstractAutomaton that's currently running
the handle() method to get a thread that lets us do things with
the throttle. Therefore, operations in this class need to be
called from SpeedMatch.handle() - having a bunch of other calls
on the stack between SpeedMatch.handle() and methods in this class
works fine.
"""

import jmri
from Utils import RedirectStdErr
from Program import Program

class Throttle:
    def __init__(self, speedMatchInstance, dccaddress):
        self.speedMatchInstance = speedMatchInstance
        self.dccaddress = dccaddress
        self.longaddress = None
        self.throttle = None
        self.programmer = None
        # must be called here due to jmri constraints
        # see https://groups.io/g/jmriusers/topic/24732866?p=Created,,,20,2,0,0::recentpostdate%2Fsticky,,,20,2,80,24732866
        self._selectEngine()

    @RedirectStdErr
    def _selectEngine(self):
        dccnumber = int(self.dccaddress)
        if (dccnumber > 127) :
             self.longaddress = True
        else :
             self.longaddress = False
        self.throttle = self.speedMatchInstance.getThrottle(dccnumber, self.longaddress)
        if (self.throttle == None) :
             print("Couldn't assign throttle!")
        else :
            print("Selected DCC Address ", dccnumber)

        self.programmer = self.speedMatchInstance.addressedProgrammers.getAddressedProgrammer(self.longaddress, dccnumber)

        return

    @RedirectStdErr
    def getActiveJmriThrottle(self):
        if self.throttle:
            return self.throttle
        else:
            raise Exception("Error: No locomotive selected")

    @RedirectStdErr
    def getActiveJmriProgrammer(self):
        if self.programmer:
            return self.programmer
        else:
            raise Exception("Error: No locomotive selected")


    """
    Drives the train based on a CV in the speed table rather
    than based on throttle steps.

    Note that you may want to set forward and reverse trim
    to a scaling of 1.0 (usually 128) when using this method.

    params:
    forward: True for forward, False for Reverse
    speedTableStep: The CV we want to alter - from step 1 to step 28
    cvValue = speed of the locomotive, based on the CV value
    """
    @RedirectStdErr
    def driveCv(self, cvValue, forward=True, speedTableStep=14):
        p = Program(self.speedMatchInstance, self)

        if cvValue == 0:
            # if we're stopping
            self.getActiveJmriThrottle().speedSetting = 0.0
        else:
            # set steps around the target bececause decoders interpolate
            # these values and our throttle setting might not be exactly
            # on the dot to avoid interpolation
            for step in [speedTableStep-1, speedTableStep, speedTableStep+1]:
                if (step > 0) and (step <=28):
                    p.programCv(cvNumber = 66 + step, cvValue = cvValue)
            self.getActiveJmriThrottle().setIsForward(forward)
            self.getActiveJmriThrottle().speedSetting = speedTableStep * 1.0/28
        return
