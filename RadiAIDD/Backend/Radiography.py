# -*- coding: utf-8 -*-
"""
Created on Thu Jun 10 11:18:37 2021

@author: johan
"""

import logging
import numpy as np

from PyQt5.QtWidgets import QMessageBox as QMessage

from RadiAIDD.Backend.Containers import Crosshair
from RadiAIDD.Backend.Children import IsoCenter_Child as IsoCenter
# from Backend.Children import Landmark_Child as Landmark


class Radiography(object):
    def __init__(self, GUI, Checklist):

        self.GUI = GUI
        self.Checklist = Checklist

        try:
            # Patient Positioning holds information about positioning
            # of patient in CT
            self.PatientPosition = []

            # Crosshairs (two because two radiography images)
            self.Crosshair_Landmark = [Crosshair(), Crosshair()]
            self.Crosshair_Target = [Crosshair(), Crosshair()]

            # Three isocenter crosshairs for active positioning
            self.Crosshair_IsoCenter = [Crosshair(), Crosshair(),
                                        Crosshair(), Crosshair()]

            # Flags for visibility SpotTxt_x
            self.crosshair = False
            self.landmark = False
            self.target = False
            self.pixelsizeXR = None
            self.pixelsizeRG = None

            # Image data/Target coordiante containers
            # self.Radiography_scatter = Lynx()

            # RADIOGRAPHY RELATED Buttons
            self.GUI.Button_RG_defineIsoCenter.clicked.connect(self.define_isocenter)
            # self.GUI.Button_RadiographyLM.clicked.connect(self.define_landmarks)

            # toggle visibility of isocenter crosshair in Radiography
            self.GUI.Button_Radiograph_toggleIso.clicked.connect(self.toggleIso)

            # toggle visibility of landmark lines in Radiography
            self.GUI.Button_toggleLandmarksRG.clicked.connect(self.toggleLM)

            logging.info('Radiography class successfully initialized')

        except Exception:
            logging.error('Radiography class could not be initialized')

    def define_isocenter(self):
        "start pipeline in open child window within which isocenter is defined"

        if self.Checklist.IsoCenter:
            # If Landmarks were determined previously:
            Hint = QMessage()
            Hint.setIcon(QMessage.Information)
            Hint.setStandardButtons(QMessage.Ok | QMessage.Cancel)
            Hint.setText("Loading new Radiography will remove Isocenter "
                         "Definition. \n Proceed?")
            proceed = Hint.exec_()
            if proceed == QMessage.Ok:
                [crosshair.wipe for crosshair in self.Crosshair_IsoCenter]
                self.GUI.Text_RG_Filename_IsoCenter.setText('')
                self.GUI.SpotTxt_x.setText('')
                self.GUI.SpotTxt_y.setText('')
                self.GUI.Display_Isocenter.canvas.axes.imshow([[0], [0]])
                self.GUI.Display_Isocenter.canvas.draw()
                self.Checklist.IsoCenter = False
            else:
                return 0

        # set state down just to be sure here
        self.GUI.IsoCenterState.flag_down()

        self.isocenter_window = IsoCenter(self.GUI, self)
        self.isocenter_window.show()

    # def define_landmarks(self):
    #     "start pipeline in open child window within which isocenter is defined"

    #     if self.Checklist.LandmarkRG:
    #         # If Landmarks were determined previously:
    #         Hint = QMessage()
    #         Hint.setIcon(QMessage.Information)
    #         Hint.setStandardButtons(QMessage.Ok | QMessage.Cancel)
    #         Hint.setText("Loading new Radiography will remove "
    #                      "Landmark Definition. \n Proceed?")
    #         proceed = Hint.exec_()
    #         if proceed == QMessage.Ok:
    #             # Remove all Landmark-related values/flags
    #             [crosshair.wipe for crosshair in self.Crosshair_Landmark]
    #             self.GUI.Text_RG_Filename_Landmark.setText('')
    #             self.GUI.TxtRGPinX.setText('')
    #             self.GUI.TxtRGPinY.setText('')
    #             self.GUI.TxtRGShiftX.setText('')
    #             self.GUI.TxtRGShiftY.setText('')
    #             self.GUI.TxtRG_pxcalc.setText('Pixel Spacing:')
    #             self.GUI.Display_Radiography.canvas.axes.imshow([[0], [0]])
    #             self.GUI.Display_Radiography.canvas.draw()
    #             self.Checklist.LandmarkRG = False
    #         else:
    #             return 0

    #     "start pipeline in child window within which landmarks are defined"
    #     self.landmark_window = Landmark(self.GUI, self)
    #     self.landmark_window.show()

    def CalcDist(self):

        # DEPRECATED?
        " Calculate actual shift between target and isocenter"
        # if not all values are set: do nothing
        if not self.Checklist.ready():
            return 0

