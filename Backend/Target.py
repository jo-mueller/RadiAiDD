# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Target.ui'
#
# Created: Mon Dec 11 17:39:14 2017
#      by: PyQt4 UI code generator 4.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Target(object):
    def setupUi(self, Target):
        Target.setObjectName(_fromUtf8("Target"))
        Target.resize(714, 517)
        self.centralwidget = QtGui.QWidget(Target)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.groupBox = QtGui.QGroupBox(self.centralwidget)
        self.groupBox.setGeometry(QtCore.QRect(10, 10, 661, 461))
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.Display_XRay = matplotlibWidget(self.groupBox)
        self.Display_XRay.setGeometry(QtCore.QRect(100, 50, 400, 400))
        self.Display_XRay.setObjectName(_fromUtf8("Display_XRay"))
        self.Button_Done = QtGui.QPushButton(self.groupBox)
        self.Button_Done.setGeometry(QtCore.QRect(540, 400, 111, 31))
        self.Button_Done.setObjectName(_fromUtf8("Button_Done"))
        self.groupBox_2 = QtGui.QGroupBox(self.groupBox)
        self.groupBox_2.setGeometry(QtCore.QRect(10, 20, 81, 411))
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.splitter = QtGui.QSplitter(self.groupBox_2)
        self.splitter.setGeometry(QtCore.QRect(20, 20, 40, 371))
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setObjectName(_fromUtf8("splitter"))
        self.layoutWidget = QtGui.QWidget(self.splitter)
        self.layoutWidget.setObjectName(_fromUtf8("layoutWidget"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.layoutWidget)
        self.horizontalLayout_2.setMargin(0)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.GreyValue_center = QtGui.QSlider(self.layoutWidget)
        self.GreyValue_center.setOrientation(QtCore.Qt.Vertical)
        self.GreyValue_center.setObjectName(_fromUtf8("GreyValue_center"))
        self.horizontalLayout_2.addWidget(self.GreyValue_center)
        self.GreyValue_range = QtGui.QSlider(self.layoutWidget)
        self.GreyValue_range.setOrientation(QtCore.Qt.Vertical)
        self.GreyValue_range.setObjectName(_fromUtf8("GreyValue_range"))
        self.horizontalLayout_2.addWidget(self.GreyValue_range)
        self.layoutWidget_2 = QtGui.QWidget(self.splitter)
        self.layoutWidget_2.setObjectName(_fromUtf8("layoutWidget_2"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.layoutWidget_2)
        self.horizontalLayout.setMargin(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.Label_Scrollbar_center = QtGui.QLabel(self.layoutWidget_2)
        self.Label_Scrollbar_center.setAutoFillBackground(True)
        self.Label_Scrollbar_center.setObjectName(_fromUtf8("Label_Scrollbar_center"))
        self.horizontalLayout.addWidget(self.Label_Scrollbar_center)
        self.Label_Scrollbar_range = QtGui.QLabel(self.layoutWidget_2)
        self.Label_Scrollbar_range.setObjectName(_fromUtf8("Label_Scrollbar_range"))
        self.horizontalLayout.addWidget(self.Label_Scrollbar_range)
        self.Button_setTarget = QtGui.QPushButton(self.groupBox)
        self.Button_setTarget.setGeometry(QtCore.QRect(540, 30, 111, 31))
        self.Button_setTarget.setObjectName(_fromUtf8("Button_setTarget"))
        self.Slider_TargetX = QtGui.QSlider(self.groupBox)
        self.Slider_TargetX.setGeometry(QtCore.QRect(100, 20, 401, 19))
        self.Slider_TargetX.setOrientation(QtCore.Qt.Horizontal)
        self.Slider_TargetX.setObjectName(_fromUtf8("Slider_TargetX"))
        self.Slider_TargetY = QtGui.QSlider(self.groupBox)
        self.Slider_TargetY.setGeometry(QtCore.QRect(510, 50, 19, 391))
        self.Slider_TargetY.setOrientation(QtCore.Qt.Vertical)
        self.Slider_TargetY.setInvertedAppearance(True)
        self.Slider_TargetY.setObjectName(_fromUtf8("Slider_TargetY"))
        self.Button_lockTarget = QtGui.QPushButton(self.groupBox)
        self.Button_lockTarget.setGeometry(QtCore.QRect(540, 130, 111, 31))
        self.Button_lockTarget.setObjectName(_fromUtf8("Button_lockTarget"))
        self.widget = QtGui.QWidget(self.groupBox)
        self.widget.setGeometry(QtCore.QRect(542, 72, 111, 48))
        self.widget.setObjectName(_fromUtf8("widget"))
        self.gridLayout = QtGui.QGridLayout(self.widget)
        self.gridLayout.setMargin(0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label_5 = QtGui.QLabel(self.widget)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.gridLayout.addWidget(self.label_5, 0, 0, 1, 1)
        self.TxtTrgtX = QtGui.QLineEdit(self.widget)
        self.TxtTrgtX.setObjectName(_fromUtf8("TxtTrgtX"))
        self.gridLayout.addWidget(self.TxtTrgtX, 0, 1, 1, 1)
        self.label_6 = QtGui.QLabel(self.widget)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.gridLayout.addWidget(self.label_6, 1, 0, 1, 1)
        self.TxtTrgtY = QtGui.QLineEdit(self.widget)
        self.TxtTrgtY.setObjectName(_fromUtf8("TxtTrgtY"))
        self.gridLayout.addWidget(self.TxtTrgtY, 1, 1, 1, 1)
        Target.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(Target)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 714, 21))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        Target.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(Target)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        Target.setStatusBar(self.statusbar)

        self.retranslateUi(Target)
        QtCore.QMetaObject.connectSlotsByName(Target)

    def retranslateUi(self, Target):
        Target.setWindowTitle(_translate("Target", "TargetDefinition", None))
        self.groupBox.setTitle(_translate("Target", "Target", None))
        self.Button_Done.setText(_translate("Target", "Done", None))
        self.groupBox_2.setTitle(_translate("Target", "Gray Window", None))
        self.Label_Scrollbar_center.setText(_translate("Target", "0", None))
        self.Label_Scrollbar_range.setText(_translate("Target", "0", None))
        self.Button_setTarget.setText(_translate("Target", "Set Target", None))
        self.Button_lockTarget.setText(_translate("Target", "Lock", None))
        self.label_5.setText(_translate("Target", "x=", None))
        self.label_6.setText(_translate("Target", "y=", None))

from matplotlibwidgetFile import matplotlibWidget
