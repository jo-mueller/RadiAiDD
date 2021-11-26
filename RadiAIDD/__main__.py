# -*- coding: utf-8 -*-


from RadiAIDD.Backend.UI.Positioning_Assistant_GUI import Ui_Mouse_Positioning_Interface
from RadiAIDD.Backend.Registration import Registration
from RadiAIDD.Backend.Radiography import Radiography
from RadiAIDD.Backend.MotorControl import MotorControl
from RadiAIDD.Backend.Containers import StateSign
from RadiAIDD.Backend.Containers import Check
from RadiAIDD.Backend.Report import Report

import ctypes

import logging
import sys
import os
from datetime import datetime


from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication as Qapp
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QFileDialog as Qfile
from PyQt5.QtWidgets import QMainWindow as QMain
import PyQt5.QtWidgets as QtWidgets
pyqt_version = 5

class Workflow:
    """
    Class that contains all states that are relevant throughout RadiAIDD
    """
    def __init__(self):

        # Radiography-stuff
        self.has_IsoCenterImage = False  # Was IC image provided?
        self.has_IsoCenterCoords = False  # Were IC coordinates provided?

        # Plan/Treatment Comparison
        self.has_PlanImage = False  # Was plan image provided?
        self.has_TreatImage = False  # Was treatment image provided?
        self.has_Target = False  # Was target volume set?
        self.has_Registration = False # was registration succesful?

        # Stage Movement
        self.has_motor_origin = False  # were IC image motor coordinates (i.e. motor origin) set?
        self.has_motor_dest = False  # was motor destination calculated?
        self.has_motor_reached = False  # has motor reached destination?

        self.steps = []

    def add_step(self, statesign):
        """Add a step in the form of a statesign to the workflow"""

        # If this is the first step: just add
        if len(self.steps) == 0:
            self.steps.append(statesign)

        # if other steps have been provided: Connect state change signal of previous step to this one.
        # This means, when a workflow step is switched to unsatisifed,
        # it will trigger all downstream workflow steps to unsatisifed as well.
        else:
            self.steps[-1].Signals.state_down.connect(statesign.flag_down)
            self.steps.append(statesign)


class Log(object):
    """
    This class handles all choices that can be made in the
    menu dropdown lists
    """

    def __init__(self, GUI):

        self.GUI = GUI

        self.LogDir = os.path.join(os.getcwd(), 'LogFiles')
        if not os.path.exists(self.LogDir):
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
                            level=logging.INFO)

        self.initTextLogger()

        # Set actions
        GUI.actionSet_Logfile_Directory.triggered.connect(self.setLogDir)
        GUI.action_LogLevel_Info.triggered.connect( self.LogLevelInfo)
        GUI.action_LogLevel_Debug.triggered.connect(self.LogLevelDebug)
        GUI.action_Log_Serial_Com.triggered.connect(self.Log_Serial_Com)

    def initTextLogger(self):
        "installs everything to display propper Logger"
        logTextBox = QTextEditLogger(self.GUI)
        # You can format what is printed to text box
        logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(logTextBox)
        # You can control the logging level
        logging.getLogger().setLevel(logging.INFO)

        # Add the new logging box widget to the layout
        self.GUI.LogBox.addWidget(logTextBox.widget)

        logging.info('========== GUI STARTED ==============')
        logging.info('Propper Logger installed.')

        # Remove unnecessary logs from matlotlib
        mpl_logger = logging.getLogger('matplotlib')
        mpl_logger.setLevel(logging.INFO)

    def LogLevelInfo(self):

        logging.info('Log Level: Info')
        logging.basicConfig(level=logging.INFO)
        self.GUI.action_LogLevel_Debug.setChecked(False)
        self.GUI.action_LogLevel_Info.setChecked(True)

    def LogLevelDebug(self):
        logging.info('Log Level: Debug')
        logging.basicConfig(level=logging.DEBUG)
        self.GUI.action_LogLevel_Debug.setChecked(True)
        self.GUI.action_LogLevel_Info.setChecked(False)

    def Log_Serial_Com(self):
        """This will set the logger to record all serial communication between
        computer and motors (and produce A LOT of text)"""

        if not self.GUI.action_Log_Serial_Com.isChecked():
            logging.debug('ending logging of serial communication')
            Motor.verbose = False
        else:
            logging.debug('beginning logging of serial communication')
            Motor.verbose = True

    def setLogDir(self):
        """ Function that sets new directory for storage of logfiles via
        a getDirectory Window"""
        # get a new directory for logfile storage
        self.LogDir = Qfile.getExistingDirectory(self.GUI, 'Set Directory for logfiles')

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

        # Workflow steps
        self.IsoCenterState = StateSign(self.SS_IsoCenter,
                                        ['Isocenter\nnot set', 'Isocenter\nset'],
                                        loglvl='info')
        self.PlanImageState = StateSign(self.SS_PlanImage,
                                        ['Plan\nImage', 'Plan\nImage'])
        self.TreatImageState = StateSign(self.SS_TreatImage,
                                         ['Treatment\nImage', 'Plan\nImage'])
        self.RegistrationState = StateSign(self.SS_RegApproved,
                                           ['Registratio\nunconfirmed', 'Registration\nconfirmed'],
                                        loglvl='info')
        self.StageState = StateSign(self.SS_StageSet,
                                    ['Stage not set', 'Stage set'],
                                        loglvl='info')

        # create workflow
        self.Workflow = Workflow()
        self.Workflow.add_step(self.IsoCenterState)
        self.Workflow.add_step(self.PlanImageState)
        self.Workflow.add_step(self.TreatImageState)
        self.Workflow.add_step(self.RegistrationState)
        self.Workflow.add_step(self.StageState)



    def closeEvent(self, event):
        Motor.threadpool.clear()
        Motor.StatusWatchDog.Stop()
        Motor.ctrl.close()
        self.close()

        logging.info('++++++++ GUI closed ++++++++++++')

        app.quit()


if __name__ == "__main__":

    root = os.getcwd()
    stylefile = os.path.join(root, 'RadiAIDD', 'Backend', 'Style', 'stylefile.qss')

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
    app.setWindowIcon(QtGui.QIcon('/RadiAIDD/Backend/UI/Icons/Icon_3.png'))

    # Create GUI + Logo and Style
    GUI = MainWindow()
    GUI.setStyleSheet(open(stylefile, "r").read())
    GUI.show()

    # initialize subfunctions
    Logger = Log(GUI)
    Radiography = Radiography(GUI, Checklist)
    Motor = MotorControl(GUI)
    Reg = Registration(GUI)
    Report = Report(GUI)
    app.exec_()
