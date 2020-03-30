"""
Given a QWidget object these objects give a matplotlib window in Qt4
with one subplot and the toolbar. Can be used in designer-qt4 for promoting
QWidgets.
"""

try:
    from PyQt4 import QtGui
    from PyQt4.QtGui import QApplication as Qapp
    from PyQt4.QtGui import QFileDialog as Qfile
    import PyQt4.QtCore as QtCore
    from PyQt4.QtGui import QWidget as QWid
except:
    from PyQt5 import QtGui
    from PyQt5.QtWidgets import QApplication as Qapp
    from PyQt5.QtWidgets import QFileDialog as Qfile
    from PyQt5.QtWidgets import QWidget as QWid
    import PyQt5.QtCore as QtCore
    
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4 import NavigationToolbar2QT as NavigationToolbar
 
from matplotlib.figure import Figure
 
 
class MplCanvas(FigureCanvas):
    """
    Defines the canvas of the matplotlib window
    """
    def __init__(self):
        self.fig = Figure()                         # create figure
        self.axes = self.fig.add_subplot(111)       # create subplot
        self.fig.subplots_adjust(left=0.13, bottom=0.08, right=0.96, 
                                 top=0.92,  wspace=None, hspace=None)
        
        FigureCanvas.__init__(self, self.fig)       # initialize canvas
        FigureCanvas.setSizePolicy(self, QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
    
 
class matplotlibWidgetSmall(QWid):
    """
    The matplotlibWidget class based on QWidget
    """
    def __init__(self, parent=None):
        QWid.__init__(self, parent)
        # save canvas and toolbar
        self.canvas = MplCanvas()
        self.toolbar = NavigationToolbar(self.canvas, self)        
        # set layout and add them to widget
        self.vbl = QtGui.QVBoxLayout()
        self.vbl.addWidget(self.toolbar)
        self.vbl.addWidget(self.canvas)
        self.setLayout(self.vbl)
