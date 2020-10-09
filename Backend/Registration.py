# -*- coding: utf-8 -*-
"""
Created on Wed Aug 19 20:08:38 2020

@author: johan
"""
import tifffile
import logging
import numpy as np
import cv2
import os

from PyQt5.QtWidgets import QFileDialog as Qfile
from PyQt5.QtWidgets import QPushButton

from PyQt5.QtWidgets import QToolBar

import matplotlib.pyplot as plt
from scipy.optimize import minimize
from Backend.Containers import GrayWindow2 as GW
from Backend.Containers import DragPoint

ccycle = plt.rcParams['axes.prop_cycle'].by_key()['color']


class DisplayObject:
    def __init__(self, canvas, label, GrayControl=None, **kwargs):
        self.canvas = canvas
        self.Qlabel = label

        self.GUI = self.getGUI()
        self.GrayControl = GrayControl
        self.overlay = None  # storage for overlay image array
        self.has_overlay = False  # Flag that tells whether image has overlay
        self.overlay_active = False  #Flag that tells if overlay is active

    def load_Image(self):
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

        self.h_img = self.display(cmap='gray')
        self.Qlabel.setText(fname)

        logging.info('Successfully imported {:s}'.format(fname))
        self.GUI.WindowSelector.setEnabled(True)

        self.GrayControl.fill(self.array)

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

    def display(self, **kwargs):
        self.canvas.axes.clear()
        handle = self.canvas.axes.imshow(self.array, origin='lower', **kwargs)
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


