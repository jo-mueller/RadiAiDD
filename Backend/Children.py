# -*- coding: utf-8 -*-

try:
    from PyQt4 import QtGui
    from PyQt4.QtGui import QMessageBox as QMessage
    from PyQt4.QtGui import QFileDialog as Qfile
    import PyQt4.QtCore as QtCore
    from PyQt4.QtGui import QMainWindow as QMain
    from PyQt4.QtGui import QToolBar
    pyqt_version = 4
except:
    from PyQt5 import QtGui
    from PyQt5.QtWidgets import QMessageBox as QMessage
    from PyQt5.QtWidgets import QFileDialog as Qfile
    from PyQt5.QtWidgets import QMainWindow as QMain
    from PyQt5.QtWidgets import QToolBar
    from PyQt5.QtWidgets import QApplication
    import PyQt5.QtCore as QtCore
    pyqt_version = 5



import matplotlib.patches as patches
from matplotlib import backend_tools
import numpy as np
import traceback, os, ntpath, logging
import scipy.ndimage.filters as filters
import scipy.optimize as opt

if pyqt_version == 4:
    import IsoCenter as IsoCenter
    import Landmark  as Landmark
    import Target    as Target
    
elif pyqt_version == 5:
    import Backend.IsoCenter5 as IsoCenter
    import Backend.Landmark5  as Landmark
    import Backend.Target5    as Target
    
from Backend.Containers   import Lynx
from Backend.Containers   import histogram_equalize
        

import matplotlib.pyplot as plt


folder = os.path.normpath('P:\Projects\Protonenexperimente\Scripts\Positioning_GUI')

''''''''''''''''''''''''
"""ISOCENTER -Dialogue"""
''''''''''''''''''''''''
        
