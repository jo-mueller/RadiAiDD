# -*- coding: utf-8 -*-

from Backend.Containers import RTstruct
from Backend.Containers import OverlayImage
from Backend.Containers import Check
from Backend.Containers import GrayWindow
from Backend.Containers import Crosshair

from Backend.Children import IsoCenter_Child as IsoCenter
from Backend.Children import Landmark_Child as Landmark
from Backend.UI.Positioning_Assistant_GUI5 import Ui_Mouse_Positioning_Interface
from Backend.Registration import Registration

import traceback
import ctypes
import glob
import serial
import configparser
import time
import logging
import sys
import os
import numpy as np

import pydicom as dicom
from datetime import datetime


from PyQt5 import QtGui
from PyQt5.QtWidgets import QMessageBox as QMessage
from PyQt5.QtWidgets import QApplication as Qapp
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QThreadPool
from PyQt5.QtCore import QRunnable
from PyQt5.QtCore import QObject
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QFileDialog as Qfile
from PyQt5.QtWidgets import QMainWindow as QMain
#    from PyQt5.QtWidgets import QWidget as QWid
from PyQt5.QtWidgets import QToolBar

import PyQt5.QtWidgets as QtWidgets
pyqt_version = 5


class Radiography(object):
    def __init__(self):

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
            GUI.Button_RG_defineIsoCenter.clicked.connect(self.define_isocenter)
            GUI.Button_RadiographyLM.clicked.connect(self.define_landmarks)

    #        toggle visibility of isocenter crosshair in Radiography
            GUI.Button_Radiograph_toggleIso.clicked.connect(self.toggleIso)

            # toggle visibility of landmark lines in Radiography
            GUI.Button_toggleLandmarksRG.clicked.connect(self.toggleLM)

            logging.info('Radiography class successfully initialized')

        except Exception:
            logging.error('Radiography class could not be initialized')

    def define_isocenter(self):
        "start pipeline in open child window within which isocenter is defined"

        if Checklist.IsoCenter:
            # If Landmarks were determined previously:
            Hint = QMessage()
            Hint.setIcon(QMessage.Information)
            Hint.setStandardButtons(QMessage.Ok | QMessage.Cancel)
            Hint.setText("Loading new Radiography will remove Isocenter "
                         "Definition. \n Proceed?")
            proceed = Hint.exec_()
            if proceed == QMessage.Ok:
                [crosshair.wipe for crosshair in self.Crosshair_IsoCenter]
                GUI.Text_RG_Filename_IsoCenter.setText('')
                GUI.SpotTxt_x.setText('')
                GUI.SpotTxt_y.setText('')
                GUI.TxtRGShiftX.setText('')
                GUI.TxtRGShiftY.setText('')
                GUI.TxtRG_pxcalc.setText('Pixel Spacing:')
                GUI.Display_Isocenter.canvas.axes.imshow([[0], [0]])
                GUI.Display_Isocenter.canvas.draw()
                Checklist.IsoCenter = False
            else:
                return 0

        self.isocenter_window = IsoCenter(GUI, self)
        self.isocenter_window.show()

    def define_landmarks(self):
        "start pipeline in open child window within which isocenter is defined"

        if Checklist.LandmarkRG:
            # If Landmarks were determined previously:
            Hint = QMessage()
            Hint.setIcon(QMessage.Information)
            Hint.setStandardButtons(QMessage.Ok | QMessage.Cancel)
            Hint.setText("Loading new Radiography will remove "
                         "Landmark Definition. \n Proceed?")
            proceed = Hint.exec_()
            if proceed == QMessage.Ok:
                # Remove all Landmark-related values/flags
                [crosshair.wipe for crosshair in self.Crosshair_Landmark]
                GUI.Text_RG_Filename_Landmark.setText('')
                GUI.TxtRGPinX.setText('')
                GUI.TxtRGPinY.setText('')
                GUI.TxtRGShiftX.setText('')
                GUI.TxtRGShiftY.setText('')
                GUI.TxtRG_pxcalc.setText('Pixel Spacing:')
                GUI.Display_Radiography.canvas.axes.imshow([[0], [0]])
                GUI.Display_Radiography.canvas.draw()
                Checklist.LandmarkRG = False
            else:
                return 0

        "start pipeline in child window within which landmarks are defined"
        self.landmark_window = Landmark(GUI, self)
        self.landmark_window.show()

    def CalcDist(self):

        # DEPRECATED?
        " Calculate actual shift between target and isocenter"
        # if not all values are set: do nothing
        if not Checklist.ready():
            return 0

#        TxtRGShiftX

        # Get current coordinates of moving tables
        x_table = float(GUI.TableTxt_x.text())
        y_table = float(GUI.TableTxt_y.text())

        # Get coordinates from repositioning
        x_repo = float(GUI.LCD_shift_x.value())
        y_repo = float(GUI.LCD_shift_y.value())

        # get coordinates of isocenter (relative to earpin)
        x_iso = float(GUI.TxtRGShiftX.text())
        y_iso = float(GUI.TxtRGShiftY.text())

        # get coordinates of target (relative to earpin)
        x_target = float(GUI.TxtXRShiftX.text())
        y_target = float(GUI.TxtXRShiftY.text())

        # Caution: Head first supine and feet first prone positions have
        # inverted dorsal-ventral and inferior-superior axes!!!
        if self.PatientPosition == 'HFS':
            # (-1) because x/y-coordiantes are inverse in table/CT coordinates
            target2iso_x = (-1.0)*(x_iso - x_target) + x_table + x_repo
            target2iso_y = (-1.0)*(y_iso - y_target) + y_table + y_repo

            # Write to text field
            GUI.TableTxt_xCorr.setText('{:4.2f}'.format(target2iso_x))
            GUI.TableTxt_yCorr.setText('{:4.2f}'.format(target2iso_y))

        elif self.PatientPosition == 'FFP':
            target2iso_x = x_table + (x_iso - x_target) + x_repo
            target2iso_y = y_table + (y_iso - y_target) + y_repo

            # Write to text field
            GUI.TableTxt_xCorr.setText('{:4.2f}'.format(target2iso_x))
            GUI.TableTxt_yCorr.setText('{:4.2f}'.format(target2iso_y))
        else:  # if other positionings were used:
            GUI.TableTxt_xCorr.setText('Unknown Pat. Positioning')
            GUI.TableTxt_yCorr.setText('Unknown Pat. Positioning')
            return 0

        # Highlight result
        GUI.Group_Result.setStyleSheet(".QGroupBox { border: 2px solid "
                                       "rgb(0,0,255);}")
        GUI.TableTxt_xCorr.setStyleSheet("color: #b1b1b1; font-weight: bold;")
        GUI.TableTxt_yCorr.setStyleSheet("color: #b1b1b1; font-weight: bold;")

    def return_spacing(self, Spacing):
        " Function to be invoked from landmark child to pass spacing values"

        # Calculate RG pixel spacing from bed top/bottom coordinates
        self.pixelsizeRG = Spacing

        # print to field and pass result to Radiography instance
        GUI.TxtRG_pxcalc.setText('Pixel Spacing: {:4.2f} mm'.format(
            self.pixelsizeRG))
        GUI.TxtRG_pxcalc.setStyleSheet("color: #b1b1b1;")

    def return_landmarks(self, Image, xy):
        """Function to be invoked from child
        window that serves Landmark definition by earpin"""

        # catch returned Image data
        self.LandmarkRG = Image
        x_lm = xy[0]
        y_lm = xy[1]

        # Set GUI fields
        GUI.TxtRGPinX.setText(str(x_lm))
        GUI.TxtRGPinY.setText(str(y_lm))
        GUI.TxtRGPinX.setStyleSheet("color: #b1b1b1;")
        GUI.TxtRGPinY.setStyleSheet("color: #b1b1b1;")
        GUI.Text_RG_Filename_Landmark.setText(self.LandmarkRG.filename)

        # Raise Flag in Checklist
        Checklist.LandmarkRG = True

        # Make image
        GUI.Display_Radiography.canvas.axes.imshow(self.LandmarkRG.array,
                                                   cmap='gray', zorder=1,
                                                   origin='lower')
        GUI.Display_Radiography.canvas.draw()
        canvases = [GUI.Display_Radiography.canvas,
                    GUI.Display_Isocenter.canvas]

        # Prepare crosshairs
        for crosshair in tuple(zip(self.Crosshair_Landmark, canvases)):
            crosshair[0].setup(crosshair[1], size=5, x=x_lm, y=y_lm,
                               text='Earpin', zorder=3,
                               color='red', circle=False)

        # If landmark and isocenter are provided,
        # calculate spatial shift in RG image
        if Checklist.IsoCenter and Checklist.LandmarkRG:
            pixperdistRG = self.pixelsizeRG

            # Get local representatives of necessary variables
            x_Iso = float(GUI.SpotTxt_x.text())
            y_Iso = float(GUI.SpotTxt_y.text())

            x_Pin = float(GUI.TxtRGPinX.text())
            y_Pin = float(GUI.TxtRGPinY.text())

            # Calculate shift
            dx = pixperdistRG*(x_Iso - x_Pin)
            dy = pixperdistRG*(y_Iso - y_Pin)

            GUI.TxtRGShiftX.setText('{:4.2f}'.format(dx))
            GUI.TxtRGShiftY.setText('{:4.2f}'.format(dy))

            if np.sqrt(dx**2 + dy**2) < 1.0:
                GUI.TxtRGShiftX.setStyleSheet("color: rgb(0, 255, 0);")
                GUI.TxtRGShiftY.setStyleSheet("color: rgb(0, 255, 0);")
            else:
                GUI.TxtRGShiftX.setStyleSheet("color: rgb(255, 0, 0);")
                GUI.TxtRGShiftY.setStyleSheet("color: rgb(255, 0, 0);")
            self.CalcDist()

    def return_isocenter(self, RadiographyImg, xy):
        """Function to be invoked from child window that passes IsoCenter
        coordinates to main window"""

        self.IsoCenterImg = RadiographyImg
        x_iso = xy[0]
        y_iso = xy[1]

        GUI.SpotTxt_x.setText('{:.3f}'.format(x_iso))
        GUI.SpotTxt_y.setText('{:.3f}'.format(y_iso))
        GUI.SpotTxt_x.setStyleSheet("color: #b1b1b1;")
        GUI.SpotTxt_y.setStyleSheet("color: #b1b1b1;")

        # Set checklist entry for IsoCenter True and try calculation
        Checklist.IsoCenter = True
        if Checklist.ready():
            self.CalcDist()

        # Display isocenter image, filename and enable crosshair on this image
        GUI.Display_Isocenter.canvas.axes.imshow(self.IsoCenterImg.array,
                                                 cmap='gray',
                                                 zorder=1, origin='lower')
        GUI.Display_Isocenter.canvas.draw()
        GUI.Text_RG_Filename_IsoCenter.setText(self.IsoCenterImg.filename)

        canvases = [GUI.Display_Radiography.canvas,
                    GUI.Display_Isocenter.canvas,
                    GUI.Display_Fixed.canvas,
                    GUI.Display_Fusion.canvas]

        # Prepare crosshairs
        for crosshair in tuple(zip(self.Crosshair_IsoCenter, canvases)):
            crosshair[0].setup(crosshair[1], size=5, x=x_iso, y=y_iso,
                               text='IsoCenter', zorder=3,
                               color='blue', circle=True)

    def toggleLM(self):
        for crosshair in self.Crosshair_Landmark:
            crosshair.toggle()

    def toggleIso(self):
        for crosshair in self.Crosshair_IsoCenter:
            crosshair.toggle()


