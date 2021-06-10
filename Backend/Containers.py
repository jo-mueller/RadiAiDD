#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
This script contains all kinds of object definitions that are required
for RadiAIDD program to read DICOM data from the IBA Lynx device and support
the setup of the double scattering system
"""


from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QFileDialog as Qfile

import numpy as np
import pydicom as dicom
import traceback
import tifffile
import logging
import os 
from scipy import ndimage

from matplotlib.lines import Line2D
from matplotlib.patches import Circle
import matplotlib.patches as patches

#n2v
from n2v.models import N2V
# do not show warnings from tensorflow
os.environ['TF_CPP_MIN_LOG_LEVEL']='3'


class Signals(QObject):
    moving = pyqtSignal()


class DragPoint(QWidget):

    lock = None  # only one can be animated at a time

    def __init__(self, parent, x=0.1, y=0.1, size=7, transparent=False,
                 alpha=0.9, **kwargs):
        super().__init__()

        if "fc" in kwargs:
            fc = kwargs["fc"]
        else:
            fc = "blue"

        if "edgecolor" in kwargs:
            ec = kwargs["edgecolor"]
        else:
            ec = "white"

        if transparent:
            fc = "white"
            alpha = 0.3
            ec = "black"

        self.parent = parent
        self.point = patches.Circle((x, y), radius=size, alpha=alpha,
                                    fc=fc, ec=ec, zorder=10)
        self.x = x
        self.y = y
        self.canvas = parent.canvas
        self.canvas.axes.add_patch(self.point)
        self.canvas.draw()
        self.press = None
        self.background = None
        self.connect()
        self.is_visible = True

        self.Signal = Signals()

    def toggle(self):
        """Turn this point on and off"""
        if self.is_visible:
            self.point.set_visible(False)
        else:
            self.point.is_visible(True)

    def remove(self):
        'make this point invisible'
        self.point.set_visible(False)

    def connect(self):
        'connect to all the events we need'

        self.cidpress = self.point.figure.canvas.mpl_connect(
            'button_press_event', self.on_press)
        self.cidrelease = self.point.figure.canvas.mpl_connect(
            'button_release_event', self.on_release)
        self.cidmotion = self.point.figure.canvas.mpl_connect(
            'motion_notify_event', self.on_motion)

    def on_press(self, event):

        if event.inaxes != self.point.axes:
            return
        if DragPoint.lock is not None:
            return
        contains, attrd = self.point.contains(event)
        if not contains:
            return
        self.press = (self.point.center), event.xdata, event.ydata
        DragPoint.lock = self

        # draw everything but the selected rectangle and store the pixel buffer
        canvas = self.point.figure.canvas
        axes = self.point.axes
        self.point.set_animated(True)

        canvas.draw()
        self.background = canvas.copy_from_bbox(self.point.axes.bbox)

        # now redraw just the rectangle
        axes.draw_artist(self.point)

        # and blit just the redrawn area
        canvas.blit(axes.bbox)

    @pyqtSlot()
    def on_motion(self, event):

        if DragPoint.lock is not self:
            return
        if event.inaxes != self.point.axes:
            return
        self.point.center, xpress, ypress = self.press
        dx = event.xdata - xpress
        dy = event.ydata - ypress
        self.point.center = (self.point.center[0]+dx, self.point.center[1]+dy)

        canvas = self.point.figure.canvas
        axes = self.point.axes
        # restore the background region
        canvas.restore_region(self.background)

        # redraw just the current rectangle
        axes.draw_artist(self.point)

        self.x = self.point.center[0]
        self.y = self.point.center[1]

        # blit just the redrawn area
        canvas.blit(axes.bbox)

        # emit signal with coordinates of this point
        self.Signal.moving.emit()

    def on_release(self, event):
        'on release we reset the press data'

        if DragPoint.lock is not self:
            return

        self.press = None
        DragPoint.lock = None

        # turn off the rect animation property and reset the background
        self.point.set_animated(False)

        self.background = None

        # redraw the full figure
        self.point.figure.canvas.draw()

        self.x = self.point.center[0]
        self.y = self.point.center[1]

    def disconnect(self):
        'disconnect all the stored connection ids'

        self.point.figure.canvas.mpl_disconnect(self.cidpress)
        self.point.figure.canvas.mpl_disconnect(self.cidrelease)
        self.point.figure.canvas.mpl_disconnect(self.cidmotion)

    def setCoords(self, x, y):
        'update the coordinates from the outside'
        self.x = x
        self.y = y
        self.point.center = (x, y)
        self.point.figure.canvas.draw()

    def setSize(self, s):
        'change the radius of this drag point'
        self.point.set_radius(s)
        self.point.axes.draw_artist(self.point)
        self.parent.canvas.draw()


class RadiographyImage(object):
    """
    This class contains all necessary information and functionality
    to load, process and store radiography images.
    """

    def __init__(self, filename, array, pw):
        self.filename = filename
        self.array = np.flipud(array)
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
        self.PatientID = metadata.PatientID

        # Iteratively load all Points in metadata into dictionary
        Points = {}
        i = 0
        while i < len(metadata.ROIContourSequence):
            name = Point(metadata, i).Name
            Points[name] = Point(metadata, i)
            i += 1

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
                self.horizontalLine.set_data([self.x-self.size,
                                              self.x +self.size],
                                             [self.y, self.y])
                self.verticalLine.set_data([self.x, self.x],
                                           [self.y -self.size,
                                            self.y+self.size])
                if self.circle:
                    self.circularLine.center = (x, y)
                    canvas.axes.add_patch(self.circularLine)

    def wipe(self):
        " Removes crosshair from wherever"
        if self.visible:
            self.toggle()

        self.x = []
        self.y = []
        self.horizontalLine = []
        self.verticalLine = []
        if self.circle:
            self.circularLine = []
        self.visible = False


class OverlayImage(QObject):
    "Class that holds data to allow shifting for positioning"
    # Define Signals
#    moved = Signal(int, int)

    def __init__(self):
        QObject.__init__(self)

        # Allocate variables so they can be written before init method
        self.Plan = np.array(None)
        self.Treat = np.array(None)
        self.Spacing = np.array([None, None])

    def init(self):
        "Initializes all necessary variables for further calculations"
        self.Plan_shift = self.Plan
        self.Treat_shift = self.Treat

        self.Difference = np.subtract(self.Plan.astype(float),
                                      self.Treat.astype(float))

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


        # Calculate size of new matrix
        new_x = self.width + abs(self.x_shift)
        new_y = self.height + abs(self.y_shift)
        # ...and allocate this matrix
        self.Plan_shift = np.zeros((new_y, new_x))
        self.Treat_shift = np.zeros((new_y, new_x))

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

        # get new difference as floating point numbers
        self.Difference = np.subtract(self.Plan_shift.astype(float),
                                      self.Treat_shift.astype(float))

        return self.x_shift, self.y_shift

    def get_rgb(self, saturated=0.3):
        """
        Returns RGB matrix with shifted colors

        saturated: percentage of pixels that should be saturated (=1)
        """
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


class DisplayObject:
    def __init__(self, canvas, label, GrayControl=None, **kwargs):
        self.canvas = canvas
        self.Qlabel = label

        self.array = None
        self.overlay = None
        self.handle = None
        self.GC = None  # No graywindow control assigned by default

        self.GUI = self.getGUI()
        self.overlay = None  # storage for overlay image array
        self.has_overlay = False  # Flag that tells whether image has overlay
        self.overlay_active = False  # Flag that tells if overlay is active

    def load_Image(self, ImgType):
        """
        Rule: Image is loaded and fliped upside down so that the display
        option origin=lower will result in correct display.
        If the imported image has more than two dimensions (i.e. has an
        additional layer vontaining only the overlayed brain mask),
        then one additional layer is stored in here - only one!
        """
        fname, _ = Qfile.getOpenFileName(self.GUI, 'Open file',
                                         "", "(*.tif)")
        # If no file is chosen:
        if not fname:
            return 0

        data = tifffile.imread(fname)
        logging.info('Loading image and using Noise2Void ...')
        # if image is radiographic then eliminate extrem pixel values and apply a trained noise2void model
        if ImgType == 'RG':
            image_without_dead_pixel = self.eliminate_dead_pixel(data)
            
            data = self.apply_n2v_model(image_without_dead_pixel)
            
        
        data = self.normalize(data, 256.0)
        if len(data.shape) > 2:
            self.overlay = np.flipud(data[1, :, :]).astype(float)
            self.overlay[self.overlay == 0] = np.nan
            self.array = np.flipud(data[0, :, :])
            self.has_overlay = True
        else:
            self.array = np.flipud(data)

        # zero padding
        if self.has_overlay:
            self.array = self.zeropadding(self.array, 1032, 1012)
            self.overlay = self.zeropadding(self.overlay, 1032, 1012)
        else:
            self.array = self.zeropadding(self.array, 1032, 1012)

        self.handle = self.display(cmap='gray')
        self.Qlabel.setText(fname)

        logging.info('Successfully imported {:s}'.format(fname))
        self.GUI.WindowSelector.setEnabled(True)

    def normalize(self, data, N):
        return N*(data - np.min(data))/(np.max(data) - np.min(data))

    def zeropadding(self, array, width, height):
        'This function embedds the X-Ray image(s) within a zero-padded image'
        if array.shape[0] < width and array.shape[1] < height:
            new_array = np.zeros((height, width))
            x = int((width - array.shape[1])/2.0)
            y = int((height - array.shape[0])/2.0)
            new_array[y:y + array.shape[0], x:x + array.shape[1]] = array
            return new_array
        else:
            return array

    def display(self, clear=True, **kwargs):
        """
        Display function to paint array in self on canvas.
        By default removes previous image on this canvas.
        """
        if clear:
            self.canvas.axes.clear()
        handle = self.canvas.axes.imshow(self.array, origin='lower', **kwargs)
        self.handle = handle
        self.canvas.draw()
        self.is_active = True
        return handle

    def toggleOverlay(self):
        'Switches the overlay on and off, provided it exists'
        if not self.has_overlay:
            return 0

        if self.overlay_active:
            self.h_overlay.set_visible(False)
            self.canvas.draw()
            self.overlay_active = False
        else:
            self.h_overlay = self.canvas.axes.imshow(self.overlay,
                                                     cmap='Oranges',
                                                     origin='lower', alpha=0.5)
            self.canvas.draw()
            self.overlay_active = True

    def set_clim(self, cntr, rng):
        "Adjuts graywindow of self object if displayed"

        # CHeck if array has already been provided
        if self.handle is None:
            return 0

        self.handle.set_clim(cntr - rng/2, cntr + rng/2)
        self.canvas.draw()
        return 1

    def get_array(self):
        return self.array

    def get_fname(self):
        return self.Qlabel.getText()

    def getGUI(self):
        """Identify parent GUI"""

        widget = self.canvas
        hasParent = True
        while hasParent:
            widget = widget.parentWidget()
            if widget.parentWidget() is None:
                return widget

    def assign_graycontrol(self, HistCanv, SliderCenter, SliderRange,
                           TxtCtr, TxtRng):
        "Assigns a graywindow control instince for this display object"
        self.GC = GrayWindow2(HistCanv, SliderCenter, SliderRange,
                              TxtCtr, TxtRng, self)
        
    def func(self, x, s, u, a):
        """ represents a gaussian function for the fit of the histogram"""
        return a/np.sqrt(2*np.pi*s**2) * np.exp(- (x-u)**2/(2*s**2))   
    
    def eliminate_dead_pixel(self, train_image):
        """ function that searches for extrem pixel values in the image, recognises them and median filter them
        """
        
        # quantile(A, 0.02) gives a pixel value of the image which cuts the tail of the normal distribution.
        idx_map = (train_image < np.quantile(train_image, 0.02)) + (train_image > np.quantile(train_image, 0.98))   # map of true and false values
        
        # median filtered image 
        train_image_median = ndimage.median_filter(train_image, size=3)
 
        #replace certain values of og image with median values of median image 
        train_image[idx_map] = train_image_median[idx_map]
    
        return train_image
    
    
    
    def apply_n2v_model(self, image):
        # model name of our trained model
        model_name = 'n2v'
        # directory where model name can be found
        basedir = os.getcwd()  
        model = N2V(config=None, name=model_name, basedir=basedir)
        
        # We load the data we want to process - single images
        pred_train = model.predict(image, axes='YX', n_tiles=(2,1))

        return pred_train        


class GrayWindow2:
    def __init__(self, HistCanv, SliderCenter, SliderRange,
                 TxtCtr, TxtRng, owner):
        self.owner = owner
        self.SliderCenter = SliderCenter
        self.SliderRange = SliderRange

        self.TextCenter = TxtCtr
        self.TextRange = TxtRng
        self.histcanvas = HistCanv

        self.is_active = False
        self.histcolor = 'blue'
        self.is_filled = False

        # defaults for histogram
        self.clim = [0, 100]
        self.center = 0
        self.range = 0
        self.hist = [[0], [0]]
        self.barwidth = 1
        self.nbins = 150

    def fill(self):
        """
            Fills the graywindow control with actual values
        """

        if self.owner.array is None:
            return 0

        # Include only non-zero data in the subsequent calculation
        self.clim = self.owner.handle.get_clim()
        self.range = np.diff(self.clim)
        self.center = self.clim[0] + self.range/2.0

        # Histogram
        data = self.owner.array.flatten()
        data = data[data != 0.0]
        self.hist = np.histogram(data, self.nbins)
        self.barwidth = np.mean(np.diff(self.hist[1]))
        self.is_filled = True

    def activate(self):
        """
        Activates control of sliders over parent's graywindowing and the
        widgets that belong to this graywindow, such as a canvas for the
        histogram and textfields for the window values
        """

        # When activated, check for input data
        if not self.is_filled:
            self.fill()

        self.SliderCenter.setMinimum(self.clim[0])
        self.SliderCenter.setMaximum(self.clim[1])
        self.SliderRange.setMinimum(1)
        self.SliderRange.setMaximum(np.diff(self.clim))
        self.SliderCenter.setValue(self.center)
        self.SliderRange.setValue(self.range)

        self.TextCenter.setText("{:d}".format(int(self.center)))
        self.TextRange.setText("{:d}".format(int(self.range)))

        self.SliderCenter.valueChanged.connect(self.update)
        self.SliderRange.valueChanged.connect(self.update)
        self.is_active = True

        self.histcanvas.axes.clear()
        self.histcanvas.axes.bar(self.hist[1][:-1], height=self.hist[0],
                                 color=self.histcolor, width=self.barwidth)
        self.histcanvas.draw()
        self.update()

    def deactivate(self):
        try:
            self.SliderCenter.disconnect()
        except Exception:
            pass
        try:
            self.SliderRange.disconnect()
        except Exception:
            pass

    def update(self):
        "Function that is used to update the plot in respective canvas"

        self.center = self.SliderCenter.value()
        self.range = self.SliderRange.value()

        self.TextCenter.setText("{:d}".format(int(self.center)))
        self.TextRange.setText("{:d}".format(int(self.range)))

        self.owner.set_clim(self.center, self.range)
        self.histcanvas.axes.set_xlim([self.center - self.range/2,
                                       self.center + self.range/2])
        self.histcanvas.axes.set_ylim([0, np.max(self.hist[0])])
        self.histcanvas.draw()


class GrayWindow(QObject):
    """
    SliderCenter, SliderRange, TextCenter, TextRange, canvas, histcanvas, data
    Class that is used to adjust GrayWindow of Planar Scans
    (DEPRECATED)
    """

    def __init__(self, SliderCenter, SliderRange,
                 TextCenter, TextRange, canvas, histcanvas, data):

        QObject.__init__(self)
        self.SliderCenter = SliderCenter
        self.SliderRange = SliderRange

        self.TextCenter = TextCenter
        self.TextRange = TextRange
        self.canvas = canvas
        self.histcanvas = histcanvas

        self.cmin = np.min(data)
        self.cmax = np.max(data)

        center = (self.cmax-self.cmin)/2.0

        self.SliderCenter.setMinimum(self.cmin)
        self.SliderCenter.setMaximum(self.cmax)
        self.SliderRange.setMinimum(0)
        self.SliderRange.setMaximum(center*2)

        # set default greyvalues only when text labels display zero.
        # Else, the slider has probably already been used and it is desirable
        # to keep the previously set grey setting
        if self.SliderCenter.value() == 0 and self.SliderCenter.value() == 0:
            self.SliderCenter.setValue(350)
            self.SliderRange.setValue(200)
            self.TextCenter.setText(str(int(350)))
            self.TextRange.setText(str(int(200)))

        # plot histogram upon initialization
        data = data.flatten()
        data = data[data > 0]  # remove all zeroes from datavector
        self.histcanvas.axes.clear()
        self.histcanvas.axes.hist(data, 200)
        self.histcanvas.draw()
        self.maxfreq = np.max(np.histogram(data, 200)[0])

        self.SliderCenter.valueChanged.connect(self.update)
        self.SliderRange.valueChanged.connect(self.update)

        self.update()

    def update(self):
        "Function that is used to update the plot in respective canvas"
        print("update")
        Center = self.SliderCenter.value()
        Range = self.SliderRange.value()

        self.TextCenter.setText(str(int(Center)))
        self.TextRange.setText(str(int(Range)))

        axes = self.canvas.axes
        for im in axes.get_images():
            im.set_clim(Center - Range/2, Center + Range/2)
        self.canvas.draw()
        self.histcanvas.axes.set_xlim([Center - Range/2, Center + Range/2])
        self.histcanvas.axes.set_ylim([0, self.maxfreq])
        self.histcanvas.draw()
        
    def disconnect(self):
        try:
            self.SliderCenter.valueChanged.disconnect()
        except Exception:
            pass
        try:
            self.SliderCenter.valueChanged.disconnect()
        except Exception:
            pass


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
        checks = [self.IsoCenter, self.Target,
                  self.LandmarkRG, self.LandmarkXR,
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
        if all(checks):
            return True
        else:
            return False

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


    