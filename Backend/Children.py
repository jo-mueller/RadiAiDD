# -*- coding: utf-8 -*-
import matplotlib.patches as patches
from matplotlib.widgets  import RectangleSelector
import numpy as np
import traceback
import logging
import tifffile
import pydicom as dcm
import scipy.optimize as opt
import matplotlib

from Backend.Containers import RadiographyImage

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
    from PyQt5.QtCore import Qt
    import PyQt5.QtCore as QtCore
    from PyQt5.QtWidgets import QInputDialog
    pyqt_version = 5

if pyqt_version == 4:
    import IsoCenter as IsoCenter
    import Landmark as Landmark

elif pyqt_version == 5:
    import Backend.UI.IsoCenter5 as IsoCenter
    import Backend.UI.Landmark5 as Landmark


''''''''''''''''''''''''
"""ISOCENTER -Dialogue"""
''''''''''''''''''''''''

class IsoCenter_Child(QMain, IsoCenter.Ui_IsoCenter):
    "Class that contains subroutines to define isocenter from Lynx image"

    def __init__(self, parent, owner):
        super(IsoCenter_Child, self).__init__()

        self.Owner = owner
        self.setupUi(self)
        self.setStyleSheet(parent.styleSheet())

        self.parent = parent
        self.canvas = self.Display_IsoCenter.canvas
        self.toolbar = self.canvas.toolbar

        # Connect buttons
        self.Button_LoadSpot.clicked.connect(self.load)
        self.Button_detectIsoCenter.clicked.connect(self.drawRect)
        self.Button_SetIsoCenter.clicked.connect(self.LockIsoCenter)
        self.Button_Done.clicked.connect(self.Done)

        # Works only after first rectangle was drawn
        try:
            self.Button_detectIsoCenter.clicked.connect(self.initclick)
        except AttributeError:
            pass

        # Flags and Containers
        self.Image = None
        self.press = None
        self.rects = []
        self.target_markers = []

        # Flags
        self.IsoCenter_flag = False

        # Lists for isocenter markers in canvas
        self.target_markers = []

    def drawRect(self):

        # Remove previous spotdetections
        for item in self.target_markers:
            if type(item) == matplotlib.contour.QuadContourSet:
                [artist.set_visible(False) for artist in item.collections]
            else:
                item.set_visible(False)

        # change cursor style
        QApplication.setOverrideCursor(Qt.CrossCursor)

        # Rectangle selector for 2d fit
        rectprops = dict(facecolor='orange', edgecolor=None,
                         alpha=0.2, fill=True)
        # drawtype is 'box' or 'line' or 'none'
        self.RS = RectangleSelector(self.canvas.axes,
                                    self.line_select_callback,
                                    drawtype='box', rectprops=rectprops,
                                    button=[1],  # don't use middle button
                                    minspanx=5, minspany=5,
                                    spancoords='pixels', useblit=True,
                                    interactive=True)
        self.canvas.draw()
        self.bg = self.canvas.copy_from_bbox(self.RS.ax.bbox)
        self.RS.set_visible(True)

        ext = (0, 4, 0, 1)
        self.RS.draw_shape(ext)

        # Update displayed handles
        self.RS._corner_handles.set_data(*self.RS.corners)
        self.RS._edge_handles.set_data(*self.RS.edge_centers)
        self.RS._center_handle.set_data(*self.RS.center)
        for artist in self.RS.artists:
            self.RS.ax.draw_artist(artist)
            artist.set_animated(False)
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect("button_press_event",
                                           self.initclick)

    def line_select_callback(self, eclick, erelease):
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata

        p1 = (x1, y1)
        p2 = (x2, y2)

        self.spotDetect(p1, p2)

    def initclick(self, evt):
        self.RS.background = self.bg
        self.RS.update()
        for artist in self.RS.artists:
            artist.set_animated(True)
        self.canvas.mpl_disconnect(self.cid)

    def load(self):
        "load radiography image of beam IsoCenter"

        # get filename from full path and display
        fname = Qfile.getOpenFileName(self, 'Open file', "",
                                      "Dicom files (*.dcm *tiff *tif)")[0]
        try:
            # import imagedata with regard to filetype
            if fname.endswith("dcm"):
                meta = dcm.read_file(fname)
                self.Image = RadiographyImage(fname, meta.pixel_array,
                                              meta.PixelSpacing)

            elif fname.endswith("tif") or fname.endswith("tiff"):
                pw, okx = QInputDialog.getDouble(self,
                                                 'Pixel Spacing',
                                                 'pixel width (mm):',
                                                 0.05, decimals=2)
                self.Image = RadiographyImage(fname, tifffile.imread(fname),
                                              pw)

            self.Text_Filename.setText(fname)  # display filename
            self.canvas.axes.imshow(self.Image.array, cmap='gray',
                                    zorder=1, origin='lower')
            self.canvas.draw()
            logging.info('{:s} imported as Isocenter'.format(fname))

        except Exception:
            logging.ERROR("{:s} could not be opened".format(fname))
            self.IsoCenter_flag = False
            return 0

    def LockIsoCenter(self):
        """ Read current values from sliders/ spot location text fields
        and set as final isocenter coordinates to be used for the
        actual positioning"""
        self.SpotTxt_x.setStyleSheet("color: rgb(255, 0, 0);")
        self.SpotTxt_y.setStyleSheet("color: rgb(255, 0, 0);")
        # Raise flag for checksum check later
        self.IsoCenter_flag = True

        # Function to pass IsoCenter values to parent window
        self.Owner.return_isocenter(self.Image,
                                    [self.SpotTxt_x.value(),
                                     self.SpotTxt_y.value()])
        logging.info('Isocenter coordinates confirmed')

    def update_crosshair(self):
        """Get value from Spinboxes and update all
        markers/plots if that value is changed"""
        x = self.SpotTxt_x.value()
        y = self.SpotTxt_y.value()

        # Update Plot Markers
        self.hline.set_ydata(y)
        self.vline.set_xdata(x)

        # Update Plot
        self.Display_IsoCenter.canvas.draw()

        self.SpotTxt_x.setStyleSheet("color: rgb(0, 0, 0);")
        self.SpotTxt_y.setStyleSheet("color: rgb(0, 0, 0);")
        self.IsoCenter_flag = False

    def spotDetect(self, p1, p2):
        " Function that is invoked by ROI selection, autodetects earpin"

        # Restore old cursor
        QApplication.restoreOverrideCursor()

        # Get ROI limits from drawn rectangle corners
        x = int(min(p1[0], p2[0]) + 0.5)
        y = int(min(p1[1], p2[1]) + 0.5)
        width = int(np.abs(p1[0] - p2[0]) + 0.5)
        height = int(np.abs(p1[1] - p2[1]) + 0.5)

        subset = self.Image.array[y: y + height, x: x + width]

        # Calculate fit function values
        try:
            popt, pcov = find_center(subset, x, y, sigma=5.0)
            logging.info('Detected coordinates for earpin:'
                         'x = {:2.1f}, y = {:2.1f}'.format(popt[1], popt[2]))
        except Exception:
            logging.error('Autodetection of Landmark in ROI failed.')
            self.TxtEarpinX.setValue(0)
            self.TxtEarpinY.setValue(0)
            return 0

        xx, yy, xrange, yrange = array2mesh(self.Image.array)
        data_fitted = twoD_Gaussian((xx, yy), *popt)

        # Print markers into image
        ax = self.canvas.axes
        self.target_markers.append(ax.contour(xx, yy, data_fitted.reshape(
                                    yrange, xrange), 5))
        self.target_markers.append(ax.axvline(popt[1], 0, ax.get_ylim()[1]))
        self.target_markers.append(ax.axhline(popt[2], 0, ax.get_xlim()[1]))
        self.canvas.draw()

        self.SpotTxt_x.setValue(popt[1])
        self.SpotTxt_y.setValue(popt[2])

        logging.info('Coordinates of IsoCenter set to '
                     'x = {:.1f}, y = {:.1f}'.format(popt[1], popt[2]))

    def Done(self):
        "Ends IsoCenter Definition and closes Child"
        # Also check whether all values were locked to main window
        if not self.IsoCenter_flag:
            Hint = QMessage()
            Hint.setStandardButtons(QMessage.No | QMessage.Yes)
            Hint.setIcon(QMessage.Information)
            Hint.setText("Some values have not been locked or were modified!"
                         "\nProceed?")
            answer = Hint.exec_()
            if answer == QMessage.Yes:
                self.close()
        else:
            self.close()


