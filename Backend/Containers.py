 #! /usr/bin/python
# -*- coding: utf-8 -*-
""" Program to read DICOM data from the IBA Lynx device and support the

    setup of the double scattering system"""


try:
    from PyQt4.QtCore import QObject
    pyqt_version = 4
except:
    from PyQt5.QtCore import QObject
    pyqt_version = 5


import os
import numpy as np
import pydicom as dicom
import scipy.ndimage.filters as filters
import traceback
import tifffile
import logging

from matplotlib.lines import Line2D
from matplotlib.patches import Circle


class RadiographyImage(object):
    """
    This class contains all necessary information and functionality
    to load, process and store radiography images.
    """

    def __init__(self, filename, array, pw):
        self.filename = filename
        self.array = array
        self.pw = pw

# class Lynx(object):
#     """Central class representing the measurement from the Lynx device"""
#     def __init__(self):

#         self.protonEnergy = 0
#         self.measDepth = 0
#         self.measMaterial = ""
#         self.comment = ""
#         self.fileOK = False
#         self.dataOK = False
#         self.MUcorr = False
#         self.data =  []
#         self.dcmDat = None
#         self.filename = None

#         self.xrange = [-np.inf,  np.inf]
#         self.yrange = [-np.inf, np.inf]


#     def load(self, filename):
#         """ Import function to actually read the dicom/png file,
#             uses the filename, which was provided during initialization of the
#             Lynx object.
#             Requires a proper installed pydicom package.
#             If you are using Python3, you might be interested in the module 2to3
#             to convert pydicom for Pythton 2.7 to Python3
#         """
#         self.filename = os.path.expanduser(filename)                 # get rid of '~' in filename
#         self.path = os.path.dirname(self.filename)                   # path to data
#         self.filenameBare = os.path.splitext(self.filename)[0]       # filename without suffix

#         if not(os.access(self.filename, os.R_OK)):
#             print ("ERR: Could not access {0:s} for reading! Check filename.".format(filename))
#             return
#         else:
#             self.fileOK = True

#         if os.path.splitext(filename)[1] == ".dcm":
#             print ("INFO: {0:s} seems to be a dicom file.".format(os.path.basename(filename)))
#             print ("INFO: Trying to read...", end = "")
#             if not self.fileOK:
#                 print ("ERR: Object not initialized (no access to file {0:s}".format(self.filename))
#                 return

#             self.dcmDat = dicom.read_file(self.filename)
#             print('Done.')

#             self.xsc = float(self.dcmDat.RTImagePosition[0]) + np.arange(0, self.dcmDat.Rows)*float(self.dcmDat.PixelSpacing[0])
#             self.ysc = float(self.dcmDat.RTImagePosition[1]) + np.arange(0, self.dcmDat.Columns)*float(self.dcmDat.PixelSpacing[1])

#             data = self.dcmDat.pixel_array
#             data = data.astype("float")

#             # This is the working setting!!!
#             #data = np.flipud(np.fliplr(data))

#             #This not necessarily
#             data = np.fliplr(data)

#             self.data = data
#             print ("INFO: Importet a matrix of {0:d}x{1:d} from {2:s}".format(self.dcmDat.Rows,self.dcmDat.Columns,  self.filename  ))

# #        self.metaData_fromFilename()
#         self.dataOK = True


#     def set_xrange(self,low, high):
#         """ Set the area of interest, only rectangular ROIs are supported,
#             provide low and high x value
#         """

#         if low > high:  low, high = high, low   # switch variables if provided in the wrong order
#         self.xrange[0] = low
#         self.xrange[1] = high

#     def set_yrange(self,low, high):
#         """ Set the area of interest, only rectangular ROIs are supported,
#             provide low and high y value
#         """

#         if low > high:  low, high = high, low   # switch variables if provided in the wrong order
#         self.yrange[0] = low
#         self.yrange[1] = high


#     def autodetectRectField(self, threshold = 0.9):
#         print ("INFO: Autodetecting rectangular field. ", end = "")

#         mask = self.data
#         x = np.zeros(2)
#         y = np.zeros(2)

#         "Sum along x- and y-axis"
#         threshold = 0.5
#         doseOfX = np.sum(mask, axis = 0)
#         doseOfY = np.sum(mask, axis = 1)

#         x[0] = np.min(np.where(doseOfX >= threshold* np.max(doseOfX)))
#         x[1] = np.max(np.where(doseOfX >= threshold* np.max(doseOfX)))
#         y[0] = np.min(np.where(doseOfY >= threshold* np.max(doseOfY)))
#         y[1] = np.max(np.where(doseOfY >= threshold* np.max(doseOfY)))
#         y[1] = y[1]

