"""
Operates the GUI that asks the user for locomotive address, scale, etc. and
also handles GUI updates to reflect program status ("engine driving, ...").
Note that the constructor parameter methodToCallWhenStartClicked is a callback
to whatever method triggers the actual engine testing - it's called when the
user clicks the "Start" button in the GUI

params
methodToCallWhenClicked: must accept a GUI object so that we can call
                         GUI.getData - i.e. methodToCallWhenClicked(gui_obj)
"""

import java
import javax.swing
import jmri
from Utils import RedirectStdErr

class GUI:
        def __init__(self, methodToCallWhenStartClicked):
            self.dccaddress = None
            self.filenameSuffix = None
            self.scale = None
            self.cv3 = None
            self.cv4 = None
            self.maxSpeed = None
            self.dataNormalized = None
            self.methodToCallWhenStartClicked = methodToCallWhenStartClicked
            self.frame = None

        @RedirectStdErr
        def displayGui(self):
            # create a frame to hold the button, set up for nice layout
            f = javax.swing.JFrame("Speed Matching Table Input Panel")      # argument is the frames title
            f.setLocation(120,50)  # 120 units from left edge, 50 units down from top. 1200 is off the right edge!
            f.contentPane.setLayout(javax.swing.BoxLayout(f.contentPane, javax.swing.BoxLayout.Y_AXIS))

            # create the DCC text field
            self.dccaddress = javax.swing.JTextField(5) # sized to hold 5 characters, initially empty
            self.dccaddress.setText("3")

            # put the text field on a line preceded by a label
            dccAddressPanel = javax.swing.JPanel()
            dccAddressPanel.add(javax.swing.JLabel("               DCC Address"))
            dccAddressPanel.add(self.dccaddress)

            # filename suffix - e.g. for F unit set (A,B,C,D)
            self.filenameSuffix = javax.swing.JTextField(5) # sized to hold 5 characters, initially empty
            filenameSuffixPanel = javax.swing.JPanel()
            filenameSuffixPanel.add(javax.swing.JLabel("Filename Suffix (Optional)"))
            filenameSuffixPanel.add(self.filenameSuffix)

            # save cv speed measurements to disk
            self.saveMeasurementsToDisk = javax.swing.JCheckBox(text="Save CV Measurements to Disk", selected=True)
            self.loadMeasurementsFromDisk = javax.swing.JCheckBox(text="Load Measurements from Disk", selected=False)
            savePanel = javax.swing.JPanel()
            savePanel.add(self.saveMeasurementsToDisk)
            savePanel.add(self.loadMeasurementsFromDisk)

            # create the momentum value fields
            self.cv3 = javax.swing.JTextField(3)    # sized to hold 3 characters, initially empty
            self.cv4 = javax.swing.JTextField(3)    # sized to hold 3 characters, initially empty

            # put the text field on a line preceded by a label
            momentumPanel = javax.swing.JPanel()
            momentumPanel.add(javax.swing.JLabel("  cv3 "))
            momentumPanel.add(self.cv3)
            momentumPanel.add(javax.swing.JLabel("  cv4 "))
            momentumPanel.add(self.cv4)

            self.cv3.setText("5")
            self.cv4.setText("5")

            # create the start button
            self.startButton = javax.swing.JButton("Start")
            self.startButton.actionPerformed = self._whenMyButtonClicked

            self.status = javax.swing.JLabel("Enter DCC Address and press Start")

            self.scale = javax.swing.JComboBox()
            self.scale.addItem("HO Scale")
            self.scale.addItem("N Scale")
            self.scale.addItem("S Scale")
            self.scale.addItem("O Scale")

            self.maxSpeed = javax.swing.JTextField(3)
            self.maxSpeed.setText("60")

            maxSmphPanel = javax.swing.JPanel()
            maxSmphPanel.add(javax.swing.JLabel("Maximum Speed (smph)"))
            maxSmphPanel.add(self.maxSpeed)

            #decoderList = ["ESU", "Digitrax", "TCS", "NCE", "MRC", "QSI-BLI",
            #               "SoundtraxxDSD", "Lenz Gen 5",  "Atlas/Lenz XF",
            #               "Tsunami"]
            decoderList = ["Soundtraxx", "Other"]
            self.decoder = javax.swing.JComboBox(decoderList)

            startButtonPanel = javax.swing.JPanel()
            startButtonPanel.add(self.startButton)

            # Put contents in frame and display
            f.contentPane.add(dccAddressPanel)
            f.contentPane.add(filenameSuffixPanel)
            f.contentPane.add(savePanel)
            f.contentPane.add(self.scale)
            f.contentPane.add(self.decoder)
            f.contentPane.add(momentumPanel)
            f.contentPane.add(maxSmphPanel)
            f.contentPane.add(startButtonPanel)
            f.contentPane.add(self.status)
            f.pack()
            f.show()
            self.frame = f

            self.dataNormalized = False
            return

        @RedirectStdErr
        def _whenMyButtonClicked(self, event) :
            self.disableStartButton()
            self.methodToCallWhenStartClicked(self)


        @RedirectStdErr
        def _normalizeData(self):
            if self.dataNormalized == False:
                if self.dccaddress.text == '':
                    raise Exception("Invalid DCC Address")
                self.dccaddress = int(self.dccaddress.text)

                self.filenameSuffix = str(self.filenameSuffix.text)

                self.saveMeasurementsToDisk = self.saveMeasurementsToDisk.isSelected()
                self.loadMeasurementsFromDisk = self.loadMeasurementsFromDisk.isSelected()

                self.decoder = str(self.decoder.getSelectedItem())

                if self.cv3.text == '':
                    raise Exception("Invalid CV3")
                self.cv3 = int(self.cv3.text)

                if self.cv4.text == '':
                    raise Exception("Invalid CV4")
                self.cv4 = int(self.cv4.text)

                if self.maxSpeed.text == '':
                    raise Exception("Invalid Max Speed")
                self.maxSpeed = int(self.maxSpeed.text)

                if self.scale.getSelectedItem() == "O Scale":
                    self.scale = 48
                elif self.scale.getSelectedItem() == "S Scale":
                    self.scale = 64
                elif self.scale.getSelectedItem() == "HO Scale":
                    self.scale = 87.1
                elif self.scale.getSelectedItem() == "N Scale":
                    self.scale = 160
                else:
                    raise Exception("Invalid Scale")

                self.dataNormalized = True
            elif self.dataNormalized == True:
                return
            else:
                # dataNormalized is None
                raise Exception("GUI data collection failure")

        @RedirectStdErr
        def getData(self):
            self._normalizeData()
            return {"DCC Address" : self.dccaddress,
                    "Filename Suffix" : self.filenameSuffix,
                    "Save Measurements" : self.saveMeasurementsToDisk,
                    "Load Measurements" : self.loadMeasurementsFromDisk,
                    "Decoder" : self.decoder,
                    "Scale" : self.scale,
                    "CV3" : self.cv3,
                    "CV4" : self.cv4,
                    "Maximum Speed" : self.maxSpeed}

        @RedirectStdErr
        def updateStatus(self, text):
            self.status = text

        # TODO: Re-enabling the start button and clicking on
        # 'start' again doesn't actually read new values if you
        # update the fields. Closing the GUI at the end of an
        # engine calibration instead for now.
        @RedirectStdErr
        def enableStartButton(self):
            raise Exception("This method is broken. See TODO above.")
            self.startButton.enabled = True

        @RedirectStdErr
        def disableStartButton(self):
            self.startButton.enabled = False

        @RedirectStdErr
        def closeWindow(self):
            if self.frame:
                self.frame.dispose()
