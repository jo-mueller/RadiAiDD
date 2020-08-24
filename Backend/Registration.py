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
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QObject

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from scipy.optimize import minimize
from Backend.Containers import Crosshair

ccycle = plt.rcParams['axes.prop_cycle'].by_key()['color']


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
        self.point = patches.Circle((x, y), size, alpha=alpha,
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


class DisplayObject:
    def __init__(self, canvas, label):
        self.canvas = canvas
        self.Qlabel = label

        self.GUI = self.getGUI()

    def load_Image(self):
        fname, _ = Qfile.getOpenFileName(self.GUI, 'Open file',
                                         "", "(*.tif)")
        # If no file is chosen:
        if not fname:
            return 0

        self.array = tifffile.imread(fname)
        self.canvas.axes.imshow(self.array, cmap='gray')
        self.canvas.draw()
        self.Qlabel.setText(fname)

        # get values listed in table to be drawn on newly loaded figure

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

        self.GUI.Button_load_moving.clicked.connect(self.Moving.load_Image)
        self.GUI.Button_load_fixed.clicked.connect(self.Fixed.load_Image)

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

        self.default_moving = [[625, 518],
                               [592, 520],
                               [494, 540],
                               [635, 575],
                               [703, 565]]
        self.default_fixed = self.default_moving

        # Flags
        self.PointsOnCanvas_moving = False
        self.PointsOnCanvas_fixed = False
        self.ImageOnFusion = False

        self.TrfTrgPoint = None
        self.TrgRaw = None

        self.sliderconnected = False
        logging.info('Registration class successfully initialized')

    def calcMotor(self):
        'Calculates Motor target coordinates'
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
        y = y_Table + (-1) * (y_Iso - y_Target) * 0.05  # mm

        self.GUI.TableTxt_xCorr.setText("{:.2f}".format(x))
        self.GUI.TableTxt_yCorr.setText("{:.2f}".format(y))

    def setMotorOrigin(self):
        'Copies Motor origin to GUI'
        x = self.GUI.Box_MotorOriginX.value()
        y = self.GUI.Box_MotorOriginY.value()
        self.GUI.TableTxt_x.setText("{:.3f}".format(x))
        self.GUI.TableTxt_y.setText("{:.3f}".format(y))

    def getCurrentMotorPos(self):
        'Assumes currently set motor position as position of active RG image'
        x = float(self.GUI.TablePosX.text())
        y = float(self.GUI.TablePosY.text())
        self.GUI.Box_MotorOriginX.setValue(x)
        self.GUI.Box_MotorOriginY.setValue(y)

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

            except ValueError:
                continue

        # If a target already exists, remove old one
        if self.TrgRaw is not None:
            self.TrgRaw.toggle()
            del(self.TrgRaw)

        self.TrgRaw = DragPoint(self.GUI.Display_Moving, x=x, y=y,
                                transparent=True, size=30)
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
            logging.info("Missing data for registration.")
            return 0

        vA = [(P.x, P.y) for P in self.LM_fixed]
        vB = [(P.x, P.y) for P in self.LM_moving]

        initial_guess = [1.7, 0, 0, 0]
        options = {"maxiter": 3000}
        res = minimize(self.cost_function, initial_guess, args=(vA, vB),
                       method='SLSQP', options=options)
        logging.info("Similarity transform optimization result:")
        logging.info(res)

        # Transform and display warped image
        Warped = self.ImageTransform(self.Moving.get_array(), res.x)

        canvas = self.GUI.Display_Fusion.canvas
        canvas.axes.clear()
        canvas.axes.imshow(self.Fixed.get_array(), cmap='gray',
                           alpha=0.5, interpolation='nearest')
        canvas.axes.imshow(Warped, cmap='gray',
                           alpha=0.5, interpolation='nearest')
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
                                         transparent=True, size=30*res.x[0])
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

        # Which dataset? moving or fixed?
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
            for i in range(len(self.default_moving)):
                point = DragPoint(QObj, self.default_moving[i][0],
                                  self.default_moving[i][1],
                                  fc=ccycle[i % len(ccycle)],
                                  size=9)
                point.Signal.moving.connect(lambda: self.updateTable("fixed"))
                self.LM_fixed.append(point)
            self.PointsOnCanvas_fixed = True

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
