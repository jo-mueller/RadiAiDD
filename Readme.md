Latest stable version of Positioning Interface.

Date: 20.04.2018
Author: Johannes Müller

1. How to run:

	*Go to folder with Positioning_AssistantMAIN.py (presumably the one you are at right now)
	*click into addressline
	*type "cmd" and hit Enter
	*in console, type "python Positioning_AssistantMAIN.py", the programm will then start

2. Necessary Input
	*.dcm Lynx image of Collimator for IsoCenter definition
	*.dcm Lynx image of Bed with Earpins in Transport Box
	*RS [...].dcm RT struct file that holds CT-based plan information ("structure set")
	*.dcm Planar X-Ray image (angle: 90degree) from Planning day
	*.dcm Planar X-Ray image (angle: 90degree) from Treatment day
	*A good spirit! :)

3. Bug handling
	*if unexpected behaviour occurrs: please report!
	*Coordinate addition was currently only tested without repositioning Scan!
	*Make sure that you load correct planar images; programm becomes buggy when files are loaded on top of old one
	    Better: Close and start again

4. Logfile
	A Logfile can be exported that saves all sorts of stuff. 
	The default location for the creation of the logfile is in the directory of the program itself.