#        TxtRGShiftX

        # Get current coordinates of moving tables
        x_table = float(self.GUI.TableTxt_x.text())
        y_table = float(self.GUI.TableTxt_y.text())

        # Get coordinates from repositioning
        x_repo = float(self.GUI.LCD_shift_x.value())
        y_repo = float(self.GUI.LCD_shift_y.value())

        # get coordinates of isocenter (relative to earpin)
        x_iso = float(self.GUI.TxtRGShiftX.text())
        y_iso = float(self.GUI.TxtRGShiftY.text())

        # get coordinates of target (relative to earpin)
        x_target = float(self.GUI.TxtXRShiftX.text())
        y_target = float(self.GUI.TxtXRShiftY.text())

        # Caution: Head first supine and feet first prone positions have
        # inverted dorsal-ventral and inferior-superior axes!!!
        if self.PatientPosition == 'HFS':
            # (-1) because x/y-coordiantes are inverse in table/CT coordinates
            target2iso_x = (-1.0)*(x_iso - x_target) + x_table + x_repo
            target2iso_y = (-1.0)*(y_iso - y_target) + y_table + y_repo

            # Write to text field
            self.GUI.TableTxt_xCorr.setText('{:4.2f}'.format(target2iso_x))
            self.GUI.TableTxt_yCorr.setText('{:4.2f}'.format(target2iso_y))

        elif self.PatientPosition == 'FFP':
            target2iso_x = x_table + (x_iso - x_target) + x_repo
            target2iso_y = y_table + (y_iso - y_target) + y_repo

            # Write to text field
            self.GUI.TableTxt_xCorr.setText('{:4.2f}'.format(target2iso_x))
            self.GUI.TableTxt_yCorr.setText('{:4.2f}'.format(target2iso_y))
        else:  # if other positionings were used:
            self.GUI.TableTxt_xCorr.setText('Unknown Pat. Positioning')
            self.GUI.TableTxt_yCorr.setText('Unknown Pat. Positioning')
            return 0

        # Highlight result
        self.GUI.Group_Result.setStyleSheet(".QGroupBox { border: 2px solid "
                                       "rgb(0,0,255);}")
        self.GUI.TableTxt_xCorr.setStyleSheet("color: #b1b1b1; font-weight: bold;")
        self.GUI.TableTxt_yCorr.setStyleSheet("color: #b1b1b1; font-weight: bold;")

    def return_spacing(self, Spacing):
        " Function to be invoked from landmark child to pass spacing values"

        # Calculate RG pixel spacing from bed top/bottom coordinates
        self.pixelsizeRG = Spacing

        # print to field and pass result to Radiography instance
        self.GUI.TxtRG_pxcalc.setText('Pixel Spacing: {:4.2f} mm'.format(
                self.pixelsizeRG))
        self.GUI.TxtRG_pxcalc.setStyleSheet("color: #b1b1b1;")

    def return_landmarks(self, Image, xy):
        """Function to be invoked from child
        window that serves Landmark definition by earpin"""

        # catch returned Image data
        self.LandmarkRG = Image
        x_lm = xy[0]
        y_lm = xy[1]

        # Set GUI fields
        self.GUI.TxtRGPinX.setText(str(x_lm))
        self.GUI.TxtRGPinY.setText(str(y_lm))
        self.GUI.TxtRGPinX.setStyleSheet("color: #b1b1b1;")
        self.GUI.TxtRGPinY.setStyleSheet("color: #b1b1b1;")
        self.GUI.Text_RG_Filename_Landmark.setText(self.LandmarkRG.filename)

        # Raise Flag in Checklist
        self.Checklist.LandmarkRG = True

        # Make image
        self.GUI.Display_Radiography.canvas.axes.imshow(self.LandmarkRG.array,
                                                   cmap='gray', zorder=1,
                                                   origin='lower')
        self.GUI.Display_Radiography.canvas.draw()
        canvases = [self.GUI.Display_Radiography.canvas,
                    self.GUI.Display_Isocenter.canvas]

        # Prepare crosshairs
        for crosshair in tuple(zip(self.Crosshair_Landmark, canvases)):
            crosshair[0].setup(crosshair[1], size=5, x=x_lm, y=y_lm,
                               text='Earpin', zorder=3,
                               color='red', circle=False)

        # If landmark and isocenter are provided,
        # calculate spatial shift in RG image
        if self.Checklist.IsoCenter and self.Checklist.LandmarkRG:
            pixperdistRG = self.pixelsizeRG

            # Get local representatives of necessary variables
            x_Iso = float(self.GUI.SpotTxt_x.text())
            y_Iso = float(self.GUI.SpotTxt_y.text())

            x_Pin = float(self.GUI.TxtRGPinX.text())
            y_Pin = float(self.GUI.TxtRGPinY.text())

            # Calculate shift
            dx = pixperdistRG*(x_Iso - x_Pin)
            dy = pixperdistRG*(y_Iso - y_Pin)

            self.GUI.TxtRGShiftX.setText('{:4.2f}'.format(dx))
            self.GUI.TxtRGShiftY.setText('{:4.2f}'.format(dy))

            if np.sqrt(dx**2 + dy**2) < 1.0:
                self.GUI.TxtRGShiftX.setStyleSheet("color: rgb(0, 255, 0);")
                self.GUI.TxtRGShiftY.setStyleSheet("color: rgb(0, 255, 0);")
            else:
                self.GUI.TxtRGShiftX.setStyleSheet("color: rgb(255, 0, 0);")
                self.GUI.TxtRGShiftY.setStyleSheet("color: rgb(255, 0, 0);")
            self.CalcDist()

    def return_isocenter(self, RadiographyImg, xy):
        """Function to be invoked from child window that passes IsoCenter
        coordinates to main window"""

        self.IsoCenterImg = RadiographyImg
        x_iso = xy[0]
        y_iso = xy[1]

        self.GUI.SpotTxt_x.setText('{:.3f}'.format(x_iso))
        self.GUI.SpotTxt_y.setText('{:.3f}'.format(y_iso))
        self.GUI.SpotTxt_x.setStyleSheet("color: #b1b1b1;")
        self.GUI.SpotTxt_y.setStyleSheet("color: #b1b1b1;")


        # Set checklist entry for IsoCenter True and try calculation
        self.Checklist.IsoCenter = True
        if self.Checklist.ready():
            self.CalcDist()

        # Display isocenter image, filename and enable crosshair on this image
        self.GUI.Display_Isocenter.canvas.axes.imshow(self.IsoCenterImg.array,
                                                 cmap='gray',
                                                 zorder=1, origin='lower')
        self.GUI.Display_Isocenter.canvas.draw()
        self.GUI.Text_RG_Filename_IsoCenter.setText(self.IsoCenterImg.filename)

        canvases = [self.GUI.Display_Radiography.canvas,
                    self.GUI.Display_Isocenter.canvas,
                    self.GUI.Display_Fixed.canvas,
                    self.GUI.Display_Fusion.canvas]

        # Prepare crosshairs
        for crosshair in tuple(zip(self.Crosshair_IsoCenter, canvases)):
            crosshair[0].setup(crosshair[1], size=5, x=x_iso, y=y_iso,
                               text='IsoCenter', zorder=3,
                               color='blue', circle=True)

        # Write this to statesign
        self.GUI.IsoCenterState.toggle()

    def toggleLM(self):
        for crosshair in self.Crosshair_Landmark:
            crosshair.toggle()

    def toggleIso(self):
        for crosshair in self.Crosshair_IsoCenter:
            crosshair.toggle()