''''''''''''''''''''''''
"""Landmark -Dialogue"""
''''''''''''''''''''''''


class Landmark_Child(QMain, Landmark.Ui_Landmark):
    "Class that contains subroutines to define isocenter from Lynx image"

    def __init__(self, parent, Owner):
        super(Landmark_Child, self).__init__()

        self.setupUi(self)
        self.parent = parent  # GUI instance
        self.Owner = Owner
        self.setStyleSheet(parent.styleSheet())

        # Data container
        self.Image = None

        # Set up plots
        self.canvas = self.Display_Landmarks.canvas

        # Connect Buttons and fields
        self.d_SourceDetector.valueChanged.connect(self.calcspacing)
        self.d_ObjectDetector.valueChanged.connect(self.calcspacing)

        # Set defaults
        self.d_SourceDetector.setValue(200.0)
        self.d_ObjectDetector.setValue(9.0)

        # Set up different segmentation procedures
        # define ROI for earpin autodetection
        self.Button_defineROI.clicked.connect(self.drawRect)

        # Buttons about earpin definition
        # Load Radiography image
        self.Button_LoadLandmark.clicked.connect(self.load)
        # set bed values and disconnect all sliders
        self.Button_accptPxSpace.clicked.connect(self.accept_spacing)
        # pass values about landmarks to parent
        self.Button_lockEarpin.clicked.connect(self.Lock_Landmarks)

        # Finish
        self.Button_Done.clicked.connect(self.Done)

        # Flags and Containers
        self.press = None
        self.rects = []
        self.target_markers = []

        self.Landmark_flag = False
        self.Spacing_flag = False

    def drawRect(self):

        # Remove previous spotdetections
        for item in self.target_markers:
            if type(item) == matplotlib.contour.QuadContourSet:
                [artist.set_visible(False) for artist in item.collections]
            else:
                item.set_visible(False)

        # change cursor style
        QApplication.setOverrideCursor(Qt.CrossCursor)

        # Rectangle selector for 2d fit
        rectprops = dict(facecolor='orange', edgecolor=None,
                         alpha=0.2, fill=True)
        # drawtype is 'box' or 'line' or 'none'
        self.RS = RectangleSelector(self.canvas.axes,
                                    self.line_select_callback,
                                    drawtype='box', rectprops=rectprops,
                                    button=[1],  # don't use middle button
                                    minspanx=5, minspany=5,
                                    spancoords='pixels', useblit=True,
                                    interactive=True)
        self.canvas.draw()
        self.bg = self.canvas.copy_from_bbox(self.RS.ax.bbox)
        self.RS.set_visible(True)

        ext = (0, 4, 0, 1)
        self.RS.draw_shape(ext)

        # Update displayed handles
        self.RS._corner_handles.set_data(*self.RS.corners)
        self.RS._edge_handles.set_data(*self.RS.edge_centers)
        self.RS._center_handle.set_data(*self.RS.center)
        for artist in self.RS.artists:
            self.RS.ax.draw_artist(artist)
            artist.set_animated(False)
        self.canvas.draw()
        self.cid = self.canvas.mpl_connect("button_press_event",
                                           self.initclick)

    def line_select_callback(self, eclick, erelease):
        x1, y1 = eclick.xdata, eclick.ydata
        x2, y2 = erelease.xdata, erelease.ydata

        p1 = (x1, y1)
        p2 = (x2, y2)

        self.pinDetect(p1, p2)

    def initclick(self, evt):
        self.RS.background = self.bg
        self.RS.update()
        for artist in self.RS.artists:
            artist.set_animated(True)
        self.canvas.mpl_disconnect(self.cid)

    def load(self):
        "load radiography image of object radiography"

        # get filename from full path and display
        fname = Qfile.getOpenFileName(self, 'Open file', "",
                                      "Dicom files (*.dcm *tiff *tif)")[0]
        try:
            # import imagedata with regard to filetype
            if fname.endswith("dcm"):
                meta = dcm.read_file(fname)
                self.Image = RadiographyImage(fname, meta.pixel_array,
                                              meta.PixelSpacing)

            elif fname.endswith("tif") or fname.endswith("tiff"):
                pw, okx = QInputDialog.getDouble(self,
                                                 'Pixel Spacing',
                                                 'pixel width (mm):',
                                                 0.05, decimals=2)
                self.Image = RadiographyImage(fname, tifffile.imread(fname),
                                              [pw, pw])

            self.Text_Filename.setText(fname)  # display filename

        except:
            logging.ERROR("{:s} could not be opened".format(fname))
            self.IsoCenter_flag = False
            return 0

        self.canvas.axes.imshow(self.Image.array, cmap='gray',
                                zorder=1, origin='lower')
        self.canvas.draw()
        self.calcspacing()  # recalculate spacing with new image
        logging.info('{:s} imported as Isocenter Radiography'.format(fname))
        
        self.gettablecoords()  # get motor coordinates for this image

    def gettablecoords(self):
        """Function that is called upon upload of radiography
        that prompts user to enter table coordinates"""

        x, okx = QInputDialog.getDouble(self, 'Table position: X', 'x_table:',
                                        0.0, decimals=4)
        y, oky = QInputDialog.getDouble(self, 'Table position: Y', 'y_table:',
                                        0.0, decimals=4)

        if not okx or not oky:
            self.parent.TableTxt_x.setText('X Value not set!!')
            self.parent.TableTxt_y.setText('Y Value not set!!')
        else:
            self.parent.TableTxt_x.setText('{:2.4f}'.format(x))
            self.parent.TableTxt_y.setText('{:2.4f}'.format(y))

        self.parent.TableTxt_x.setStyleSheet("color: #b1b1b1;")
        self.parent.TableTxt_y.setStyleSheet("color: #b1b1b1;")

    def calcspacing(self):
        """Calculate new pixel spacing based upon distances between
        Radiation source, object and detector"""
        try:
            dd = self.Image.pw[0]  # pixel spacing of detector in mm
            d_OD = self.d_ObjectDetector.value()
            d_SD = self.d_SourceDetector.value()

            if d_OD != 0 and d_SD != 0:
                self.Spacing = dd*(1.0 - d_OD/d_SD)  # Dreisatz
                self.LabelPixSpace.setText('Pixel Spacing: {:4.2f} mm'.format(
                    self.Spacing))
        except AttributeError:
            pass


    def pinDetect(self, p1, p2):
        " Function that is invoked by ROI selection, autodetects earpin"

        # Restore old cursor
        QApplication.restoreOverrideCursor()

        # Get ROI limits from drawn rectangle corners
        x = int(min(p1[0], p2[0]) + 0.5)
        y = int(min(p1[1], p2[1]) + 0.5)
        width = int(np.abs(p1[0] - p2[0]) + 0.5)
        height = int(np.abs(p1[1] - p2[1]) + 0.5)

        # get data selection from inside the rectangle and invert
        subset = self.Image.array[y: y + height, x: x + width]
        subset = np.max(subset) - subset

        # Calculate fit function values
        try:
            popt, pcov = find_center(subset, x, y, sigma=5.0)
            logging.info('Detected coordinates for earpin: '
                         'x = {:2.1f}, y = {:2.1f}'.format(popt[1], popt[2]))
        except Exception:
            logging.error('ERROR: Autodetection of Landmark in ROI failed.')
            self.TxtEarpinX.setValue(0)
            self.TxtEarpinY.setValue(0)
            return 0

        xx, yy, xrange, yrange = array2mesh(self.Image.array)
        data_fitted = twoD_Gaussian((xx, yy), *popt)

        # Print markers into image
        ax = self.canvas.axes
        self.target_markers.append(
            ax.contour(xx, yy, data_fitted.reshape(yrange, xrange), 5))
        self.target_markers.append(ax.axvline(popt[1], 0, ax.get_ylim()[1]))
        self.target_markers.append(ax.axhline(popt[2], 0, ax.get_xlim()[1]))
        self.canvas.draw()

        self.TxtEarpinX.setValue(popt[1])
        self.TxtEarpinY.setValue(popt[2])

        logging.info('Coordinates of Radiography landmarks: '
                     'x = {:.1f}, y = {:.1f}'.format(popt[1], popt[2]))

    def accept_spacing(self):
        "Lock Spacing and disconnect sliders"
        self.d_SourceDetector.setStyleSheet("color: rgb(255, 0, 0);")
        self.d_ObjectDetector.setStyleSheet("color: rgb(255, 0, 0);")

        # Check if rectangle is still in plot
        for rect in self.rects:
            rect.remove()
        self.rects = []
        # Update Plot
        self.Display_Landmarks.canvas.draw()

        # Pass spacing to parent
        self.Owner.return_spacing(self.Spacing)

        # Raise Flag
        self.Spacing_flag = True

        # Log
        logging.info('Pixel spacing k = {:.2f} mm/px of'
                     'landmark radiography confirmed'.format(self.Spacing))

    def Lock_Landmarks(self):
        """Checks if image is X-Ray or Dicom and
        passes landmark coordinates to parent window"""

        # Paint it Red
        self.TxtEarpinX.setStyleSheet("color: rgb(255, 0, 0);")
        self.TxtEarpinY.setStyleSheet("color: rgb(255, 0, 0);")

        # Check and pass
        self.Owner.return_landmarks(self.Image,
                                    [self.TxtEarpinX.value(),
                                     self.TxtEarpinY.value()])

        # Raise Flag
        self.Landmark_flag = True

        # Log
        logging.info('Coordinates of Radiography landmarks confirmed')

    def Done(self):
        "Closses the window"

        # Check if all values have been set properly
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