class Signals(QObject):

    # emit position as float
    travelling = pyqtSignal(np.ndarray)
    arrived = pyqtSignal()
    calibrated = pyqtSignal(bool)
    State = pyqtSignal(np.ndarray)


class StatusWatchdog(QRunnable):
    """This thread is continuosly running in the background of the GUI and
        checks the state of the object table. Needs:
        -- Motor: Handle of the Serial control instance that talks with the
        respective axis
            """

    def __init__(self, Motor):
        super(StatusWatchdog, self).__init__()

        self.Motor = Motor
        self._isRunning = True
        self._pause = False

        # shortcut to Bus IDs
        self.MID = Motor.MasterID
        self.SID = Motor.SlaveID

        # create Message to be emitted
        self.StatusAll = np.ndarray(3, dtype=bool)
        self.StatusAll[:] = False
        self.Signal = Signals()

        logging.debug('Table Status WatchDog initialized')

    @pyqtSlot()
    def run(self):

        logging.info('Table Status WatchDog awake')
        # am I running?
        if not self._isRunning:
            self._isRunning = True

        # actual routine
        while self._isRunning:

            # add additional loop for pause of loop
            while self._pause:
                time.sleep(0.1)

            # check for serial connection
            self.StatusAll[0] = self.Motor.ctrl.is_open

            # Then, check for Motor readiness
            try:
                State_Master = self.Motor.serial_query(self.MID, 1, 'ASTAT')
                State_Slave  = self.Motor.serial_query(self.SID, 1, 'ASTAT')

                if State_Master == 'R\r' and State_Slave == 'R\r':
                    self.StatusAll[1] = True
                elif State_Master == 0 or State_Slave == 0:
                    self.StatusAll[1] = False
            except Exception:
                logging.debug(traceback.print_exc())
                self.StatusAll[1] = False

            # Lastly, check for reference status
            try:
                State_Ref_M = Motor.serial_query(self.MID, 1, 'REFST')
                State_Ref_S = Motor.serial_query(self.SID, 1, 'REFST')

                if State_Ref_M == '1\r' and State_Ref_S == '1\r':
                    self.StatusAll[2] = True
                elif State_Ref_M == 0 or State_Ref_S == 0:
                    self.StatusAll[2] = False
            except Exception:
                self.StatusAll[2] = False

            # Emit collected values
            self.Signal.State.emit(self.StatusAll)
            time.sleep(5) # sleep 5 seconds

    def Stop(self):
        # Function to halt the WatchDog
        self._isRunning = False

    def Pause(self):
        # Function to temporarily halt the run function
        self._pause = True

    def Continue(self):
        # Function to continue WatchDog activity
        time.sleep(1)
        self._pause = False


class MovementSupervisor(QRunnable):
    """This thread allows to supervise motor movement without halting the GUI
        while doing this. Needs:
        -- Motor: Handle to the Serial control instance that talks with the
            respective axis
        """

    def __init__(self, Motor):
        super(MovementSupervisor, self).__init__()
        self.Motor = Motor
        self._isRunning = True

        # shortcut to Bus IDs
        self.MID = Motor.MasterID
        self.SID = Motor.SlaveID

        self.Signal = Signals()

    @pyqtSlot()
    def run(self, mode='normal'):
        """
        Routine that is executed while the thread is running
        - mode: if mode is not normal, then it's probably a reference run
        """

        logging.debug('Table is moving: Movement WatchDog awake')
        # is the thread currently running? Not sure if this is necessary
        if not self._isRunning:
            self._isRunning = True

        # actual routine
        while self._isRunning:
            time.sleep(0.5)

            self.pos = self.Motor.get_Position()
            self.Signal.travelling.emit(self.pos)

            # get state of motor
            self.MState = Motor.serial_query(self.MID, 1, 'ASTATE')[0]
            self.SState = Motor.serial_query(self.SID, 1, 'ASTATE')[0]

            # If Motor has arrived, emit stop sign
            if self.MState == 'R' and self.SState == 'R':
                time.sleep(.5)  # wait one second for fine positioning
                self.pos = Motor.get_Position()

                # Emit signals
                self.Signal.travelling.emit(self.pos)
                time.sleep(.5)  # wait +1 second until WatchDog is let off the leash
                self.Signal.arrived.emit()
                logging.debug('Destination reached: Movement WatchDog asleep')
                self._isRunning = False
                break

    def stop(self):
        "Terminates the thread"
        self._isRunning = False


