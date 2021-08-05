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
from PyQt5.QtWidgets import QToolBar
from PyQt5.QtWidgets import QLabel

import numpy as np
import traceback
import tifffile
import logging
from scipy import ndimage
import os

# from n2v.models import N2V
# # do not show warnings from tensorflow
# os.environ['TF_CPP_MIN_LOG_LEVEL']='3'

from matplotlib.lines import Line2D
from matplotlib.patches import Circle
import matplotlib.patches as patches

class Signals(QObject):
    moving = pyqtSignal()
    changing_clims = pyqtSignal([float, float])
    state_changed = pyqtSignal(bool)
    state_down = pyqtSignal()
    state_up = pyqtSignal()


class StateSign:
    def __init__(self, HostFrame, TextStates, **kwargs):
        """
        var QObj: text label object for status display
        var TextStates: array (len 2) with labels for display in treu/false state
        """

        self.loglvl = kwargs.get('loglvl', 'debug')

        # QFrame hosts the label for the state sign
        self.QFrame = HostFrame
        
        # find the Qlabel object in host box
        for obj in self.QFrame.children():
            if type(obj) ==  QLabel:
                self.QText = obj
        
        # write passed state to dictionary
        self.dict_states = dict()
        self.dict_states['off'] = TextStates[0]
        self.dict_states['on'] = TextStates[1]
        
        # define signal
        self.Signals = Signals()
        
        # init default state
        self.state = False
        self.flag_down()
        

    def flag_down(self):
        self.QText.setText(self.dict_states['off'])
        self.QFrame.setStyleSheet( "background-color: #DF362D;")
        self.state = False
        self.Signals.state_down.emit()
        
        if self.loglvl == 'info':
            logging.info('{:s}'.format(self.dict_states['off']))

    def flag_up(self):
        self.QText.setText(self.dict_states['on'])
        self.QFrame.setStyleSheet( "background-color: #18A558;")
        self.state = True
        self.Signals.state_up.emit()
        
        if self.loglvl == 'info':
            logging.info('{:s}'.format(self.dict_states['on']))
        

    def toggle(self):
        "changes the state from one to another"
        if self.state == True:
            self.flag_down()
        else:
            self.flag_up()
        self.Signals.state_changed.emit(self.state)
        logging.info('Status was changed to {:s}'.format(self.dict_states['on']))


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


# class RTstruct:
#     """Class that holds everything that is necessary
#     for the handling of RT structure sets in this application
#     """

#     def __init__(self):
#         self.filename = []
#         self.PatientID = []

#     def load(self, fullpath):
#         "Function to load all necessary info from RTstruct metadata"
#         metadata = dicom.read_file(fullpath)

#         self.filename = fullpath
#         self.PatientID = metadata.PatientID

#         # Iteratively load all Points in metadata into dictionary
#         Points = {}
#         i = 0
#         while i < len(metadata.ROIContourSequence):
#             name = Point(metadata, i).Name
#             Points[name] = Point(metadata, i)
#             i += 1

#         self.Earpin = Points.get('Earpin')
#         self.Target = Points.get('Target')

#         return metadata

#     def getshift(self):
#         " Calculate spatial shift between target and Earpin"
#         ShiftX = self.Target.coordinates[2] - self.Earpin.coordinates[2]
#         ShiftY = self.Target.coordinates[1] - self.Earpin.coordinates[1]
#         return ShiftX, ShiftY


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