#         print ("Found x = [" +str(x[0])+ "," +str(x[1])+
#                            "] and y = [" +str(y[0])+ "," +str(y[1])+ "]" )
#         return x, y


#     def crop(self, x, y):
#         """ Crops the data according to given x and y. If no boundaries are given,
#         full width/height is assumed to be correct"""

#         data = self.data[int(y[0]) : int(y[1]), int(x[0]) : int(x[1])]
#         self.data = data
#         return data

#     def preprocess(self):
#         print("Enhancing image by normalization, median-blurring and histogram-equalization...")
#         data = self.data- np.min(self.data)
#         data = 255.0*data/np.max(data)
#         median = filters.median_filter(data.astype('uint8'),7)
#         equ = histogram_equalize(median)
#         return equ

#     def grey2MU(self, MU):
#         print("Correcting image for MU")
#         self.data = self.data/MU
#         self.MUcorr = True

#     def convert2WEPL(self, p):
#         if len(p)==3:
#             self.data = p[0]*np.power(self.data,2) + p[1]*self.data + p[2]
#         if len(p)==2:
#             self.data = p[0]*self.data + p[1]

#     def normalize(self):
#         """ takes data from lynx and normalizes to values between 0 and 255."""
#         self.data = self.data- np.min(self.data)
#         self.data = 255.0*self.data/np.max(self.data)
#         return self.data

#     def invert(self):
#         """ takes the image data and inverts scale"""
#         self.data = self.data-np.max(self.data)
#         self.data = np.multiply(self.data, -1)
#         return self.data

class RTstruct:
    """Class that holds everything that is necessary
    for the handling of RT structure sets in this application
    """
    def __init__(self):
        self.filename = []
        self.PatientID = []

    def load(self, fullpath):
        "Function to load all necessary info from RTstruct metadata"
        metadata = dicom.read_file(fullpath)

        self.filename = fullpath
        self.PatientID      = metadata.PatientID

        # Iteratively load all Points in metadata into dictionary
        Points = {}
        i=0
        while i < len(metadata.ROIContourSequence):
            name = Point(metadata, i).Name
            Points[name] = Point(metadata, i)
            i+=1

        self.Earpin = Points.get('Earpin')
        self.Target = Points.get('Target')

        return metadata

    def getshift(self):
        " Calculate spatial shift between target and Earpin"
        ShiftX = self.Target.coordinates[2] - self.Earpin.coordinates[2]
        ShiftY = self.Target.coordinates[1] - self.Earpin.coordinates[1]
        return ShiftX, ShiftY


class Point:
    """Class that holds relevant data from DICOM RT Struct about landmarks"""
    def __init__(self, metadata, index):
        #write basic point properties
        self.metadata = metadata
        self.Name = self.metadata.RTROIObservationsSequence[index].ROIObservationLabel #Name of point (e.g. target or Iso)
        self.Number = self.metadata.RTROIObservationsSequence[index].ReferencedROINumber #Internal number of point

        #Store coordinates
        self.coordinates = []
        for i in range(len(metadata.ROIContourSequence[index].ContourSequence[0].ContourData)):
            self.coordinates.append(float(metadata.ROIContourSequence[index].ContourSequence[0].ContourData[i]))

        #Check if index leads to same ROI when different DICOM fields are accessed
        if self.metadata.RTROIObservationsSequence[index].ReferencedROINumber != self.metadata.ROIContourSequence[index].ReferencedROINumber:
            print('Error: Internal ROI numbers from respective field do not match!!!')
            self.coordinates = []


