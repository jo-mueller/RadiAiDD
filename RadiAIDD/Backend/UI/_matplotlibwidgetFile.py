"""
Given a QWidget object these objects give a matplotlib window in Qt4
with one subplot and the toolbar. Can be used in designer-qt4 for promoting
QWidgets.
"""


from PyQt5.QtWidgets import QSizePolicy as QSize
from PyQt5.QtWidgets import QVBoxLayout as QVBox
from PyQt5.QtWidgets import QWidget as QWid

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar

from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    """
    Defines the canvas of the matplotlib window
    """

    def __init__(self):
        self.fig = Figure()                         # create figure
        self.axes = self.fig.add_subplot(111)       # create subplot
        self.fig.subplots_adjust(left=0.04, bottom=0.04, right=0.97,
                                 top=0.96,  wspace=None, hspace=None)
        self.fig.patch.set_facecolor((0.19, 0.19, 0.19))

        FigureCanvas.__init__(self, self.fig)  # initialize canvas
        FigureCanvas.setSizePolicy(self, QSize.Expanding,
                                   QSize.Expanding)
        FigureCanvas.updateGeometry(self)


class matplotlibWidget(QWid):
    """
    The matplotlibWidget class based on QWidget
    """

    def __init__(self, parent=None):
        QWid.__init__(self, parent)
        # save canvas and toolbar
        self.canvas = MplCanvas()
        self.toolbar = NavigationToolbar(self.canvas, self)
        # set layout and add them to widget
        self.vbl = QVBox()
        self.vbl.addWidget(self.toolbar)
        self.vbl.addWidget(self.canvas)
        self.setLayout(self.vbl)