class DisplayObject(QWidget):
    """
    Host class for display of images, array storage, etc.
    """
    def __init__(self, canvas, label, GrayControl=None, **kwargs):
        super().__init__()
        
        self.canvas = canvas
        self.Qlabel = label

        self.ImgType = None
        self.array = None
        self.overlay = None
        self.handle = None
        self.GC = None  # No graywindow control assigned by default
        self.GBWidget = None  # No Graybar assigned by default

        self.GUI = self.getGUI()
        self.overlay = None  # storage for overlay image array
        self.has_overlay = False  # Flag that tells whether image has overlay
        self.overlay_active = False  # Flag that tells if overlay is active
        
        self.CCenter = 0  # center for gray range
        self.CRange = 0  # range of displayed gray values
        self.n_bins = None  # n bins for graybar
        
        # flags
        self.is_moving = False
        self.has_graybar = False
        self.Signals = Signals()
        
    def flip(self):
        """
        If the image has an overlay, this function will flip foreground and overlay
        """
        
        if not self.has_overlay:
            return 0
        
        self.overlay, self.array = self.array, self.overlay
        self.display(cmap='gray')
        return 1
        
    def wipe(self):
        """
        Cleans image object and removes all references
        """
        
        # clear image
        self.canvas.axes.clear()
        self.canvas.draw()
        
        # destroy data handles
        self.ImgType = None
        self.array = None
        self.overlay = None
        self.handle = None
        
        # destroy connection to statesign after being called once
        if self.ImgType == 'XR':
            self.GUI.PlanImageState.state_down.disconnect(self.wipe)
        elif self.ImgType == 'RG':
            self.GUI.TreatImageState.state_down.discconnect(self.wipe)
        
        # destroy file reference
        if self.Qlabel is not None:
            self.Qlabel.setText('')
        
        if self.has_graybar:
            self.GBWidget.canvas.axes.clear()
            self.GBWidget.canvas.draw()
        

    def load_Image(self, ImgType='RG', **kwargs):
        """
        Rule: Image is loaded and fliped upside down so that the display
        option origin=lower will result in correct display.
        If the imported image has more than two dimensions (i.e. has an
        additional layer vontaining only the overlayed brain mask),
        then one additional layer is stored in here - only one!
        """
        
        self.ImgType = ImgType
        self.n_bins = kwargs.get('n_bins', 100)
        fname, _ = Qfile.getOpenFileName(self.GUI, 'Open file',
                                         "", "(*.tif)")
        # If no file is chosen:
        if not fname:
            return 0
        data = tifffile.imread(fname)
        data = self.normalize(data, 256.0)
        
        # If image has more than two layers (i.e. = 3D):
        if len(data.shape) > 2:
            self.overlay = np.flipud(data[1, :, :]).astype(float)
            self.overlay[self.overlay == 0] = np.nan
            self.array = np.flipud(data[0, :, :])
            self.has_overlay = True
        else:
            self.array = np.flipud(data)

        self.hist = np.histogram(self.array, self.n_bins)  # get hist of image
        self.handle = self.display(cmap='gray')
        self.Qlabel.setText(fname)

        logging.info('Successfully imported {:s}'.format(fname))
        
        # get initial gray-range
        clims = self.canvas.axes.images[0].get_clim()
        self.CCenter = np.mean(clims)
        self.CRange = np.diff(clims)
        
        if self.has_graybar:
            self.GBWidget.canvas.axes.clear()
            self.GBWidget.canvas.axes.set_facecolor("#323232")
            self.GBWidget.canvas.axes.set_yticks([])
            self.GBWidget.canvas.axes.set_xticks([])
            self.GBWidget.canvas.axes.bar(self.hist[1][1:], self.hist[0],
                                          width=np.diff(self.hist[1])[0])
            self.GBWidget.canvas.draw()
            
        # Prevent double connection when new image is loaded
        try:
            self.disconnect()
        except Exception:
            pass
        self.connect()
        
        # Send state to Workflow
        # This switches the respective workflow step's state and connects
        # the wipe function, which is called as soon a new image is loaded
        if ImgType == 'XR':
            self.GUI.PlanImageState.flag_up()
            self.GUI.PlanImageState.Signals.state_down.connect(self.wipe)
        elif ImgType == 'RG':
            self.GUI.TreatImageState.flag_up()
            self.GUI.TreatImageState.Signals.state_down.connect(self.wipe)
        
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
        
    def proc_on_import(self, image, **kwargs):
        """
        Does some preprocessing of the image upon import
        """
        
        # options
        do_zeropadding = kwargs.get('zeropadding', False)
        do_N2V_filtering = kwargs.get('N2V', False)
        do_normalization = kwargs.get('normalize', True)
        norm_range = kwargs.get('norm_range', 256)
        
        logging.info('Preprocessing input:')
        
        # Eliminate dead pixels and remove noise (only applicable for radiographic data)
        if self.ImgType == 'RG' and do_N2V_filtering:
            logging.info('\tN2V filtering')
            image = self.eliminate_dead_pixel(image)
            image = self.apply_n2v_model(image)        
        
        # normalize gray-range
        if do_normalization:
            logging.info('\tGrayrange normalization')
            image = self.normalize(image, norm_range)
            
        # zero padding
        if do_zeropadding:
            logging.info('\tZeropadding')
            self.array = self.zeropadding(self.array, 1032, 1012)
            if self.has_overlay:
                self.overlay = self.zeropadding(self.overlay, 1032, 1012)
                
        return image
    
    def disconnect(self):
        self.canvas.mpl_disconnect(self.cidpress)
        self.canvas.mpl_disconnect(self.cidrelease)
        self.canvas.mpl_disconnect(self.cidmotion)

    def connect(self):
        # Connect mouse movement buttons
        self.cidpress = self.canvas.mpl_connect(
            'button_press_event', self.on_press)
        self.cidrelease = self.canvas.mpl_connect(
            'button_release_event', self.on_release)
        self.cidmotion = self.canvas.mpl_connect(
            'motion_notify_event', self.on_motion)

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
        
        ax_onoff = kwargs.get('ax_onoff', 'off')
        cmap = kwargs.get('cmap', 'gray')
        
        if self.array is None:
            return 0
        
        if clear:
            self.canvas.axes.clear()
        self.canvas.axes.axis(ax_onoff)
        self.handle = self.canvas.axes.imshow(self.array, origin='lower', cmap=cmap)
        self.set_clim()
        self.canvas.draw()
        self.is_active = True
        
        return self.handle
    
    def set_clim(self, **kwargs):
        "Adjuts graywindow of self object if displayed"

        cntr = kwargs.get('cntr', self.CCenter)
        rng = kwargs.get('rng', self.CRange)

        # CHeck if array has already been provided
        if self.CCenter == 0 and self.CRange == 0:  
            return 0

        self.handle.set_clim(cntr - rng/2, cntr + rng/2)
        self.canvas.draw()
        
        return 1

    def on_press(self, event):
        """
        Handles response of canvas to click of middle mouse button
        """
        
        # 1 = left click, 2 = middle click, 3 = right click
        if event.button == 2:
            self.press = event.xdata, event.ydata
            self.is_moving = True            
            
    def on_motion(self, event):
        """
        When middle-clicked mouse is moved
        """
        if self.is_moving:
            try:  # catch error that occurs when mouse goes outside plot
                xpress, ypress = self.press
                dx = event.xdata - xpress
                dy = event.ydata - ypress
                
                cntr = self.CCenter + dx * (50/self.array.shape[0])
                rng = self.CRange + dy * (50/self.array.shape[1])
                
                if self.CRange < 0: 
                    self.CRange = 1
                    
                if self.CCenter < 0:
                    self.CCenter = 0
                    
                if self.CCenter > 256:
                    self.CCenter = 256
    
                # update colorlimits
                self.set_clim(cntr=cntr, rng=rng)
                self.Signals.changing_clims.emit(cntr, rng)
                if self.has_graybar:
                    self.update_graybar(cntr=cntr, rng=rng)
            except Exception:
                pass
            
    def on_release(self, event):
        """
        When middle-clicked mouse is release
        """
        
        if self.is_moving:
            try:
                xpress, ypress = self.press
                dx = event.xdata - xpress
                dy = event.ydata - ypress
                
                self.CCenter += dx * (50/self.array.shape[0])
                self.CRange += dy * (50/self.array.shape[1])
                
            except Exception:
                pass
            self.is_moving = False

    def toggleOverlay(self):
        'Switches the overlay on and off, provided it exists'
        if self.array is None:
            return 0
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
        
    def assign_graybar(self, GBwidget):
        self.GBWidget = GBwidget
        self.GBWidget.canvas.axes.axis('off')
        self.GBWidget.findChild(QToolBar).setVisible(False)
        self.GBWidget.canvas.axes.figure.tight_layout()
        self.GBWidget.canvas.draw()
        
        self.has_graybar = True
    
    def update_graybar(self, **kwargs):
        cntr = kwargs.get('cntr', self.CCenter)  # adjust graybar center
        rng = kwargs.get('rng', self.CRange)  # and range
        
        self.GBWidget.canvas.axes.set_xlim([cntr - rng/2, cntr + rng/2])
        # self.GBWidget.canvas.axes.figure.tight_layout()
        self.GBWidget.canvas.draw()




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
