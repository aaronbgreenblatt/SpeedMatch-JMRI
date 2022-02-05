class Program:
    def __init__(self, speedMatchInstance, throttleInstance):
        self.speedMatchInstance = speedMatchInstance
        self.throttleInstance = throttleInstance

    """
    Programs a raw CV
    """
    def programCv(self, cvNumber, cvValue):
        self.throttleInstance.programmer.writeCV(str(int(cvNumber)), int(cvValue), None)
        self.speedMatchInstance.waitMsec(750)

    """
    Sets trim gain to 1.0 in both directions
    """
    def disableTrim(self):
        self.programCv(66, 0)
        self.programCv(95, 0)

    def enableSpeedTable(self):
        if self.throttleInstance.longaddress:
            self.programCv(29, 50)
        else:
            self.programCv(29, 18)

        if self.speedMatchInstance.data["Decoder"] == "Soundtraxx":
            self.programCv(25, 16)

    def disableManufacturerSpeedTables(self):
        self.programCv(25, 0)

    """
    writes 28 step table

    takes a 28 element list of ints as input
    """
    def programSpeedTable(self, speedTable28Steps):
        if not len(speedTable28Steps) == 28:
            raise Exception("Speed table must be 28 steps")

        for i in range(len(speedTable28Steps)):
            self.programCv(67+i, int(speedTable28Steps[i]))
