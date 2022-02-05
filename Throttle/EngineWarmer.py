"""
This class "warms up" the engine by running it in forward and reverse
for a set number of minutes
"""

class EngineWarmer:
    def __init__(self, speedMatchInstance, throttleInstance):
        self.speedMatchInstance = speedMatchInstance
        self.throttle = throttleInstance

    def warmUp(self, minutes=2):
        t = self.throttle.getActiveJmriThrottle()
        p = self.throttle.getActiveJmriProgrammer()

        # stop, in case already moving
        t.speedSetting = 0.0
        self.speedMatchInstance.waitMsec(2000)
        t.speedSetting = 0.1 # "turns on" some types of sound decoders
        self.speedMatchInstance.waitMsec(1000)
        t.speedSetting = 0.0
        self.speedMatchInstance.waitMsec(1000)

        # forward
        self._whistle(2)
        t.setIsForward(True)
        t.speedSetting = 0.5
        self.speedMatchInstance.waitMsec(int(minutes * 60 * 1000 / 2))

        # stop
        self._whistle(1)
        t.speedSetting = 0.0
        self.speedMatchInstance.waitMsec(2000)

        # reverse
        self._whistle(3)
        t.setIsForward(False)
        t.speedSetting = 0.5
        self.speedMatchInstance.waitMsec(int(minutes * 60 * 1000 / 2))

        # stop
        self._whistle(1)
        t.speedSetting = 0.0
        self.speedMatchInstance.waitMsec(2000)

        return


    def _whistle(self, toots):
        t = self.throttle.getActiveJmriThrottle()
        for i in range(toots):
            t.setF2(True)
            self.speedMatchInstance.waitMsec(300)
            t.setF2(False)
            self.speedMatchInstance.waitMsec(300)