class IsoCenter_Child(QMain, IsoCenter.Ui_IsoCenter):
    "Class that contains subroutines to define isocenter from Lynx image"
    def __init__(self, parent, owner):
        super(IsoCenter_Child, self).__init__(parent)
        
        self.Owner  = owner
        self.setupUi(self)
        
        self.parent = parent
        self.canvas = self.Display_IsoCenter.canvas
        self.toolbar = self.canvas.toolbar
        
        #Connect buttons
        self.Button_LoadSpot.clicked.connect(self.load)    
        self.Button_detectIsoCenter.clicked.connect(self.define_ROI)
        self.Button_SetIsoCenter.clicked.connect(self.LockIsoCenter)     
        self.Button_Done.clicked.connect(self.Done)
        
        # Flags and Containers
        self.Image = Lynx()        
        self.press = None
        self.rects = []
        self.target_markers = []
        
        #Flags
        self.FieldSize_flag = False
        self.IsoCenter_flag = False
        
    def load(self):
        "load radiography image of beam IsoCenter"
        if pyqt_version == 5:
            fname = Qfile.getOpenFileName(self, 'Open file', folder,"Dicom files (*.dcm)")[0]
        else:
            fname = str(Qfile.getOpenFileName(self, 'Open file', folder,"Dicom files (*.dcm)"))
        
        # get filename from full path and display     
        _, filename = ntpath.split(fname)
        self.Text_Filename.setText(filename)
        
        try:
            # Load Radiography and display
            self.Image.load(fname)
            self.canvas.axes.imshow(self.Image.data, cmap = 'gray', 
                                    zorder=1, origin = 'lower')
            self.canvas.draw()
            
            logging.info('{:s} imported as Isocenter Radiography'.format(filename))
            
            self.IsoCenter_flag = False
        except:
            pass

        
    def define_ROI(self):
        "Specify a ROI within which the bed contours can be found"

        print(self.Button_detectIsoCenter.isChecked())

        # If button is pressed and user wants to un-press it:
        if self.Button_detectIsoCenter.isChecked():
            self.Button_detectIsoCenter.setChecked(False)
            self.Button_detectIsoCenter.setStyleSheet('border: 2px solid #343434;')
            return 0
        
        self.Button_detectIsoCenter.setChecked(True)
        self.Button_detectIsoCenter.setStyleSheet('border: 2px solid QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ffa02f, stop: 1 #d7801a);')
                                                                               
        # If rects or other markers are visible, remove        
        for rect in self.rects:
            rect.remove()
        self.rects = []        
        for marker in self.target_markers:
            marker.remove()
        self.target_markers = []

        self.canvas.draw()  
        
        self.connect()        
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()
        self.canvas.draw()
        
        
    def connect(self):
        'connect to all the events needed'
        self.cidpress = self.canvas.mpl_connect(
            'button_press_event', self.on_press)
        self.cidrelease = self.canvas.mpl_connect(
            'button_release_event', self.on_release)
        self.cidmotion = self.canvas.mpl_connect(
            'motion_notify_event', self.on_motion)
            
    def on_press(self, event):
        'on button press we will see if the mouse is over us and store some data'
        #Existiert schon ein Rechteck? Falls nein
        if not self.rects: # Neues Rechteck malen
            self.rect = self.canvas.axes.add_patch( patches.Rectangle((event.xdata,event.ydata), 0, 0 , fill = False))
            self.rects.append(self.rect)
        else: #Altes Rechteck/Konturlinien weg und neu malen
            for rect in self.rects: 
                rect.remove()
                self.rects = []
            
            self.rect = self.canvas.axes.add_patch( patches.Rectangle((event.xdata,event.ydata), 0, 0 , fill = False))
            self.rects.append(self.rect)
        
        # Ursprungskoordinaten in self.press hinterlegen. self.press enthält nur werte wenn geklickt wurde!                        
        self.press = self.rect.xy
        self.canvas.draw()
        
    def on_motion(self, event):
        'on motion move the boundaries of the rect to cursor location'
        #  Is the button pushed or have values been stored in self.press, respectively?
        if self.press is None: return
        x0, y0 = self.press
        
        if event.xdata < x0:
            self.rect.set_x(event.xdata)
        if event.ydata < y0:
            self.rect.set_y(event.ydata)
            
        self.rect.set_width(abs(event.xdata - x0))
        self.rect.set_height(abs(event.xdata - x0)) #set to square for fitting purpose
        self.canvas.draw()

    def on_release(self, event):
        'on release we reset the press data and disconnect'
        self.press = None
        self.canvas.draw()
        
        self.canvas.mpl_disconnect(self.cidpress)
        self.canvas.mpl_disconnect(self.cidrelease)
        self.canvas.mpl_disconnect(self.cidmotion)
        
        self.spotDetect()
        self.Button_detectIsoCenter.setChecked(False)
        self.Button_detectIsoCenter.setStyleSheet('border-width: 1px;')
        self.Button_detectIsoCenter.setStyleSheet('border-color: #1e1e1e;')
        
    def LockIsoCenter(self):
        """ Read current values from sliders/ spot location text fields and set as final """
        """ isocenter coordinates to be used for the actual positioning"""
        self.SpotTxt_x.setStyleSheet("color: rgb(255, 0, 0);")
        self.SpotTxt_y.setStyleSheet("color: rgb(255, 0, 0);")
        # Raise flag for checksum check later
        self.IsoCenter_flag = True
        
        # Function to pass IsoCenter values to parent window
        self.Owner.return_isocenter(self.Image, self.SpotTxt_x.value(), self.SpotTxt_y.value())
        
        logging.info('Isocenter coordinates confirmed')

        
    def update_crosshair(self):
        "Get value from Spinboxes and update all markers/plots if that value is changed"
        x = self.SpotTxt_x.value()
        y = self.SpotTxt_y.value()

        # Update Plot Markers
        self.hline.set_ydata(y)
        self.vline.set_xdata(x)

        #Update Plot
        self.Display_IsoCenter.canvas.draw()

        self.SpotTxt_x.setStyleSheet("color: rgb(0, 0, 0);")
        self.SpotTxt_y.setStyleSheet("color: rgb(0, 0, 0);")
        self.IsoCenter_flag = False
        
    def spotDetect(self):
        " Function that is invoked by ROI selection, autodetects earpin"
        #Get ROI limits from drawn rectangle            
        x = int(np.floor(self.rect.get_x()))
        y = int(np.floor(self.rect.get_y()))
        
        #get data selection from inside the rectangle
        width  = int(np.floor(self.rect.get_width()))
        height = int(np.floor(self.rect.get_height()))        
        subset = self.Image.data[y: y + height, x: x + width]
        
        # Calculate fit function values
        try:
            popt, pcov = find_center(subset, x, y, sigma = 5.0)
            logging.info('Detected coordinates for earpin: x = {:2.1f}, y = {:2.1f}'.format(popt[1], popt[2]))
        except Exception:
            logging.error('Autodetection of Landmark in ROI failed.')
            self.TxtEarpinX.setValue(0)
            self.TxtEarpinY.setValue(0)
            return 0
        
        xx, yy, xrange, yrange = array2mesh(self.Image.data)
        data_fitted = twoD_Gaussian((xx, yy), *popt)
    
        # Print markers into image
        self.canvas.axes.contour(xx, yy, data_fitted.reshape(yrange, xrange), 5)
        self.target_markers.append(self.canvas.axes.axvline(popt[1], 0, self.canvas.axes.get_ylim()[1]))
        self.target_markers.append(self.canvas.axes.axhline(popt[2], 0, self.canvas.axes.get_xlim()[1]))
        self.canvas.draw()
        
        self.SpotTxt_x.setValue(popt[1])
        self.SpotTxt_y.setValue(popt[2])
        
        logging.info('Coordinates of IsoCenter set to x = {:.1f}, y = {:.1f}'.format(popt[1], popt[2]))
        
    def Done(self):
        "Ends IsoCenter Definition and closes Child"
        # Also check whether all values were locked to main window
        if not self.IsoCenter_flag:
            Hint = QMessage()
            Hint.setStandardButtons( QMessage.No | QMessage.Yes)
            Hint.setIcon(QMessage.Information)
            Hint.setText("Some values have not been locked or were modified! \nProceed?")
            answer = Hint.exec_()
            if answer == QMessage.Yes: self.close()
        else:
            self.close()
            