class MotorControl(object):
    """ This class holds holds all basic functionality to control the
        motorized linear axes. """

    def __init__(self):

        # Variables
        self.pos = []  # Unit: mm
        self.Step2MM = 10000.0

        # IDs of PS10 elements in bus
        self.MasterID = None
        self.SlaveID = None

        self.ctrl = serial.Serial()

        # Set default logging of serial communication to false
        self.verbose = False

        # State indicators
        self.COMstate = StateSign(GUI.BoxTableCOM,
                                  GUI.LabelCOM,
                                  ['Disconnected', 'Connected'])
        self.MOTORstate = StateSign(GUI.BoxTableInit,
                                    GUI.LabelINIT,
                                    ['Not ready', 'Ready'])
        self.CALIBstate = StateSign(GUI.BoxTableLimits,
                                    GUI.LabelREF,
                                    ['Calibrated', 'Uncalibrated'])

        # First: Find available COM ports and add to ComboBox
        self.ScanCOMPorts()
        GUI.action_scan_COM_ports.triggered.connect(self.ScanCOMPorts)

        # Set up Combo box for positioning mode and connect
        GUI.CBoxABSREL.addItem('absolute')
        GUI.CBoxABSREL.addItem('relative')
        GUI.CBoxABSREL.currentIndexChanged.connect(self.setPositioningMode)

        # Connect buttons
        GUI.Button_MotorInit.clicked.connect(self.InitMotor)
        GUI.Button_MoveTable.clicked.connect(self.moveTable)
        GUI.ButtonCopyCoordinates.clicked.connect(self.CopyCoordinates)

        # Thread Control
        self.threadpool = QThreadPool()
        self.WatchState()

        # Log
        logging.debug('Motor functionality set up successfully')

    def ScanCOMPorts(self):
        """Scans list of COM ports and adds to List of Ports in GUI"""
        portlist = self.get_serial_ports()
        GUI.QComboBox_ListOfPorts.clear()
        for port in portlist:
            GUI.QComboBox_ListOfPorts.addItem(port)

        if len(portlist) == 0:
            logging.info(('No open ports found. Axes may be disconnected or ' +
                          'used by another software (e.g. OWISOFT)'))

    def moveTable(self):
        """
        Basic executer function to move table by/to selected value
        """

        # Nothing happens if motor isn't ready.
        if not self.MOTORstate:
            return 0

        try:
            val = np.array((GUI.SpinBoxTablex.value(),
                            GUI.SpinBoxTabley.value()))

            # get current position
            curpos = self.get_Position()

            # calculate destination depending on positioning mode
            mode = GUI.CBoxABSREL.currentText()

            if mode == 'absolute':
                dest = val
            elif mode == 'relative':
                dest = curpos + val

            # convert to motor steps
            val = self.Step2MM * val  # convert to motor steps

            # maximum/minimum value check
            if not 0 <= dest[0] <= 80.0*self.Step2MM and 0<= dest[1] <=80.0*self.Step2MM:
                # Ask User if calibration is desired
                Hint = QMessage()
                Hint.setIcon(QMessage.Warning)
                Hint.setStandardButtons(QMessage.Ok)
                Hint.setText("Destination outside of axis limits!")
                Hint.exec_()
                return -1

            # write to Axis
            self.serial_write(self.MasterID, 1, 'PSET', val[1])  # Watch out here: Depends on cable connections!!!!
            self.serial_write(self.SlaveID,  1, 'PSET', val[0])  # Watch out here: Depends on cable connections!!!!
            self.serial_write(self.MasterID, 1, 'PGO')
            self.serial_write(self.SlaveID,  1, 'PGO')

            # check this again - are these values correct or LR-inverted?
            if mode == "absolute":
                logging.info('Moving table to coordinates: x = {:.2f} '
                             'y = {:.2f}'.format(val[0], val[1]))
            else:
                logging.info('Moving table by: dx = {:.2f} '
                             'dy = {:.2f}'.format(val[0], val[1]))

            self.WatchMovement()

        except Exception:
            logging.debug(traceback.print_exc())


    def get_Position(self):
        " get current position of selected axis via USB"

        # Watch out here: y@ Master and x@SLave!
        # may be different in other beamtimes!!!
        y = float(self.serial_query(self.MasterID, 1, 'CNT'))/self.Step2MM
        x = float(self.serial_query(self.SlaveID,  1, 'CNT'))/self.Step2MM

        return np.array((x, y))

    def CopyCoordinates(self):
        "Copies calculated irradiation coordinates to respective field"
        x = float(GUI.TableTxt_xCorr.text())
        y = float(GUI.TableTxt_yCorr.text())

        GUI.SpinBoxTablex.setValue(x)
        GUI.SpinBoxTabley.setValue(y)

        # Log
        logging.info('Coppied destination coordinates x = {:.2f}, y = {:.2f}'
                     .format(x, y))

    def setPositioningMode(self):
        """When Mode in absolute/relative combo box changes, write to motor"""

        # get text from Combo Box
        mode = GUI.CBoxABSREL.currentText()
        if self.MOTORstate.state is False:
            logging.info('No Motor connected. '
                         'Mode will be applied to next connected device.')

        if mode == 'absolute':
            self.serial_write(self.MasterID, 1, 'ABSOL')
            self.serial_write(self.SlaveID,  1, 'ABSOL')
            logging.info('Positioning mode: absolute')
        elif mode == 'relative':
            self.serial_write(self.MasterID, 1, 'RELAT')
            self.serial_write(self.SlaveID, 1, 'RELAT')
            logging.info('Positioning mode: relative')

    # Thread Control for Movement Control
    def WatchMovement(self):
        " Execute this whenever tables are moved"

        self.MotorWatch = MovementSupervisor(self)
        self.MotorWatch.Signal.travelling.connect(self.update_position)
        self.MotorWatch.Signal.travelling.connect(self.StatusWatchDog.Pause)
        self.MotorWatch.Signal.arrived.connect(self.StatusWatchDog.Continue)
        GUI.Button_StopTable.clicked.connect(
            lambda: self.StopMovement(self.MotorWatch))
        self.StatusWatchDog.Pause()

        self.threadpool.start(self.MotorWatch)

    def StopMovement(self, Instance):
        "Function to stop ax from moving and will stop WatchDog"

        self.serial_write(self.MasterID, 1, 'STOP')
        self.serial_write(self.SlaveID,  1, 'STOP')
        Instance.stop()

    def WatchState(self):
        "permanent background thread for table state supervision"

        self.StatusWatchDog = StatusWatchdog(self)
        self.StatusWatchDog.Signal.State.connect(self.update_state)

        self.threadpool.start(self.StatusWatchDog)

    def update_state(self, State):
        "Passes State from WatchDog to GUI"

        if State[0]:
            self.COMstate.flag_up()
        else:
            self.COMstate.flag_down()

        if State[1]:
            self.MOTORstate.flag_up()
        else:
            self.MOTORstate.flag_down()

        if State[2]:
            self.CALIBstate.flag_up()
        else:
            self.CALIBstate.flag_down()

    def update_position(self, pos):
        "Can be called from thread to update position in GUI and internally"

        # save value in ownb class
        self.pos = pos

        # write to GUI
        GUI.TablePosX.setText(str(pos[0]))
        GUI.TablePosY.setText(str(pos[1]))

    # Initialization
    def InitMotor(self):
        """
        function that executes everything that is necessary to initialize
        the motor
        """

        # Before first: Pause Status WatchDog
        self.StatusWatchDog.Pause()

        # First: Init COM
        port = GUI.QComboBox_ListOfPorts.currentText()
        self.InitializeCOM(port)

        # disable boxes for port selection and connect button
        if self.COMstate.state:
            logging.info('Port {:s} ready for serial communication.'
                         .format(port))
            GUI.QComboBox_ListOfPorts.setEnabled(False)
            GUI.Button_MotorInit.setEnabled(False)
        else:
            logging.error('No serial communication with selected port.')
            return -1

        # Find Slaves
        self.find_slaves(10)

        # Next: set all motorvalues
        self.config_motor(self.MasterID)
        self.config_motor(self.SlaveID)

        # Next: Init Motor
        self.serial_write(self.MasterID, 1, 'INIT')
        self.serial_write(self.SlaveID,  1, 'INIT')
        State_Master = self.serial_query(self.MasterID, 1, 'ASTAT')
        State_Slave = self.serial_query(self.SlaveID,  1, 'ASTAT')
        logging.debug('Motor init terminated with state {:s} @ Master/{:s} @Slave'.format(State_Master, State_Slave))

        # Status checken und calib starten.
        if State_Master.startswith('R') and State_Slave.startswith('R'):
            logging.info('INFO: Motor successfully initialized.')
            self.setPositioningMode()  # read current setting, write to motor
            self.MOTORstate.flag_up()

            # When Motor ready: calibrate
            self.Calibrate_Motor()
            self.CALIBstate.flag_up()

        else:
            logging.error('Motor could not be initialized')

    def Calibrate_Motor(self):
        """execute reference run of object table"""

        # Ask User if calibration is desired
        Hint = QMessage()
        Hint.setIcon(QMessage.Information)
        Hint.setStandardButtons(QMessage.Ok)
        Hint.setText("Kalibrierung wird jetzt durchgeführt!")
        proceed = Hint.exec_()

        # Execute Calib
        if proceed == QMessage.Ok:
            self.serial_write(self.MasterID, 1, 'REF', 4)
            self.serial_write(self.SlaveID, 1, 'REF', 4)
            self.WatchMovement()  # start the thread for reference run
        logging.info('Table calibration running.')

    def on_calib(self, flag):
        "gets called when reference motion is finished"
        if flag is True:
            GUI.BoxTableLimits.setStyleSheet("background-color: green;")
            GUI.LabelREF.setText('Calibrated')

    # basic communication stuff
    def serial_write(self, slaveID, nAxis, command, value=''):
        """ will format and send the given command through the COM port.
            -- command: serial command to be sent.
        """

        # write request to COM
        if value == '':
            command = ("{:02d}{:s}{:d}\r\n".format(slaveID, command, nAxis))
        else:
            command = ("{:02d}{:s}{:d}={:s}\r\n"
                       .format(slaveID, command, nAxis, str(value)))

        command = command.encode(encoding="ASCII")
        if self.verbose:
            logging.debug(command)
        self.ctrl.write(command)

        # Read answer from COM and print full command  + reply
        asw = (self.ctrl.read(1024)).decode()

        return asw


    def serial_query(self, slaveID, nAxis, request):
        """ will format and send the given query through the COM port.
            -- command: serial command to be sent.
        """

        if slaveID is None or nAxis is None:
            return 0

        # write request to COM
        request =  ("{:02d}?{:s}{:d}\r\n".format(slaveID, request, nAxis))
        request = request.encode(encoding="ASCII")
        if self.verbose: logging.debug(request)
        self.ctrl.write(request)

        # Read answer from COM and return
        asw = (self.ctrl.read(1024)).decode()
        return asw


    def config_motor(self, slaveID, filename = os.path.join(os.getcwd(), 'Backend\\OWIS\\owis.ini')):
        """configures motor parameters of owis axis based oon data in given
            .ini file
            -- filename: full path of .ini containing necessary information
            -- slaveID: slaveID of motor the settings of which should be written
            """


        if not os.path.isfile(filename):
            logging.error('Motor config file {:s} not found'.format(filename))
            return -1


        # read config file
        config = configparser.RawConfigParser()
        config.read(filename)

        logging.debug('Configuring Motor Parameters for Slave ID {:s}'.format(slaveID))

        #write values to axis
        self.serial_write(slaveID, 1, 'SMK',       config.get('MOTOR', 'SMK'))
        self.serial_write(slaveID, 1, 'SMK',       config.get('MOTOR', 'SMK'))
        self.serial_write(slaveID, 1, 'SPL',       config.get('MOTOR', 'SPL'))
        self.serial_write(slaveID, 1, 'RMK',       config.get('MOTOR', 'RMK'))
        self.serial_write(slaveID, 1, 'RPL',       config.get('MOTOR', 'RPL'))
        self.serial_write(slaveID, 1, 'RVELF',     config.get('MOTOR', 'RVELF'))
        self.serial_write(slaveID, 1, 'RVELS',     config.get('MOTOR', 'RVELS'))
        self.serial_write(slaveID, 1, 'ACC',       config.get('MOTOR', 'ACC'))
        self.serial_write(slaveID, 1, 'PVEL',      config.get('MOTOR', 'PVEL'))
        self.serial_write(slaveID, 1, 'FVEL',      config.get('MOTOR', 'FVEL'))
        self.serial_write(slaveID, 1, 'PHINTIM',   config.get('MOTOR', 'PHINTIM'))
        self.serial_write(slaveID, 1, 'MCSTP',     config.get('MOTOR', 'MCSTP'))
        self.serial_write(slaveID, 1, 'DRICUR',    config.get('MOTOR', 'DRICUR'))
        self.serial_write(slaveID, 1, 'HOLCUR',    config.get('MOTOR', 'HOLCUR'))
        self.serial_write(slaveID, 1, 'ATOT',      config.get('MOTOR', 'ATOT'))
        self.serial_write(slaveID, 1, 'MOTYPE',    config.get('MOTOR', 'MOTYPE'))
        self.serial_write(slaveID, 1, 'MAXOUT',    config.get('MOTOR', 'MAXOUT'))
        self.serial_write(slaveID, 1, 'AMPSHNT',   config.get('MOTOR', 'AMPSHNT'))
        self.serial_write(slaveID, 1, 'AMPPWMF',   config.get('MOTOR', 'AMPPWMF'))
        self.serial_write(slaveID, 1, 'ABSOL')  # default setting: absolute positioning

        logging.debug('Done')

    def find_slaves(self, Range):
        """sends a testmessage to all slaves in range 0 to Range and listens
            for an answer. """

        logging.debug('Scanning Master/Slave structure...')
        self.MasterID = 0  # MasterID is always 00 - right?
        # check if serial port is open
        if not self.ctrl.is_open:
            return -1

        # Otherwise, browse all slaveIDs in given range
        for I in range(1, Range):
            asw = self.serial_query(I, 1, 'ASTAT') # request status
            time.sleep(1)

            # check if an answer came
            if asw == '':
                if I == Range -1:
                    # If maximum number of IDs have been checked, throw error
                    logging.error('No Master/Slave structure found')
                    return -1
                else:
                    continue

            # If reply comes:
            else:
                # break loop
                self.SlaveID = I
                logging.debug('Found Slave at ID={:d}'.format(I))
                break

        try:
            self.StatusWatchDog.MID = self.MasterID
            self.StatusWatchDog.SID = self.SlaveID
        except Exception:
            pass



    def get_serial_ports(self):

        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
                A list of the serial ports available on the system
        """

        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result


    def InitializeCOM(self, port, baudrate = 9600, bytesize = serial.EIGHTBITS,
                      parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                      rtscts=False, xonxoff=True, timeout=0.05, writeTimeout=0.05):

        """Function to initialize the serial communication
            - port: Set COM-Port that is connected to the OWIS components
            - all other necessary parameters are default parameters
        """
        logging.debug('Trying to open serial connection.')
        self.ctrl.port          = port
        self.ctrl.baudrate      = baudrate
        self.ctrl.bytesize      = bytesize
        self.ctrl.parity        = parity
        self.ctrl.stopbits      = stopbits
        self.ctrl.rtscts        = rtscts
        self.ctrl.xonxoff       = xonxoff
        self.ctrl.timeout       = timeout
        self.ctrl.writeTimeout  = writeTimeout

        try:
            self.ctrl.open()
            self.COMstate.flag_up()
        except Exception:
            logging.error('No serial connection could be openend with selected port!')
            return -1

class StateSign(MotorControl):
    def __init__(self, QFrame, QText, TextStates):
        """
        var QObj: text label object for status display
        var TextStates: array (len 2) with labels for display in treu/false state
        """

        self.QFrame = QFrame
        self.QText = QText
        self.TextStates = TextStates
        self.state = False

    def flag_down(self):
        self.QText.setText(self.TextStates[0])
        self.QFrame.setStyleSheet( "background-color: red;")
        self.state = False

    def flag_up(self):
        self.QText.setText(self.TextStates[1])
        self.QFrame.setStyleSheet( "background-color: green;")
        self.state = True

    def toggle(self):
        "changes the state from one to another"
        if self.flag == True:
            self.flag_down()
        else:
            self.flag_up()



class XRay(object):
    """Class that holds all X-Ray related functionality (e.g. Plan data,
    Plan/treatment-derived Planar scan-based repositioning, etc.)"""
    def __init__(self):

        print('INIT: Setting up X-Ray functionality...', end = '')
        try:
            # Assign buttons etc
            # load RT struct instead
            GUI.Button_LoadRTstruct.clicked.connect(self.loadRTstruct)

            # Load X-Rays of planar scans
            GUI.Button_Load_Plan.clicked.connect(self.loadPlanarXRay_Plan)
            GUI.Button_Load_Treatment.clicked.connect(self.loadPlanarXRay_Treat)

            # Accept or clear repositioning
            GUI.Button_Accept_Repositioning.clicked.connect(self.accept_repo)
            GUI.Button_WipePositioning.clicked.connect(self.wipe_positioning)

            # Assign containers
            self.StructureSet = RTstruct()
            self.Planar_Scans = OverlayImage()
            self.PatientPosition = []
            self.Crosshair_Target = Crosshair()
            self.Crosshair_Repo = Crosshair()
            self.Mousepath = ""
            self.UID_CT = ""
            self.UID_RTstruct = ""
            self.UID_treat = ""
            self.UID_plan = ""

            GUI.Display_Plan_Hist.findChild(QToolBar).setVisible(False)
            GUI.Display_Plan.findChild(QToolBar).setVisible(False)
            GUI.Display_Treatment_Hist.findChild(QToolBar).setVisible(False)
            GUI.Display_Treatment.findChild(QToolBar).setVisible(False)
            GUI.Display_Overlay_Hist.findChild(QToolBar).setVisible(False)
            GUI.Display_Overlay_Hist.findChild(QToolBar).setVisible(False)
            GUI.Display_Difference_Hist.findChild(QToolBar).setVisible(False)
            GUI.Display_FalseColor.findChild(QToolBar).setVisible(True)

            print('Successfull')
        except Exception:
            print('Failed')

    def isRTorDCM(self, path):
        """Check nature of given filename"""
        # Try to read the file with dicomreader; if it fails, it's not dicom
        try:
            meta = dicom.read_file(path)
        except Exception:
            return 0

        # Check if specific flags are found in dcm file
        if meta.Modality == 'RTSTRUCT':
            return 1
        elif meta.Modality == 'CT':
            return 2


    def loadRTstruct(self):
        try:
            "loads the RTstructure sets for Target and Earpin"

            RTflag  = False
            DCMflag = False

            #Get directory containing CT data: Then get filelist
            self.Mousepath = Qfile.getExistingDirectory(GUI, 'Open file', '\home\muellerjo')

            # Check if path was selected
            if not self.Mousepath:
                return 0
            else:
                #get filelist in specified directory (no directories)
                filelist = [f for f in os.listdir(self.Mousepath) if os.path.isfile(os.path.join(self.Mousepath, f))]

                if len(filelist) == 0:
                    logging.info('Specified folder seems to be empty.')
                    return 0
                logging.info('browsing {:d} files...'.format( len(filelist)))

                #Browse filelist for RTstruct dicom file and normal Dcm file to get metadata and print filename
                for i in range(len(filelist)):

                    if DCMflag and RTflag: break

                    fname = os.path.join(self.Mousepath, filelist[i])
                    # Check if file dcm or rtstruct. if it is neither:
                    if self.isRTorDCM(fname) == 0:
                        continue

                    # Get data from RTstruct
                    if self.isRTorDCM(fname) == 1 and not RTflag:

                        # Log
                        logging.info('Importing {:s} as RT structure set.'.format(fname))

                        # Load file and display patient ID
                        meta = self.StructureSet.load(fname)
                        self.UID_RTstruct = meta.PatientID
                        GUI.Text_XR_Filename.setText('RT struct: ' + filelist[i])
                        GUI.Txt_Mouse_ID.setText(self.StructureSet.PatientID)
                        RTflag = True

                    #get further metadata from CT dicom file
                    if self.isRTorDCM(fname) == 2 and not DCMflag:

                        #Log
                        logging.info('Importing {:s} as DCM data file.'.format(fname))

                        # Load meta data
                        common_metadata = dicom.read_file(fname)
                        self.UID_CT = common_metadata.PatientID
                        self.PatientPosition = common_metadata.PatientPosition
                        detect_pos =  (int(common_metadata.DistanceSourceToDetector) -
                                       int(common_metadata.DistanceSourceToPatient))

                        # Print
                        GUI.LabelPosition.setText('Patient Position: ' + self.PatientPosition)
                        GUI.Txt_CT_date.setText(common_metadata.StudyDate)
                        GUI.Txt_CT_detect_pos.setText(str(detect_pos) + 'mm')
                        GUI.LabelPixSpacingXR.setText('Pixel spacing: '
                                                + str(common_metadata.SliceThickness) + ' x '
                                                + str(common_metadata.PixelSpacing[0]) + ' x '
                                                + str(common_metadata.PixelSpacing[0]) + ' mm^3')
                        DCMflag = True

                if RTflag == False:
                    logging.error('ERROR: RTstruct could not be found in given directory.')
                    return 0

                if DCMflag == False:
                    logging.error('ERROR: .dcm file from Planning CT could not be found in given directory.')
                    return 0

                # Check if UIDs of CT and Plan match
                if self.UID_CT != self.UID_RTstruct:
                    Hint = QMessage()
                    Hint.setIcon(QMessage.Information)
                    Hint.setStandardButtons(QMessage.Ok | QMessage.Cancel)
                    Hint.setText("Warning: CT Patient name ({:s}) and "
                                 "RTstruct UID ({:s}) do not match. "
                                 "\nProceed?".format(self.UID_CT,
                                                     proceed = Hint.exec_()))
                else:
                    proceed = QMessage.Ok

                if proceed == QMessage.Cancel:
                    logging.error('UID missmatch detected. Review RTstruct and CT files')
                    return 0
                else:

                    ShiftX, ShiftY = self.StructureSet.getshift()

                    GUI.TxtXRShiftX.setText('{:4.2f}'.format(ShiftX))
                    GUI.TxtXRShiftY.setText('{:4.2f}'.format(ShiftY))
                    GUI.TxtXRShiftX.setStyleSheet("color: #b1b1b1;")
                    GUI.TxtXRShiftY.setStyleSheet("color: #b1b1b1;")

                    # Print results and values to respective text fields
                    GUI.TxtTrgtX.setText('{:4.2f}'.format(self.StructureSet.Target.coordinates[2]))
                    GUI.TxtTrgtY.setText('{:4.2f}'.format(self.StructureSet.Target.coordinates[1]))

                    GUI.TxtXRPinX.setText('{:4.2f}'.format(self.StructureSet.Earpin.coordinates[2]))
                    GUI.TxtXRPinY.setText('{:4.2f}'.format(self.StructureSet.Earpin.coordinates[1]))

                    #self.XRunit('mm')
                    Checklist.LandmarkXR = True
                    Checklist.Target = True
                    Radiography.PatientPosition = self.PatientPosition
                    Radiography.CalcDist()

                    # Activate button for target toggling
                    GUI.Button_toggle_target.clicked.connect(self.toggle_target)
                    logging.info('Import successfull')

        except Exception:
            logging.debug(traceback.print_exc())

    def consistency_check(self):
        """
        checks all currently set User IDs (aka patient names)
        from the different modalities. If the user accidently loaded the wrong
        CT image data/structure set/planar image, this check will
        notice

        Output:
            True for consistent UIDs
            False for inconsistent UIDs
        """
        UIDs = [self.UID_CT, self.UID_RTstruct, self.UID_plan, self.UID_treat]
        UIDs = [x for x in UIDs if x != ""]  # remove None-UIds

        # check how many unique usernames where used
        # and point out any inconsistencies
        if len(list(set(UIDs))) > 1:
            Hint = QMessage()
            Hint.setIcon(QMessage.Information)
            Hint.setStandardButtons(QMessage.Ok | QMessage.Cancel)
            Hint.setText("Different patient names detected in input data: "
                         "\nCT patient name: {:s}"
                         "\nRTstruct patient name: {:s}"
                         "\nPlanning planar image patient name: {:s}"
                         "\nTreatment planar image patient name: {:s}"
                         "\nProceed?".format(self.UID_CT, self.UID_RTstruct,
                                             self.UID_plan, self.UID_treat))
            proceed = Hint.exec_()
            if proceed == QMessage.Cancel:
                return False
            else:
                return True
        else:
            return True

    def processPlanarXRay(self, meta, saturated=0.35, rotate=90):
        """
        Processes a planar X-ray image for display with enhanced contrast

        ---Input---
        Image: dicom metadata object
        saturated: percentage of pixels that should be saturated. Default
        value is 0.35 %
        rotate: Angle by which the image should be rotate. Has to be
        multiple of 90 degrees

        ---Returns---
        n x m array
        """

        # Rotate
        array = meta.pixel_array
        for i in range(int(rotate/90.0)):
            array = np.rot90(array)

        t = np.sort(array.flatten())
        clip = t[int(len(t)*(1.0 - saturated/100.0))]
        array[array > clip] = clip

        return array

    def loadPlanarXRay_Plan(self):
        """Function to be invoked for zupload of planar XRay image from Plan"""

        # If file has been loaded before:
        if Checklist.Planar_scan_Plan:

            GUI.TableTxt_xCorr.setText('')
            GUI.TableTxt_yCorr.setText('')
            GUI.LCD_shift_x.display(0)
            GUI.LCD_shift_y.display(0)
            Checklist.Repositioning = False

        # Clear canvases
        GUI.Display_Plan.canvas.axes.clear()
        GUI.Display_Plan_Hist.canvas.axes.clear()

        # If Mousepath hasnt been specified before
        if not self.Mousepath:
            self.Mousepath = os.path.normpath('\\\\g40fs3\\H-Team\\Experimente\\')

        # Get filename
        fname, _ = Qfile.getOpenFileName(GUI, 'Open file',
                                         self.Mousepath, "Dicom files (*.dcm)")

        if not fname:
            return 0
        else:

            # Load dicom data and read pixel array
            meta = dicom.read_file(fname)
            self.UID_plan = meta.PatientID
            if self.consistency_check():
                pass
            else:
                return 0

            # preprocessing and displaying planar X-Ray:
            self.Planar_Scans.Plan = self.processPlanarXRay(meta)
            GUI.Display_Plan.canvas.axes.imshow(self.Planar_Scans.Plan,
                                                cmap='gray', origin='lower')
            GUI.Display_Plan.canvas.draw()
            GUI.Display_Plan_Hist.canvas.axes.hist(
                self.Planar_Scans.Plan.flatten(), 200)
            GUI.Display_Plan_Hist.canvas.draw()
            GUI.txt_file_Plan.setText(fname)

            # Assign Gray Window
            self.PlanGrayWindow = GrayWindow(GUI.Slider_Plan_GV_center,
                                             GUI.Slider_Plan_GV_range,
                                             GUI.Txt_Plan_GV_center,
                                             GUI.Txt_Plan_GV_range,
                                             GUI.Display_Plan.canvas,
                                             GUI.Display_Plan_Hist.canvas,
                                             self.Planar_Scans.Plan)

            # Raise flag and attempt to start comparison between Plan and Treatment
            Checklist.Planar_scan_Plan = True
            self.compare()
            logging.info('Imported Plan Planar Image {:s}'.format(fname))

    def loadPlanarXRay_Treat(self):
        """Function to be invoked for upload of planar XRay image from Treatment"""

        # If file has been loaded before:
        if Checklist.Planar_scan_Treat:

            GUI.TableTxt_xCorr.setText('')
            GUI.TableTxt_yCorr.setText('')
            GUI.LCD_shift_x.display(0)
            GUI.LCD_shift_y.display(0)
            Checklist.Repositioning = False

        # Clear canvases
        GUI.Display_Treatment.canvas.axes.clear()
        GUI.Display_Treatment_Hist.canvas.axes.clear()

        # If Mousepath hasnt been specified before
        if not self.Mousepath:
            self.Mousepath = os.path.normpath('\\g40fs3\H-Team\Experimente')

        # Get filename
        fname = Qfile.getOpenFileName(GUI, 'Open file',
                                      self.Mousepath, "Dicom files (*.dcm)")[0]

        # If loading was cancelled:
        if not fname:
            return 0
        else:
            # Load dicom data and read pixel array
            meta = dicom.read_file(fname)
            self.UID_treat = meta.PatientID
            if self.consistency_check():
                pass
            else:
                return 0

            # load planar image
            self.Planar_Scans.Treat = self.processPlanarXRay(meta)
            # self.Planar_Scans.Treat = np.rot90(meta.pixel_array)

            GUI.Display_Treatment.canvas.axes.imshow(self.Planar_Scans.Treat,
                                                     cmap='gray',
                                                     origin='lower')
            GUI.Display_Treatment.canvas.draw()
            GUI.Display_Treatment_Hist.canvas.axes.hist(
                self.Planar_Scans.Treat.flatten(), 200)
            GUI.Display_Treatment_Hist.canvas.draw()
            GUI.txt_file_Treatment.setText(fname)

            GUI.Planar_spacing_x.display(meta.PixelSpacing[0])
            GUI.Planar_spacing_y.display(meta.PixelSpacing[1])

            # Assign GrayWindow control
            self.TreatGrayWindow = GrayWindow(GUI.Slider_Treat_GV_center,
                                              GUI.Slider_Treat_GV_range,
                                              GUI.Txt_Treat_GV_center,
                                              GUI.Txt_Treat_GV_range,
                                              GUI.Display_Treatment.canvas,
                                              GUI.Display_Treatment_Hist.canvas,
                                              self.Planar_Scans.Treat)

            # Raise flag and attempt start of comparison
            # between Plan and Treatment
            Checklist.Planar_scan_Treat = True
            self.compare()
            logging.info('Imported Treatment Planar Image {:s}'.format(fname))

    def compare(self):
        """universal function to initialize comparison of
        Plan image and treatment image once both are loaded"""
        # When both images are provided:
        if Checklist.Planar_scan_Plan and Checklist.Planar_scan_Treat:
            # Store data in respective Container
            self.Planar_Scans.init()
            GUI.Display_Overlay_Hist.canvas.axes.hist(
                self.Planar_Scans.Plan.flatten(), 200)

            # Enable toolboxes for movement
            GUI.Planar_Scan_Toolbox.setEnabled(True)
            GUI.group_move_Overlay.setEnabled(True)
            GUI.group_move_Overlay_2.setEnabled(True)
            GUI.group_move_Overlay_3.setEnabled(True)
            GUI.Button_Accept_Repositioning.setEnabled(True)
            self.update_overlay(self.Planar_Scans,
                                GUI.Display_Overlay.canvas,
                                GUI.Display_FalseColor.canvas,
                                GUI.Display_Difference.canvas, first=True)

            # For safety reasons: Disconnect all
            try:
                GUI.Button_UP.clicked.disconnect()
                GUI.Button_DOWN.clicked.disconnect()
                GUI.Button_LEFT.clicked.disconnect()
                GUI.Button_RIGHT.clicked.disconnect()
                GUI.Button_RESET.clicked.disconnect()
                GUI.Slider_Planar_Overlay.valueChanged.disconnect()
                GUI.Planar_Scan_Toolbox.valueChanged.disconnect()
            except Exception:
                pass

            # Connect buttons and text
            GUI.Button_UP.clicked.connect(lambda:   self.move_overlay([+1, 0]))
            GUI.Button_DOWN.clicked.connect(lambda: self.move_overlay([-1, 0]))
            GUI.Button_LEFT.clicked.connect(lambda: self.move_overlay([ 0,-1]))
            GUI.Button_RIGHT.clicked.connect(lambda:self.move_overlay([ 0,+1]))
            GUI.Button_RESET.clicked.connect(self.reset_overlay)
            GUI.Slider_Planar_Overlay.valueChanged.connect(self.adjust_alpha)
            GUI.Planar_Scan_Toolbox.currentChanged.connect(
                lambda: self.update_overlay(self.Planar_Scans,
                                            GUI.Display_Overlay.canvas,
                                            GUI.Display_FalseColor.canvas,
                                            GUI.Display_Difference.canvas))

            # Assign GrayWindow Handler to Overlay image
            self.OverlayGrayWindow = GrayWindow(GUI.Slider_Overlay_GV_center,
                                                GUI.Slider_Overlay_GV_range,
                                                GUI.Txt_Overlay_GV_center,
                                                GUI.Txt_Overlay_GV_range,
                                                GUI.Display_Overlay.canvas,
                                                GUI.Display_Overlay_Hist.canvas,
                                                self.Planar_Scans.Plan)

            # Assign GrayWindow Handler to Difference Image
            self.DifferenceGrayWindow = GrayWindow(GUI.Slider_Difference_GV_center,
                                                   GUI.Slider_Difference_GV_range,
                                                   GUI.Txt_Overlay_GV_center,
                                                   GUI.Txt_Overlay_GV_range,
                                                   GUI.Display_Difference.canvas,
                                                   GUI.Display_Difference_Hist.canvas,
                                                   self.Planar_Scans.get_diff())

    def wipe_positioning(self):
        """
        If pressed, this removes all data
        about current repositioning session
        """

        # Move vectors back to zero
        try:
            self.reset_overlay()
        except Exception:
            pass

        # Remove plan
        GUI.Display_Plan.canvas.axes.clear()
        GUI.Display_Plan.canvas.draw()
        GUI.Display_Plan_Hist.canvas.axes.clear()
        GUI.Display_Plan_Hist.canvas.draw()
        GUI.txt_file_Plan.setText('')

        # Remove Treatment data
        GUI.Display_Treatment.canvas.axes.clear()
        GUI.Display_Treatment.canvas.draw()
        GUI.Display_Treatment_Hist.canvas.axes.clear()
        GUI.Display_Treatment_Hist.canvas.draw()
        GUI.txt_file_Treatment.setText('')

        # Remove overlays
        GUI.Display_Overlay.canvas.axes.clear()
        GUI.Display_Overlay.canvas.draw()
        GUI.Display_FalseColor.canvas.axes.clear()
        GUI.Display_FalseColor.canvas.draw()
        GUI.Display_Difference.canvas.axes.clear()
        GUI.Display_Difference.canvas.draw()
        GUI.Display_Overlay_Hist.canvas.axes.clear()
        GUI.Display_Overlay_Hist.canvas.draw()
        GUI.Display_Difference_Hist.canvas.axes.clear()
        GUI.Display_Difference_Hist.canvas.draw()

        # Remove calculated table coordinates
        GUI.TableTxt_xCorr.setText('')
        GUI.TableTxt_yCorr.setText('')

        # Remove CT data
        GUI.Text_XR_Filename.setText('')

        GUI.TxtXRPinX.setText('')
        GUI.TxtXRPinY.setText('')
        GUI.TxtTrgtX.setText('')
        GUI.TxtTrgtY.setText('')

        GUI.Txt_Mouse_ID.setText('')
        GUI.Txt_CT_date.setText('')
        GUI.Txt_CT_detect_pos.setText('')
        GUI.LabelPosition.setText('Patient Position: ')

        GUI.TxtXRShiftX.setText('')
        GUI.TxtXRShiftY.setText('')
        GUI.LabelPixSpacingXR.setText('Pixel spacing: ')

        # lower flags
        Checklist.Planar_scan_Plan = False
        Checklist.Planar_scan_Treat = False
        Checklist.Target = False
        Checklist.Repositioning = False
        GUI.Button_Accept_Repositioning.setEnabled(False)

        self.UID_CT = []
        self.UID_RTstruct = []

        logging.info('============= POSITIONING DATA REMOVED =============')

    def toggle_target(self):
        """Function that projects target into Radiography image"""
        canvas = GUI.Display_Radiography.canvas

        if not self.Crosshair_Target.visible:
            if not Checklist.IsoCenter:
                logging.debug('Warning: Isocenter hasn\'t been defined yet')
            if not Checklist.LandmarkRG:
                logging.debug('Warning: Radiography Landmark not defined yet')
            if not Checklist.LandmarkXR and Checklist.Target:
                logging.debug('Warning: Plan has not been loaded yet')

            dx = float(GUI.TxtXRShiftX.text())
            dy = float(GUI.TxtXRShiftY.text())

            x_Pin = float(GUI.TxtRGPinX.text())
            y_Pin = float(GUI.TxtRGPinY.text())

            k = Radiography.pixelsizeRG

            x_target = x_Pin + dx/k
            y_target = y_Pin + dy/k

            self.Crosshair_Target.setup(canvas, 5, x_target, y_target,
                                        text='Target', zorder=2,
                                        color='purple')
            self.Crosshair_Repo.setup(canvas, 3, x_target, y_target,
                                      text='', zorder=2,
                                      color='purple')
            self.Crosshair_Target.toggle()
            self.Crosshair_Repo.toggle()
        else:
            self.Crosshair_Target.toggle()
            self.Crosshair_Repo.toggle()

    def accept_repo(self):
        """
        function that's called when X-Ray based Repositioning is accepted
        """
        try:
            Checklist.Repositioning = True
            Radiography.CalcDist()
            GUI.LCD_shift_x.setStyleSheet("color: rgb(0,255,0);")
            GUI.LCD_shift_y.setStyleSheet("color: rgb(0,255,0);")
            GUI.TableTxt_xCorr.setStyleSheet("color: rgb(0,255,0);")
            GUI.TableTxt_yCorr.setStyleSheet("color: rgb(0,255,0);")
        except Exception:
            logging.error(traceback.print_exc())

    def adjust_alpha(self):
        """
        Function that is invoked if alpha slider for Overlay is moved
        """

        # get alpha value from Slider
        alpha = float(GUI.Slider_Planar_Overlay.value()/100.0)

        # Get handles to both images and adjust alpha
        images = GUI.Display_Overlay.canvas.axes.get_images()
        Plan = images[0]
        Treat = images[1]
        Plan.set_alpha(alpha)
        Treat.set_alpha(1.0-alpha)

        GUI.Display_Overlay.canvas.draw()

    def update_overlay(self, Overlay_container, canvas_overlay,
                       canvas_FC, canvas_diff, first=False):
        """
        Function that repaints all images that are necessary for overlay
        of planar X-Ray scans
        """

        # If function is called for the first time:
        # Print all images once with default setting to initialize settings
        if first:
            # Set up new Overlay and set clim
            canvas_overlay.axes.imshow(Overlay_container.get_plan(),
                                       interpolation='nearest',
                                       cmap='gray', alpha=0.5,
                                       origin='lower')
            canvas_overlay.axes.imshow(Overlay_container.get_treat(),
                                       interpolation='nearest',
                                       cmap='gray', alpha=0.5,
                                       origin='lower')
            canvas_overlay.draw()

            # False-color image
            FC = canvas_FC.axes.imshow(Overlay_container.get_rgb(),
                                       origin='lower')
            FC.set_clim(0.2, 1.0)
            canvas_FC.draw()

            # difference image
            canvas_diff.axes.imshow(Overlay_container.get_diff(), cmap='gray',
                                    origin='lower')

            canvas_diff.draw()
            return 0

        # depending on which tool is selected, do not redraw all
        if GUI.Planar_Scan_Toolbox.currentIndex() == 0:
            # if Overlay is selected:
            # Get clims and xlims from Slider/image
            clim_overlay = (int(GUI.Slider_Overlay_GV_center.value()),
                            int(GUI.Slider_Overlay_GV_range.value()))
            xlims = canvas_overlay.axes.get_xlim()
            ylims = canvas_overlay.axes.get_ylim()
            alpha = canvas_overlay.axes.get_alpha()

            # Clear
            canvas_overlay.axes.clear()

            # Set up new Overlay and set clim
            canvas_overlay.axes.imshow(Overlay_container.get_plan(),
                                                interpolation='nearest',
                                                cmap='gray', alpha=0.5,
                                                origin='lower')
            canvas_overlay.axes.imshow(Overlay_container.get_treat(),
                                                interpolation='nearest',
                                                cmap='gray', alpha=0.5,
                                                origin='lower')
            canvas_overlay.axes.set_xlim(xlims)
            canvas_overlay.axes.set_ylim(ylims)
            canvas_overlay.axes.set_alpha(alpha)

            for im in canvas_overlay.axes.get_images():
                im.set_clim(clim_overlay[0] - clim_overlay[1]/2,
                            clim_overlay[0] + clim_overlay[1]/2)
            # Redraw
            canvas_overlay.draw()

        elif GUI.Planar_Scan_Toolbox.currentIndex() == 1:
            # If False Color is selected

            # Get xlims and ylims
            xlims = canvas_FC.axes.get_xlim()
            ylims = canvas_FC.axes.get_ylim()

            canvas_FC.axes.clear()
            canvas_FC.axes.imshow(Overlay_container.get_rgb(), origin = 'lower')
            canvas_FC.axes.set_xlim(xlims)
            canvas_FC.axes.set_ylim(ylims)

            canvas_FC.draw()

        elif GUI.Planar_Scan_Toolbox.currentIndex() == 2:
            # If Difference image is selected
            # Get clim and xlims from Slider/image
            clim_diff    = (GUI.Slider_Difference_GV_center.value()/100.0,
                            GUI.Slider_Difference_GV_range.value()/100.0)
            xlims        = canvas_diff.axes.get_xlim()
            ylims        = canvas_diff.axes.get_ylim()

            canvas_diff.axes.clear()

            # Print Difference Image and set clim
            canvas_diff.axes.imshow(Overlay_container.get_diff(), cmap = 'gray',
                                    origin = 'lower')
            canvas_diff.axes.set_xlim(xlims)
            canvas_diff.axes.set_ylim(ylims)
            for im in canvas_overlay.axes.get_images():
                im.set_clim(clim_diff[0] - clim_diff[1]/2,
                            clim_diff[0] + clim_diff[1]/2)

            canvas_diff.draw()

        GUI.LCD_shift_x.setStyleSheet("color: rgb(255,255,255);")
        GUI.LCD_shift_y.setStyleSheet("color: rgb(255,255,255);")

    def reset_overlay(self):
        " Function to reset overlays to initial position"
        #reset data containers
        self.Planar_Scans.reset()
        self.update_overlay(self.Planar_Scans,
                            GUI.Display_Overlay.canvas,
                            GUI.Display_FalseColor.canvas,
                            GUI.Display_Difference.canvas)

        # Print to txt-fields and reset colors
        GUI.txt_Planar_shift_x.display(0)
        GUI.txt_Planar_shift_y.display(0)
        GUI.LCD_shift_x.display(0)
        GUI.LCD_shift_y.display(0)

        # Remove previously calculated final position
        GUI.TableTxt_xCorr.setText('')
        GUI.TableTxt_yCorr.setText('')

        # reset colors
        GUI.LCD_shift_x.setStyleSheet("color: rgb(255,255,255);")
        GUI.LCD_shift_y.setStyleSheet("color: rgb(255,255,255);")
        GUI.TableTxt_xCorr.setStyleSheet("color: rgb(0,255,0);")
        GUI.TableTxt_yCorr.setStyleSheet("color: rgb(0,255,0);")

    def move_overlay(self, direction):
        """ Function that gets how far the planar image
        is to be moved and executes this"""
        #Read spacing, direction and distance, multiply for net translation
        Spacing_x = GUI.Planar_spacing_x.value()
        Spacing_y = GUI.Planar_spacing_y.value()

        distance = GUI.input_Planar_move.value()
        vector = np.multiply(direction, distance)

        # Move and update
        x,y = self.Planar_Scans.move(vector)
        self.update_overlay(self.Planar_Scans,
                            GUI.Display_Overlay.canvas,
                            GUI.Display_FalseColor.canvas,
                            GUI.Display_Difference.canvas)

        #Print to txt-fields
        GUI.txt_Planar_shift_x.display(x)
        GUI.txt_Planar_shift_y.display(y)

        GUI.LCD_shift_x.display((Spacing_x * x))
        GUI.LCD_shift_y.display((Spacing_y * y))

class Log(object):
    """
    This class handles all choices that can be made in the
    menu dropdown lists
    """

    def __init__(self):

        self.LogDir = os.path.join(os.getcwd(), 'LogFiles')
        if not os.path.isdir(self.LogDir):
            os.mkdir(self.LogDir)

        # make default place for logfile
        self.fname = "{:s}_Radi8_LogFile.log".format(
            datetime.strftime(datetime.today(), '%y%m%d'))
        self.fname = os.path.join(self.LogDir, self.fname)

        GUI.action_LogLevel_Debug.setChecked(True)
        GUI.action_LogLevel_Info.setChecked(False)
        GUI.action_Log_Serial_Com.setChecked(False)

        logging.basicConfig(filename=self.fname,
                            filemode='a',
                            format='%(asctime)s, %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)

        self.initTextLogger()

        # Set actions
        GUI.actionSet_Logfile_Directory.triggered.connect(self.setLogDir)
        GUI.action_LogLevel_Info.triggered.connect( self.LogLevelInfo)
        GUI.action_LogLevel_Debug.triggered.connect(self.LogLevelDebug)
        GUI.action_Log_Serial_Com.triggered.connect(self.Log_Serial_Com)

    def initTextLogger(self):
        "installs everything to display propper Logger"
        logTextBox = QTextEditLogger(GUI)
        # You can format what is printed to text box
        logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(logTextBox)
        # You can control the logging level
        logging.getLogger().setLevel(logging.DEBUG)

        # Add the new logging box widget to the layout
        GUI.LogBox.addWidget(logTextBox.widget)

        logging.info('========== GUI STARTED ==============')
        logging.info('Propper Logger installed.')

        # Remove unnecessary logs from matlotlib
        mpl_logger = logging.getLogger('matplotlib')
        mpl_logger.setLevel(logging.WARNING)

    def LogLevelInfo(self):

        logging.info('Log Level: Info')
        logging.basicConfig(level=logging.INFO)
        GUI.action_LogLevel_Debug.setChecked(False)
        GUI.action_LogLevel_Info.setChecked(True)

    def LogLevelDebug(self):
        logging.info('Log Level: Debug')
        logging.basicConfig(level=logging.DEBUG)
        GUI.action_LogLevel_Debug.setChecked(True)
        GUI.action_LogLevel_Info.setChecked(False)

    def Log_Serial_Com(self):
        """This will set the logger to record all serial communication between
        computer and motors (and produce A LOT of text)"""

        if not GUI.action_Log_Serial_Com.isChecked():
            logging.debug('ending logging of serial communication')
            Motor.verbose = False
        else:
            logging.debug('beginning logging of serial communication')
            Motor.verbose = True

    def setLogDir(self):
        """ Function that sets new directory for storage of logfiles via
        a getDirectory Window"""
        # get a new directory for logfile storage
        self.LogDir = Qfile.getExistingDirectory(GUI, 'Set Directory for logfiles')

        # set new logfile config
        logging.basicConfig(filename=self.fname,
                            filemode='a',
                            format='%(asctime)s, %(levelname)s %(message)s',
                            datefmt='%H:%M:%S')
        logging.info('Changed directory for logfile to: {:s}'.format(self.fname))
        self.LogLevelDebug()

    def LevelAction(self):
        "handles the menu options that set the logging level"





class QTextEditLogger(logging.Handler):
    """ class that subclasses the logging Handler to forward the logging
    information to any widget of the owning object"""
    def __init__(self, parent):
        super().__init__()
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)



"""
  Klasse zur Beschreibung der Graphischen Benutzeroberfläche