class Registration:
    def __init__(self, parent):

        self.GUI = parent

        # Table for target coordinates
        # Put Button in Table to get target coordinates
        self.Btn_get_raw_trg = QPushButton(self.GUI.table_TrgCoords)
        self.Btn_get_raw_trg.setText('Get')
        self.GUI.table_TrgCoords.setCellWidget(0, 1, self.Btn_get_raw_trg)
        self.Btn_get_raw_trg.clicked.connect(self.get_raw_target)

        self.Moving = DisplayObject(self.GUI.Display_Moving.canvas,
                                    self.GUI.Label_Moving)
        self.Fixed = DisplayObject(self.GUI.Display_Fixed.canvas,
                                   self.GUI.Label_Fixed)
        self.Warped = DisplayObject(self.GUI.Display_Fusion.canvas,
                                    None)

        # GrayWIndow control for both images
        GrayObj_M = GW(self.Moving.canvas,
                       self.GUI.ActPos_GreyWindow_Hist.canvas,
                       self.GUI.ActPos_Slider_Center,
                       self.GUI.ActPos_SliderRange,
                       self.GUI.ActPos_Label_Center_Alignment,
                       self.GUI.ActPos_Label_Range_Alignment)
        GrayObj_F = GW(self.Fixed.canvas,
                       self.GUI.ActPos_GreyWindow_Hist.canvas,
                       self.GUI.ActPos_Slider_Center,
                       self.GUI.ActPos_SliderRange,
                       self.GUI.ActPos_Label_Center_Alignment,
                       self.GUI.ActPos_Label_Range_Alignment)
        self.Fixed.GrayControl = GrayObj_F
        self.Moving.GrayControl = GrayObj_M
        self.Fixed.GrayControl.histcolor = 'blue'
        self.Moving.GrayControl.histcolor = 'orange'

        self.GUI.Button_load_moving.clicked.connect(self.Moving.load_Image)
        self.GUI.Button_load_fixed.clicked.connect(self.Fixed.load_Image)

        # Allocate connections for grayvalue control
        self.GUI.WindowSelector.addItem("")
        self.GUI.WindowSelector.addItem("Moving image (X-Ray)")
        self.GUI.WindowSelector.addItem("Target image (Radiography)")
        self.GUI.WindowSelector.currentIndexChanged.connect(self.greyscale)
        self.GUI.ActPos_GreyWindow_Hist.findChild(QToolBar).setVisible(False)

        # Control for overlay function
        self.GUI.Button_toggleOverlay.clicked.connect(self.toggleOverlay)

        # Buttons for default marker positions
        self.GUI.Button_default_moving.clicked.connect(
            lambda: self.setDefaultPositions("moving"))
        self.GUI.Button_default_fixed.clicked.connect(
            lambda: self.setDefaultPositions("fixed"))

        # Buttons for registration execution
        self.GUI.Button_RunReg.clicked.connect(self.runRegistration)

        # Buttons for Motor stuff
        self.GUI.Btn_getCurrentMotor.clicked.connect(
            self.getCurrentMotorPos)
        self.GUI.Btn_setMotor_Origin.clicked.connect(
            self.setMotorOrigin)
        self.GUI.Btn_Reg_calcTable.clicked.connect(
            self.calcMotor)

        # List of landmarks and default coordinates
        self.LM_moving = []
        self.LM_fixed = []

        self.default_moving = [[627, 489],
                               [484, 473],
                               [590, 498],
                               [643, 438],
                               [703, 443]]
        self.default_fixed = [[603, 368],
                              [336, 332],
                              [502, 362],
                              [607, 267],
                              [704, 281]]

        # Flags
        self.PointsOnCanvas_moving = False
        self.PointsOnCanvas_fixed = False
        self.ImageOnFusion = False

        self.TrfTrgPoint = None
        self.TrgRaw = None

        self.sliderconnected = False
        logging.info('Registration class successfully initialized')

    def toggleOverlay(self):
        'Shows the overlay of image if it exists'

        # Has an overlay been passed to the moving image?
        # Only moving image can have overlay.
        if not self.Moving.has_overlay:
            logging.info("Current moving image does not have an overlay")
            return 0
        else:
            self.Moving.toggleOverlay()

        if self.Warped.has_overlay:
            self.Warped.toggleOverlay()
        else:
            return 0

        if self.Warped.overlay_active != self.Moving.overlay_active:
            self.Warped.toggleOverlay()

    def greyscale(self):
        'Assigns the image controls to the chosen display if required.'

        # Try to disconnect upon connecting again
        self.Moving.GrayControl.deactivate()
        self.Fixed.GrayControl.deactivate()

        if self.GUI.WindowSelector.currentIndex() == 1:
            self.Moving.GrayControl.activate()
        elif self.GUI.WindowSelector.currentIndex() == 2:
            self.Fixed.GrayControl.activate()
        else:
            return 0

    def calcMotor(self):
        'Calculates Motor target coordinates'

        if self.GUI.TableTxt_x.text() == "":
            logging.error("No Motor coordinates given")
            return 0
        if self.GUI.SpotTxt_x.text() == "":
            logging.error("No Isocenter coordinates given")
            return 0

        x_Table = float(self.GUI.TableTxt_x.text())
        y_Table = float(self.GUI.TableTxt_y.text())

        x_Target = self.TrfTrgPoint.x
        y_Target = self.TrfTrgPoint.y

        x_Iso = float(self.GUI.SpotTxt_x.text())
        y_Iso = float(self.GUI.SpotTxt_y.text())

        # pw = self.GUI.TxtRG_pxcalc.getText()

        # calculate table movement
        # y is inverted because image y-axis is inverted, too
        x = x_Table + (x_Iso - x_Target) * 0.05  # mm
        y = y_Table + (y_Iso - y_Target) * 0.05  # mm

        self.GUI.TableTxt_xCorr.setText("{:.2f}".format(x))
        self.GUI.TableTxt_yCorr.setText("{:.2f}".format(y))
        logging.info("Calculated motor target position: (x={:.2f}, y={:.2f}"
                     .format(x, y))

    def setMotorOrigin(self):
        'Copies Motor origin to GUI'
        x = self.GUI.Box_MotorOriginX.value()
        y = self.GUI.Box_MotorOriginY.value()
        self.GUI.TableTxt_x.setText("{:.3f}".format(x))
        self.GUI.TableTxt_y.setText("{:.3f}".format(y))
        logging.info("Set motor origin position to (x={:.2f}, y={:.2f}"
                     .format(x, y))

    def getCurrentMotorPos(self):
        'Assumes currently set motor position as position of active RG image'
        x = float(self.GUI.TablePosX.text())
        y = float(self.GUI.TablePosY.text())
        self.GUI.Box_MotorOriginX.setValue(x)
        self.GUI.Box_MotorOriginY.setValue(y)
        logging.info("Current motor position: (x={:.2f}, y={:.2f}"
                     .format(x, y))

    def get_raw_target(self):
        """
        Identify coordinates of target from supplied mask file
        """
        fname = self.GUI.Label_Moving.text()
        if fname == "":
            return 0
        x = ""
        y = ""
        fname = os.path.basename(fname).split(".")[0].split("_")
        for piece in fname:
            try:
                if "x" in piece:
                    x = int(piece.split("x")[0])
                elif "y" in piece:
                    y = int(piece.split("y")[0])

            except Exception:
                logging.error("Target coordinates could not be " +
                              "inferred from filename")
                continue

        # If a target already exists, remove old one
        if self.TrgRaw is not None:
            self.TrgRaw.toggle()
            del(self.TrgRaw)

        if x == "":
            center = np.asarray(self.Moving.array.shape)/2
            x, y = center[0], center[1]

        self.TrgRaw = DragPoint(self.GUI.Display_Moving, x=x, y=y,
                                transparent=True, size=30/2.0)
        self.GUI.table_TrgCoords.item(0, 0).setText("{:.0f}, {:.0f}"
                                                    .format(x, y))
        self.TrgRaw.Signal.moving.connect(self.updateRawTarget)

    def updateRawTarget(self):
        'Update untransformed target coord. in table if point is moved'
        x = self.TrgRaw.x
        y = self.TrgRaw.y
        self.GUI.table_TrgCoords.item(0, 0).setText("{:.0f}, {:.0f}"
                                                    .format(x, y))

    def runRegistration(self):
        """
        Do similarity transform to warp moving image on target image
        (landmark-based)
        """

        # Have landmarks been defined?
        if not (self.PointsOnCanvas_fixed and self.PointsOnCanvas_moving):
            logging.error("Missing data (image data or landmarks)" +
                          " for registration.")
            return 0

        vA = [(P.x, P.y) for P in self.LM_fixed]
        vB = [(P.x, P.y) for P in self.LM_moving]

        initial_guess = [1.7, 0, 0, 0]
        options = {"maxiter": 3000}
        res = minimize(self.cost_function, initial_guess, args=(vA, vB),
                       method='SLSQP', options=options)
        logging.info("Similarity transform optimization result:\n" +
                     "Success: {:b}, n_evals = {:d}\n"
                     .format(res.success, res.nfev) +
                     "scale={:.2f}, angle={:.2f}°, t=({:.1f}, {:.1f})"
                     .format(res.x[0], res.x[1], res.x[2], res.x[3]))

        # Transform and display warped image
        # Allocate new display Object(s) for this purpose
        self.Warped.array = self.ImageTransform(self.Moving.array, res.x)

        if self.Moving.has_overlay:
            self.Warped.overlay = self.ImageTransform(self.Moving.overlay, res.x)
            self.Warped.has_overlay = True

        canvas = self.GUI.Display_Fusion.canvas
        self.Warped.display(alpha=0.5, interpolation='nearest', cmap='gray')
        canvas.axes.imshow(self.Fixed.get_array(), cmap='gray',
                           alpha=0.5, interpolation='nearest', origin='lower')
        canvas.draw()

        # Transform target coordinates.
        # A target may not have been defined yet. Throws ValueError if no
        # target is known
        try:
            coords = self.GUI.table_TrgCoords.item(0, 0).text().split(",")
            r = self.f([np.array(coords).astype(np.float32)], res.x)[0]
            self.GUI.table_TrgCoords.item(1, 0).setText("{:.0f}, {:.0f}"
                                                        .format(r[0], r[1]))

            if self.TrfTrgPoint is not None:
                self.TrfTrgPoint.toggle()
                del(self.TrfTrgPoint)

            self.TrfTrgPoint = DragPoint(self.GUI.Display_Fusion,
                                         x=r[0], y=r[1],
                                         transparent=True, size=30/2.0*res.x[0])
        except ValueError:
            pass

        # Display trafo params in text-label
        txt = "r={:.2f}x, angle = {:.1f}, t = ({:.0f},{:.0f})".format(
            res.x[0], 180.0*res.x[1]/np.pi, res.x[2], res.x[3])

        self.GUI.Label_Trafo_Params.setText(txt)

        # set slider value
        self.GUI.Slider_RegOverlay.setValue(50)

        if not self.sliderconnected:
            self.GUI.Slider_RegOverlay.valueChanged.connect(self.adjust_alpha)
            self.sliderconnected = True

    def ImageTransform(self, Img, params):
        """
        Function for similarity transform of given input Image
        Input:
            Img: nd-array
            params: vector (length 4) with transformation parameters
                r (scaling factor), angle (rotation angle) t_1 and t_2
                (translation vector)
        Returns:
            nd-Image array
        """

        rows, cols = np.shape(Img)[0], np.shape(Img)[1]
        r, alpha, t1, t2 = params
        alpha = alpha/(np.pi)  # convert to degree
        A = cv2.getRotationMatrix2D((cols/2, rows/2), alpha, 1)
        T = np.float32([[1.0, 0.0, t1], [0.0, 1.0, t2]])

        Img = cv2.warpAffine(Img, A, (cols, rows))
        Img = cv2.resize(Img, None, fx=r, fy=r, interpolation=cv2.INTER_CUBIC)
        Img = cv2.warpAffine(Img, T, (cols, rows))

        return Img

    def adjust_alpha(self):
        """
        Adjust the alpha values of the fixed/warped image overlay.
        """
        # get alpha value from Slider
        alpha = float(self.GUI.Slider_RegOverlay.value()/100.0)

        # Get handles to both images and adjust alpha
        images = self.GUI.Display_Fusion.canvas.axes.get_images()
        Fixed = images[0]
        Warped = images[1]
        Fixed.set_alpha(alpha)
        Warped.set_alpha(1.0-alpha)

        # Update
        self.GUI.Display_Fusion.canvas.draw()

    def f(self, x, params):
        """
        similarity transformsformation of x according to parameters param
        x = (x_1, x_2)
        params = [r, alpha, t1, t2] denoting:
            - rotation angle
            - scaling factor
            - translation vector (t_1, t_2)
        """
        r, alpha, t1, t2 = params
        A = [[np.cos(alpha), (-1)*np.sin(alpha)],
             [np.sin(alpha), np.cos(alpha)]]

        if type(x) is tuple:
            return [r * np.dot(A, x) + [t1, t2]]
        else:
            return [r * np.dot(A, v) + [t1, t2] for v in x]

    def cost_function(self, params, v1, v2):
        """
        cost function to be minimized:
            Inputs:
                params: transformation parameters for v2
            returns:
                summed squared pairwise euclidian distance
                between two sets of vectors vectors v_1 and v_2
        """
        return np.sum([self.ED(x1, self.f([x2], params))
                       for x1, x2 in zip(v1, v2)])

    def ED(self, x1, x2):
        """Euclidian distance in 2D"""
        return np.sqrt(np.sum(np.power(np.subtract(x1, x2), 2)))

    def setDefaultPositions(self, which):
        # ______
        # MOVING
        # ______
        if which == "moving":
            QObj = self.GUI.Display_Moving

            # If points are already on canvas:
            if self.PointsOnCanvas_moving:
                [P.remove() for P in self.LM_moving]
                self.PointsOnCanvas_moving = False

            # remove reference to points
            del(self.LM_moving[:])

            # add the default draggable points to the figure
            for i in range(len(self.default_moving)):
                point = DragPoint(QObj, self.default_moving[i][0],
                                  self.default_moving[i][1],
                                  fc=ccycle[i % len(ccycle)],
                                  size=5)
                point.Signal.moving.connect(lambda: self.updateTable("moving"))
                self.LM_moving.append(point)
            self.PointsOnCanvas_moving = True

        # ______
        # FIXED
        # ______
        elif which == "fixed":
            QObj = self.GUI.Display_Fixed

            # If points are already on canvas
            if self.PointsOnCanvas_fixed:
                [P.remove() for P in self.LM_fixed]
                self.PointsOnCanvas_fixed = False

            # remove reference to points
            del(self.LM_fixed[:])

            # add the default draggable points to the figure
            # Use same coordinates as in moving image
            for i in range(len(self.default_fixed)):
                point = DragPoint(QObj, self.default_fixed[i][0],
                                  self.default_fixed[i][1],
                                  fc=ccycle[i % len(ccycle)],
                                  size=5)
                point.Signal.moving.connect(lambda: self.updateTable("fixed"))
                self.LM_fixed.append(point)
            self.PointsOnCanvas_fixed = True

        # Now: Take care of sliders for markersize
        if which == "moving":
            self.GUI.Slider_MarkerSize_Moving.setEnabled(True)
            self.GUI.Slider_MarkerSize_Moving.valueChanged.connect(
                self.setMMarkerSize)

        elif which == "fixed":
            self.GUI.Slider_MarkerSize_Fixed.setEnabled(True)
            self.GUI.Slider_MarkerSize_Fixed.valueChanged.connect(
                self.setFMarkerSize)

    def setMMarkerSize(self):
        'Change size of landmarks in moving image'
        for m in self.LM_moving:
            m.setSize(self.GUI.Slider_MarkerSize_Moving.value()/2.0)

    def setFMarkerSize(self):
        for m in self.LM_fixed:
            m.setSize(self.GUI.Slider_MarkerSize_Fixed.value()/2.0)

    def updateTable(self, which):
        "update the table if the markers are moved"
        table = self.GUI.CoordsTable
        if which == "moving":
            for i in range(len(self.LM_moving)):
                table.item(i, 0).setText("{:.0f}, {:.0f}".format(
                    self.LM_moving[i].x, self.LM_moving[i].y))
        elif which == "fixed":
            for i in range(len(self.LM_fixed)):
                table.item(i, 1).setText("{:.0f}, {:.0f}".format(
                    self.LM_fixed[i].x, self.LM_fixed[i].y))