class Crosshair:
    """Class that corms a crosshair of given color
    and size on a given canvas"""
    
    def __init__(self):
        self.canvas = []
        self.size = []
        self.color = []
        self.zorder = []
        self.x = []
        self.y = []
        self.visible= False

    def setup(self, canvas, size, x, y, text='', zorder=2, color='blue',
              circle=False):

        # get input and save to internal namespace
        self.canvas = canvas
        self.size = size
        self.color = color
        self.zorder = zorder
        self.x = x
        self.y = y
        self.visible = False
        self.circle = circle # should a circle be drawn around crosshair?
        self.text = text

        # create lines
        self.horizontalLine = Line2D([ self.x - self.size, self.x + self.size],
                                     [ self.y, self.y],
                                     linestyle='-', alpha=0.5, linewidth=1.5,
                                     color=color, zorder=zorder)
        self.verticalLine = Line2D([self.x, self.x],
                                   [self.y - self.size, self.y + self.size],
                                   linestyle='-', alpha=0.5, linewidth=1.5,
                                   color=color, zorder=zorder)

        if self.circle:
            self.circularLine = Circle((self.x,self.y), self.size, fill=False,
                                       linestyle='-', alpha=0.5,
                                       linewidth=1.5, zorder=zorder,
                                       color=color)

    def toggle(self):
        "makes cross (in)visible, depending on previous state"
        try:
            # if crosshair is invisible
            if not self.visible:
                self.canvas.axes.add_line(self.horizontalLine)
                self.canvas.axes.add_line(self.verticalLine)
                if self.circle: self.canvas.axes.add_patch(self.circularLine)
                self.annotation = self.canvas.axes.text(self.x, self.y, self.text,
                                                        color=self.color,
                                                        zorder=self.zorder,
                                                        fontsize=10)
                self.canvas.draw()
                self.visible = True

            # If crosshair is currently visible
            else:
                self.horizontalLine.remove()
                self.verticalLine.remove()
                self.annotation.remove()
                if self.circle: self.circularLine.remove()
                self.canvas.draw()
                self.visible = False
        except Exception:
            print(traceback.print_exc())

    def move(self, x, y):
        " moves crosshair to new location"
        self.x += x
        self.y += y

        for canvas in self.canvases:

            if self.visible:
                self.horizontalLine.set_data([self.x-self.size, self.x +self.size], [self.y, self.y])
                self.verticalLine.set_data(  [self.x, self.x], [self.y -self.size, self.y+self.size])
                if self.circle:
                    self.circularLine.center = (x,y)
                    canvas.axes.add_patch(self.circularLine)

    def wipe(self):
        " Removes crosshair from wherever"
        if self.visible: 
            self.toggle()

        self.x = []
        self.y = []
        self.horizontalLine = []
        self.verticalLine   = []
        if self.circle: 
            self.circularLine = []
        self.visible = False









class OverlayImage(QObject):
    "Class that holds data to allow shifting for positioning"
    #Define Signals
#    moved = Signal(int, int)

    def __init__(self):
        QObject.__init__(self)

        # Allocate variables so they can be written before init method
        self.Plan = np.array(None)
        self.Treat= np.array(None)

        self.Spacing = np.array([None, None])


    def init(self):
        "Initializes all necessary variables for further calculations"
        self.Plan_shift = self.Plan
        self.Treat_shift = self.Treat

        self.Difference = np.subtract( self.Plan, self.Treat)

        self.width = np.shape(self.Plan)[1]
        self.height = np.shape(self.Plan)[0]

        self.x_shift = 0
        self.y_shift = 0
    def move(self, direction):
        "function that returns new imagedata with moved coords"

        y = direction[0]
        x = direction[1]

        self.x_shift += x
        self.y_shift += y


        #Calculate size of new matrix
        new_x = self.width + abs(self.x_shift)
        new_y = self.height + abs(self.y_shift)
        #...and allocate this matrix
        self.Plan_shift   = np.zeros((new_y, new_x))
        self.Treat_shift  = np.zeros((new_y, new_x))

        # depending on which direction is moved:
#        if self.x_shift >= 0   and self.y_shift >= 0:
#            self.Treat_shift[ :self.height, :self.width] = self.Treat
#            self.Plan_shift[self.y_shift:,self.x_shift:] = self.Plan
#
#        elif self.x_shift < 0  and self.y_shift >= 0:
#            self.Treat_shift[:self.height, abs(self.x_shift):] = self.Treat
#            self.Plan_shift[self.y_shift:, :self.width] = self.Plan
#
#        elif self.x_shift >= 0 and self.y_shift < 0:
#            self.Treat_shift[abs(self.y_shift):, :self.width] = self.Treat
#            self.Plan_shift[:self.height, self.x_shift:] = self.Plan
#
#        elif self.x_shift < 0  and self.y_shift < 0:
#            self.Treat_shift[abs(self.y_shift):, abs(self.x_shift):] = self.Treat
#            self.Plan_shift[:self.height, :self.width]   = self.Plan
        # depending on which direction is moved:
        if self.x_shift >= 0   and self.y_shift >= 0:
            self.Plan_shift[ :self.height, :self.width] = self.Plan
            self.Treat_shift[self.y_shift:,self.x_shift:] = self.Treat

        elif self.x_shift < 0  and self.y_shift >= 0:
            self.Plan_shift[:self.height, abs(self.x_shift):] = self.Plan
            self.Treat_shift[self.y_shift:, :self.width] = self.Treat

        elif self.x_shift >= 0 and self.y_shift < 0:
            self.Plan_shift[abs(self.y_shift):, :self.width] = self.Plan
            self.Treat_shift[:self.height, self.x_shift:] = self.Treat

        elif self.x_shift < 0  and self.y_shift < 0:
            self.Plan_shift[abs(self.y_shift):, abs(self.x_shift):] = self.Plan
            self.Treat_shift[:self.height, :self.width]   = self.Treat

        # get new difference
        self.Difference = self.Plan_shift - self.Treat_shift

        return self.x_shift, self.y_shift

    def get_rgb(self):
        "Returns RGB matrix with shifted colors"
        RED = self.Plan_shift
        GREEN = self.Treat_shift
        BLUE = np.zeros(np.shape(RED))

        RGB = np.zeros((np.shape(RED)[0], np.shape(RED)[1], 3))
        RGB[:,:,0] = RED
        RGB[:,:,1] = GREEN
        RGB[:,:,2] = BLUE

        return RGB

    def get_plan(self):
        "returns shifted data in separate matrices"
        return self.Plan_shift

    def get_treat(self):
        "returns shifted data in separate matrices"
        return self.Treat_shift

    def get_diff(self):
        "returns difference data"
        return self.Difference

    def reset(self):
        "Resets movement from previous commands"
        self.Plan_shift = self.Plan
        self.Treat_shift= self.Treat

        self.x_shift = 0
        self.y_shift = 0