''''''''''''''''''''''''
"""Landmark -Dialogue"""
''''''''''''''''''''''''
class Landmark_Child(QMain, Landmark.Ui_Landmark):
    "Class that contains subroutines to define isocenter from Lynx image"
    def __init__(self, parent, Owner):
        super(Landmark_Child, self).__init__(parent)
        
        self.setupUi(self)
        self.parent = parent # GUI instance
        self.Owner = Owner
        # self.image_data = Owner.Radiography_scatter
        
        # Data container
        self.Image = Lynx()
        
        # Set up plots
        self.canvas = self.Display_Landmarks.canvas
        
        # Connect Buttons and fields
        self.d_SourceDetector.valueChanged.connect(self.calcspacing)
        self.d_ObjectDetector.valueChanged.connect(self.calcspacing)
        
        # Set defaults
        self.d_SourceDetector.setValue(200.0)
        self.d_ObjectDetector.setValue(9.0)
        
        #Set up different segmentation procedures
        self.Button_defineROI.clicked.connect(self.define_ROI) # define ROI for earpin autodetection
        
        #Buttons about earpin definition
        self.Button_LoadLandmark.clicked.connect(self.load) # Load Radiography image
        self.Button_accptPxSpace.clicked.connect(self.accept_spacing) # set bed values and disconnect all sliders and pass values relevant for spacing to parent
        self.Button_lockEarpin.clicked.connect(self.Lock_Landmarks) # pass values about landmarks to parent
        
        # Finish 
        self.Button_Done.clicked.connect(self.Done)
        
        #Flags and Containers
        self.press = None
        self.rects = []
        self.target_markers = []
        
        self.Landmark_flag = False
        self.Spacing_flag  = False
        
    def load(self):
        "load radiography image of Bedding landmark"
        if pyqt_version == 5:
            fname = Qfile.getOpenFileName(self, 'Open file', folder,"Dicom files (*.dcm)")[0]
        else:
            fname = str(Qfile.getOpenFileName(self, 'Open file', folder,"Dicom files (*.dcm)"))
        
        # get filename from full path and display     
        _, filename = ntpath.split(fname)
        self.Text_Filename.setText(filename)
        
        # Load Radiography and display
        self.Image.load(fname)
        self.canvas.axes.imshow(self.Image.data, cmap = 'gray', 
                                zorder=1, origin = 'lower')
        self.canvas.draw()
        
        logging.info('{:s} imported as Isocenter Radiography'.format(filename))
        
        self.IsoCenter_flag = False
                    
        
    def calcspacing(self):
        """Calculate new pixel spacing based upon distances between
        Radiation source, object and detector"""
        dd     = 0.5 # pixel spacing of detector
        d_OD   = self.d_ObjectDetector.value()
        d_SD   = self.d_SourceDetector.value()
        
        if d_OD !=0 and d_SD != 0:
            self.Spacing = dd*(1.0 - d_OD/d_SD)
            self.LabelPixSpace.setText('Pixel Spacing: ' + '{:4.2f}'.format(self.Spacing) + ' mm')
              
        
    def define_ROI(self):
        "Specify a ROI within which the bed contours can be found"
        
        self.Button_defineROI.setChecked(True)
        self.Button_defineROI.setStyleSheet('border: 2px solid QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #ffa02f, stop: 1 #d7801a);')
                                                                               
        # If rects or other markers are visible, remove        
        for rect in self.rects:
            rect.remove()
        self.rects = []        
        for marker in self.target_markers:
            marker.remove()
        self.target_markers = []

        self.Display_Landmarks.canvas.draw()        
        
        self.connect()        
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()
        self.canvas.draw()
        
        
    def connect(self):
        'connect to all the events we need'
        self.cidpress = self.canvas.mpl_connect(
            'button_press_event', self.on_press)
        self.cidrelease = self.canvas.mpl_connect(
            'button_release_event', self.on_release)
        self.cidmotion = self.canvas.mpl_connect(
            'motion_notify_event', self.on_motion)
            
    def on_press(self, event):
        'on button press we will see if the mouse is over us and store some data'
        #Existiert schon ein Rechteck? Falls nein
        if not self.rects: # Neues Rechteck malen
            self.rect = self.canvas.axes.add_patch(patches.Rectangle((event.xdata,event.ydata), 0, 0 , fill = False))
            self.rects.append(self.rect)
        else: #Altes Rechteck/Konturlinien weg und neu malen
            for rect in self.rects: 
                rect.remove()
                self.rects = []
            
            self.rect = self.canvas.axes.add_patch(patches.Rectangle((event.xdata,event.ydata), 0, 0 , fill = False))
            self.rects.append(self.rect)
        
        # Ursprungskoordinaten in self.press hinterlegen. self.press enthält nur werte wenn geklickt wurde!                        
        self.press = self.rect.xy
        self.canvas.draw()
        
    def on_motion(self, event):
        'on motion move the boundaries of the rect to cursor location'
        #  Is the button pushed or have values been stored in self.press, respectively?
        if self.press is None: return
        x0, y0 = self.press
        
        if event.xdata < x0:
            self.rect.set_x(event.xdata)
        if event.ydata < y0:
            self.rect.set_y(event.ydata)
            
        self.rect.set_width(abs(event.xdata - x0))
        self.rect.set_height(abs(event.xdata - x0)) #set to square for fitting purpose
        self.canvas.draw()
        
    def on_release(self, event):
        'on release we reset the press data and disconnect'
        self.press = None
        self.canvas.draw()
        
        self.canvas.mpl_disconnect(self.cidpress)
        self.canvas.mpl_disconnect(self.cidrelease)
        self.canvas.mpl_disconnect(self.cidmotion)
        
        self.pinDetect()
        self.Button_defineROI.setChecked(False)
        self.Button_defineROI.setStyleSheet('border-width: 1px;')
        self.Button_defineROI.setStyleSheet('border-color: #1e1e1e;')
        
    def pinDetect(self):
        " Function that is invoked by ROI selection, autodetects earpin"
        #Get ROI limits from drawn rectangle            
        x = int(np.floor(self.rect.get_x()))
        y = int(np.floor(self.rect.get_y()))
        
        width  = int(np.floor(self.rect.get_width()))
        height = int(np.floor(self.rect.get_height()))
        
        #get data selection from inside the rectangle and invert
        subset = self.Image.data[y: y + height, x: x + width]
        subset = np.max(subset) - subset
        
        # Calculate fit function values
        try:
            popt, pcov = find_center(subset, x, y, sigma = 5.0)
            logging.info('Detected coordinates for earpin: x = {:2.1f}, y = {:2.1f}'.format(popt[1], popt[2]))
        except Exception:
            logging.error('ERROR: Autodetection of Landmark in ROI failed.')
            self.TxtEarpinX.setValue(0)
            self.TxtEarpinY.setValue(0)
            return 0
        
        xx, yy, xrange, yrange = array2mesh(self.Image.data)
        data_fitted = twoD_Gaussian((xx, yy), *popt)
    
        # Print markers into image
        self.canvas.axes.contour(xx, yy, data_fitted.reshape(yrange, xrange), 5)
        self.target_markers.append(self.canvas.axes.axvline(popt[1], 0, self.canvas.axes.get_ylim()[1]))
        self.target_markers.append(self.canvas.axes.axhline(popt[2], 0, self.canvas.axes.get_xlim()[1]))
        self.canvas.draw()
        
        self.TxtEarpinX.setValue(popt[1])
        self.TxtEarpinY.setValue(popt[2])
        
        logging.info('Coordinates of Radiography landmarks: x = {:.1f}, y = {:.1f}'.format(
                popt[1], popt[2]))
        
    def accept_spacing(self):
        "Lock Spacing and disconnect sliders"
        self.d_SourceDetector.setStyleSheet("color: rgb(255, 0, 0);")
        self.d_ObjectDetector.setStyleSheet("color: rgb(255, 0, 0);")
        
        # Check if rectangle is still in plot
        for rect in self.rects:
            rect.remove()
        self.rects = []
        #Update Plot
        self.Display_Landmarks.canvas.draw()
        
        # Pass spacing to parent
        self.Owner.return_spacing(self.Spacing)
        
        # Raise Flag
        self.Spacing_flag = True
        
        # Log 
        logging.info('Pixel spacing k = {:.2f} mm/px of landmark radiography confirmed'.format(
                self.Spacing))
        
    def Lock_Landmarks(self):
        "Checks if image is X-Ray or Dicom and passes landmark coordinates to parent window"
        
        # Paint it Red
        self.TxtEarpinX.setStyleSheet("color: rgb(255, 0, 0);")
        self.TxtEarpinY.setStyleSheet("color: rgb(255, 0, 0);")
        
        # Check and pass
        self.Owner.return_landmarks(self.Image, self.TxtEarpinX.value(), self.TxtEarpinY.value())
        
        # Raise Flag
        self.Landmark_flag = True
        
        # Log
        logging.info('Coordinates of Radiography landmarks confirmed')

    def Done(self):
        "Closses the window"
        
        #Check if all values have been set properly
        if False in [self.Spacing_flag, self.Landmark_flag]:
            Hint = QMessage()
            Hint.setStandardButtons( QMessage.No | QMessage.Yes)
            Hint.setIcon(QMessage.Information)
            Hint.setText("Some values have not been locked or were modified! \nProceed?")
            answer = Hint.exec_()
            if answer == QMessage.Yes: self.close()
        else:
            self.close()
        

    
