# -*- coding: utf-8 -*-
"""
Created on Thu Jun 10 11:31:06 2021

@author: johan
"""

import numpy as np
import time
import logging
import traceback
import serial
import os
import configparser
import sys
import glob

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import QThreadPool
from PyQt5.QtCore import QRunnable
from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QMessageBox as QMessage

from Backend.Containers import StateSign


class Signals(QObject):

    # emit position as float
    travelling = pyqtSignal(np.ndarray)
    arrived = pyqtSignal()
    calibrated = pyqtSignal(bool)
    State = pyqtSignal(object)
        

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

        # # shortcut to Bus IDs
        self.MID = Motor.MasterID
        self.SID = Motor.SlaveID

        # create Message to be emitted
        self.StatusAll = np.ndarray(3, dtype=bool)
        self.StatusAll[:] = False
        self.Signal = Signals()

        # logging.debug('Table Status WatchDog initialized')

    @pyqtSlot()
    def run(self):

        # logging.info('Table Status WatchDog awake')
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
                State_Ref_M = self.Motor.serial_query(self.MID, 1, 'REFST')
                State_Ref_S = self.Motor.serial_query(self.SID, 1, 'REFST')

                if State_Ref_M == '1\r' and State_Ref_S == '1\r':
                    self.StatusAll[2] = True
                elif State_Ref_M == 0 or State_Ref_S == 0:
                    self.StatusAll[2] = False
            except Exception:
                self.StatusAll[2] = False

            # Emit collected values
            # self.Signal.State.emit('Growl')
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

        # logging.debug('Table is moving: Movement WatchDog awake')
        # is the thread currently running? Not sure if this is necessary
        if not self._isRunning:
            self._isRunning = True

        # actual routine
        while self._isRunning:
            time.sleep(0.5)

            self.pos = self.Motor.get_Position()
            self.Signal.travelling.emit(self.pos)

            # get state of motor
            self.MState = self.Motor.serial_query(self.MID, 1, 'ASTATE')[0]
            self.SState = self.Motor.serial_query(self.SID, 1, 'ASTATE')[0]

            # If Motor has arrived, emit stop sign
            if self.MState == 'R' and self.SState == 'R':
                time.sleep(.5)  # wait one second for fine positioning
                self.pos = self.Motor.get_Position()

                # Emit signals
                self.Signal.travelling.emit(self.pos)
                time.sleep(.5)  # wait +1 second until WatchDog is let off the leash
                self.Signal.arrived.emit()
                # logging.debug('Destination reached: Movement WatchDog asleep')
                self._isRunning = False
                break

    def stop(self):
        "Terminates the thread"
        self._isRunning = False


class MotorControl(object):
    """ This class holds holds all basic functionality to control the
        motorized linear axes. """

    def __init__(self, GUI):

        self.GUI = GUI        

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
        self.COMstate = StateSign(self.GUI.BoxTableCOM,
                                  ['Disconnected', 'Connected'])
        self.MOTORstate = StateSign(self.GUI.BoxTableInit,
                                    ['Not ready', 'Ready'])
        self.CALIBstate = StateSign(GUI.BoxTableLimits,
                                    ['Calibrated', 'Uncalibrated'])

        # First: Find available COM ports and add to ComboBox
        self.ScanCOMPorts()
        self.GUI.action_scan_COM_ports.triggered.connect(self.ScanCOMPorts)

        # Set up Combo box for positioning mode and connect
        self.GUI.CBoxABSREL.addItem('absolute')
        self.GUI.CBoxABSREL.addItem('relative')
        self.GUI.CBoxABSREL.currentIndexChanged.connect(self.setPositioningMode)

        # Connect buttons
        self.GUI.Button_MotorInit.clicked.connect(self.InitMotor)
        self.GUI.Button_MoveTable.clicked.connect(self.moveTable)
        self.GUI.ButtonCopyCoordinates.clicked.connect(self.CopyCoordinates)

        # Thread Control
        self.threadpool = QThreadPool()
        self.WatchState()

        # Log
        logging.debug('Motor functionality set up successfully')

    def ScanCOMPorts(self):
        """Scans list of COM ports and adds to List of Ports in GUI"""
        portlist = self.get_serial_ports()
        self.GUI.QComboBox_ListOfPorts.clear()
        for port in portlist:
            self.GUI.QComboBox_ListOfPorts.addItem(port)

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
            val = np.array((self.GUI.SpinBoxTablex.value(),
                            self.GUI.SpinBoxTabley.value()))

            # get current position
            curpos = self.get_Position()

            # calculate destination depending on positioning mode
            mode = self.GUI.CBoxABSREL.currentText()

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
        x = float(self.GUI.TableTxt_xCorr.text())
        y = float(self.GUI.TableTxt_yCorr.text())

        self.GUI.SpinBoxTablex.setValue(x)
        self.GUI.SpinBoxTabley.setValue(y)

        # Log
        logging.info('Coppied destination coordinates x = {:.2f}, y = {:.2f}'
                     .format(x, y))

    def setPositioningMode(self):
        """When Mode in absolute/relative combo box changes, write to motor"""

        # get text from Combo Box
        mode = self.GUI.CBoxABSREL.currentText()
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
        self.GUI.Button_StopTable.clicked.connect(
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
        self.GUI.TablePosX.setText(str(pos[0]))
        self.GUI.TablePosY.setText(str(pos[1]))


    def InitMotor(self):
        """
        function that executes everything that is necessary to initialize
        the motor
        """
        
        # Before first: Pause Status WatchDog
        self.StatusWatchDog.Pause()

        # First: Init COM
        port = self.GUI.QComboBox_ListOfPorts.currentText()
        self.InitializeCOM(port)

        # disable boxes for port selection and connect button
        if self.COMstate.state:
            logging.info('Port {:s} ready for serial communication.'
                          .format(port))
            self.GUI.QComboBox_ListOfPorts.setEnabled(False)
            self.GUI.Button_MotorInit.setEnabled(False)
        else:
            logging.error('No serial communication with selected port.')
            return -1

        # Find Slaves
        self.find_slaves(10)
        
        print(self.MasterID)
        print(self.SlaveID)

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
            self.GUI.BoxTableLimits.setStyleSheet("background-color: green;")
            self.GUI.LabelREF.setText('Calibrated')

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

        logging.debug('Configuring Motor Parameters for Slave ID {:d}'.format(slaveID))

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