class GrayWindow(QObject):
    "Class that is used to adjust GrayWindow of Planar Scans"
    def __init__(self, SliderCenter, SliderRange,
                 TextCenter, TextRange, canvas, histcanvas, data):

        QObject.__init__(self)
        self.SliderCenter = SliderCenter
        self.SliderRange  = SliderRange

        self.TextCenter   = TextCenter
        self.TextRange    = TextRange
        self.canvas       = canvas
        self.histcanvas   = histcanvas
        self.cmin = np.min(data)
        self.cmax = np.max(data)

        center = (self.cmax-self.cmin)/2.0

        self.SliderCenter.setMinimum(self.cmin)
        self.SliderCenter.setMaximum(self.cmax)
        self.SliderRange.setMinimum(0)
        self.SliderRange.setMaximum(center*2)

        self.SliderCenter.valueChanged.connect(self.update)
        self.SliderRange.valueChanged.connect(self.update)

        self.SliderCenter.setValue(350)
        self.SliderRange.setValue(200)
        self.TextCenter.setText(str(int(350)))
        self.TextRange.setText(str(int(200)))
        self.update()

    def update(self):
        "Function that is used to update the plot in respective canvas"
        Center = self.SliderCenter.value()
        Range = self.SliderRange.value()

        self.TextCenter.setText(str(int(Center)))
        self.TextRange.setText(str(int(Range)))

        axes = self.canvas.axes
        for im in axes.get_images():
            im.set_clim(Center - Range/2, Center + Range/2)
        self.canvas.draw()
        self.histcanvas.axes.set_xlim([Center - Range/2, Center + Range/2])
        self.histcanvas.draw()


class Check:
    "Class to check prep status of experiment"
    def __init__(self):
        self.IsoCenter = False
        self.Target = False
        self.LandmarkRG = False
        self.LandmarkXR = False
        self.Planar_scan_Plan = False
        self.Planar_scan_Treat = False
        self.Repositioning = False

    def ready(self):
        "Checks all flags and returns true if all flags are up"
        checks = [self.IsoCenter, self.Target, self.LandmarkRG, self.LandmarkXR,
                  self.Planar_scan_Plan, self.Planar_scan_Treat,
                  self.Repositioning]

#        if not checks[0]: print('IsoCenter: Not set|'),
#        else: print('IsoCenter: Set|'),
#
#        if not checks[1]: print('Target: Not set|'),
#        else: print('Target: Set|'),
#
#        if not checks[2]: print('RG Landmarks: Not set|'),
#        else: print('RG Landmarks: Set|'),
#
#        if not checks[3]: print('X-Ray Landmarks: Not set.')
#        else: print('X-Ray Landmarks: Set.')

        # If any check fails, return False
        if all(checks): return True
        else:           return False




    def serialwrite(self, command):
        """Function that sends any given command to specified serial port.
            Returns decoded signal from the COM port
            - command: Serial command that is sent to COM-port
        """

        # properly format command line
        command = "00" + command + "\r\n"
        request = (command.format(0)).encode(encoding="ASCII")

        # Send request
        self.SerialCon.write(request)
        print('Sent command: ' + request.decode())

        # Read answer
        asw = (self.SerialCon.read(1024)).decode()

        return asw