def find_center(dataset, x_offset, y_offset, sigma):
    """ Fit function to find IsoCenter without Sliders"""
    xx, yy,_,_ = array2mesh(dataset)
     
    
    # Even background of dataset
    dataset = dataset - np.median(dataset)
    dataset[dataset < 0] = 0    
    
    # Calculate values for initial guess
    Offset = np.median(dataset)
    Amplitude = np.max(dataset) - Offset
    y0, x0 = np.unravel_index(dataset.argmax(), dataset.shape)
    initial_guess = [Amplitude, x0, y0, sigma, sigma, 0, Offset]
        
    # Run Fit
    popt, pcov = opt.curve_fit(twoD_Gaussian, (xx, yy), dataset.ravel(), p0=initial_guess)
  
    # Add offset to account for piece of vision effect
    popt[1] += x_offset
    popt[2] += y_offset
    
    return popt, pcov


        
def twoD_Gaussian(xdata_tuple, amplitude, xo, yo, sigma_x, sigma_y, theta, offset):
    (x, y) = xdata_tuple                                                        
    xo = float(xo)                                                              
    yo = float(yo)                                                              
    a = (np.cos(theta)**2)/(2*sigma_x**2) + (np.sin(theta)**2)/(2*sigma_y**2)   
    b = -(np.sin(2*theta))/(4*sigma_x**2) + (np.sin(2*theta))/(4*sigma_y**2)    
    c = (np.sin(theta)**2)/(2*sigma_x**2) + (np.cos(theta)**2)/(2*sigma_y**2)   
    g = offset + amplitude*np.exp( - (a*((x-xo)**2) + 2*b*(x-xo)*(y-yo)         
                        + c*((y-yo)**2)))                                   
    return g.ravel()
        
def array2mesh(array):
    """takes an array and returns the according meshgrid"""
    
    try:
        yrange = np.shape(array)[0]
        xrange = np.shape(array)[1]
        
        # Set grid for evaluatin of fit
        x = np.linspace(0, xrange-1, xrange)
        y = np.linspace(0, yrange-1, yrange)
        
        xx, yy = np.meshgrid(x, y)
    except Exception:
        logging.debug(traceback.print_exc())
        
    return xx, yy, xrange, yrange
    

