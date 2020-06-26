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
        if self.x_shift >= 0 and self.y_shift >= 0:
            self.Plan_shift[:self.height, :self.width] = self.Plan
            self.Treat_shift[self.y_shift:, self.x_shift:] = self.Treat

        elif self.x_shift < 0 and self.y_shift >= 0:
            self.Plan_shift[:self.height, abs(self.x_shift):] = self.Plan
            self.Treat_shift[self.y_shift:, :self.width] = self.Treat

        elif self.x_shift >= 0 and self.y_shift < 0:
            self.Plan_shift[abs(self.y_shift):, :self.width] = self.Plan
            self.Treat_shift[:self.height, self.x_shift:] = self.Treat

        elif self.x_shift < 0 and self.y_shift < 0:
            self.Plan_shift[abs(self.y_shift):, abs(self.x_shift):] = self.Plan
            self.Treat_shift[:self.height, :self.width] = self.Treat

        # get new difference
        self.Difference = self.Plan_shift - self.Treat_shift

        return self.x_shift, self.y_shift

    def get_rgb(self):
        "Returns RGB matrix with shifted colors"
        P = self.Plan_shift
        T = self.Treat_shift

        RED = (P - np.min(P))/(np.max(P) - np.min(P))
        GREEN = (T - np.min(T))/(np.max(T) - np.min(T))
        BLUE = np.zeros(np.shape(RED))

        RGB = np.zeros((np.shape(RED)[0], np.shape(RED)[1], 3))
        RGB[:, :, 0] = RED
        RGB[:, :, 1] = GREEN
        RGB[:, :, 2] = BLUE

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
        self.Treat_shift = self.Treat

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