"""
class MainWindow(QMain, Ui_Mouse_Positioning_Interface):
    """
      Initialisierung Graphischer Benutzeroberfläche
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        #Initialize GUI and load stylesheet
        self.setupUi(self)


    def closeEvent(self, event):
        Motor.threadpool.clear()
        Motor.StatusWatchDog.Stop()
        Motor.ctrl.close()
        self.close()

        logging.info('++++++++ GUI closed ++++++++++++')

        app.quit()


if __name__=="__main__":

    root = os.getcwd()
    stylefile = os.path.join(root, 'Backend', 'Style', 'stylefile.qss')

    # Assign Checklist
    Checklist = Check()

    # check if instance of app is known to OS
    app = QCoreApplication.instance()
    if app is None:
        app = Qapp(sys.argv)
    else:
        pass

    # Create App-ID: Otherwise, the software's icon will not display propperly.
    appid = 'OncoRay.Preclinical.RadiAiDD'  # for TaskManager
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
    app.setWindowIcon(QtGui.QIcon('Backend/UI/Icons/Icon_3.png'))

    # Create GUI + Logo and Style
    GUI = MainWindow()
    GUI.setStyleSheet(open(stylefile, "r").read())
    GUI.show()

    # initialize Radiography- and XRay-related functions
    Logger = Log()
    Radiography = Radiography()
    XRay = XRay()
    Motor = MotorControl()
    Reg = Registration(GUI)
    app.exec_()
