# jmri_engine_speed_match

## Installation Notes
Place the `SpeedMatch-JMRI` folder inside your JMRI scripts directory. By default, on Windows, this is `C:\Users\%username$\JMRI\jython`. Note that the name of the folder - `SpeedMatch-JMRI` - is important.

## Block Detection Notes
This script monitors travel time through detection blocks to determine engine speed. It's designed to run on a railroad mainline (in a loop), where the length and grade of each block may be different. in `SpeedMatch.py`, the user needs to fill in `self.measuredBlocks` with at least one block that has a sensor name and corresponding measured length in inches - we need the length to calibrate to the desired number of scale miles per hour. The `self.ignoredSensors` list in this file is used if you have sensors that provide false detection information, which is not an uncommon occurance with some of the diode voltage drop detectors. Adding more than one measured sensor block is likely to increase your calibration accuracy. However, if the goal is merely to speed match multiple engines and the calibration to any particular top speed is less important, then one block is sufficient. Finally, make sure that your measured block has working - rather than ignored - detection blocks on both the entry and exit side (i.e. 3 continuous working blocks, with the middle one being the measured block).

## SMPH Setting Notes
The scale miles per hour (SMPH) setting on the GUI is the top speed at which a calibrated engine will run. In the interest of not running locomotives as their maximum physical speed during calibration, we stop taking more data once the desired SMPH setting has been recorded. If you're unsure of the maximum SMPH that you want, try using a higher value, check the "Save" checkbox, and run your calibration. To lower the value, check the "Load" checkbox and the script will pull your old measurements from disk, saving you another calibration run of the locomotive. If one tries the reverse - an initial run at slow SMPH and recalibration at high SMPH - then a full calibration run of the locomotive should be performed to collect more data.

## Running the Script
In JMRI, click Scripting, Run Script, and select SpeedMatch-JMRI/SpeedMatch.py.

Filename Suffix is optional and typically used when one has multiple units with the same DCC address - e.g. an ABBA set of F units. If the set is all on address 23, may want to have file suffixes A, B, C, and D for separate calibration on each locomotive.

On the author's home railroad, where the mainline is approximately an 80-foot loop of track, data collection for one locomotive can take 2-3 hours, depending on top SMPH speed requested.

## TODO: Unfinished tasks
- PDF describing method of operation
- Revisit interpolation function in `SpeedTableBuilder.py`, especially at slow speeds
- Integration with JMRI roster entries
- Unit testing
- Momentum CV normalization across different DCC decoder vendors

## Method of Operation
More details eventually coming in a PDF. In short, since there are no promises made about how throttle steps map to speed table settings, nor how speed table settings map to the actual locomotive speed, what we do is take a speed table CV and gradually increase it, measuring block travel times in the process. From here, we use the measured block to compute a speed table.

Not yet implemented: With the computed speed table, we can calculate theoretical measured distances for all of the unmeasured blocks. By averaging the measured distances for each block, one can improve speed table accuracy slightly. Finally, the forward and reverse direction of travel ideally would each have a speed table. However, the NMRA CV definitions only provide one table, with a forward and backward gain setting. Therefore, we need a rank-1 approximation to a rank-2 matrix of speed table values, which is typically accomplished through a SVD. See notes below.

## Least Squares and SVD Software Notes
This software was developed with JMRI version 4.26, which uses Jython 2.7 rather than Jython 3. Since Python / Jython 2 are EOL at the time of initial software development, I wanted to use the following libraries:
- numpy 1.13.3 (1.16 is the last version supporting Python 2, but PyNI only supports up to 1.13.3)
- scipy 1.2.3 (1.2 is the last version supporting Python 2)

However, since these are packages compiled for CPython, and since the JMRI uses Jython, we also use [JyNI](https://www.jyni.org/) as a compatibility layer. It turns out that the JyNI requires adding a jar file to the Java classpath. That means either using this script to add to the CLASSPATH environment variable - which means opening JMRI, adding to the classpath, then closing and restarting JMRI; or, that means permanently adding to the CLASSPATH, which needs root / admin rights; or, that means a manual setup step for the user. Since none of these solutions are great, and since PyNI is still alpha software that only has limited Numpy support, I concluded that working without libraries would be best. Drawbacks to the above include lack of easy-to-use least squares and SVD algorithms.

## Disclaimer: No Warranty
This software can make your model train locomotives run very fast, potentially flying off the track, bonking into scenery, or otherwise causing damage. This software is not intended for real train engines, or large-scale train engines that carry people. Use at your own risk. No warranties, express or implied.
