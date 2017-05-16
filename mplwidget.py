# -*- coding: utf-8 -*-
"""
Created on Mon May 08 11:31:37 2017

@author: wendy
"""

from PyQt5 import QtCore, QtGui, QtWidgets
from matplotlib.backends.backend_qt5agg \
 import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure()
        self.axes = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Fixed,
                                   QtWidgets.QSizePolicy.Fixed)
        
        FigureCanvas.updateGeometry(self)

class MPLWidget(QtWidgets.QWidget):
    def __init__(self, parent = None):
        QtWidgets.QWidget.__init__(self, parent)
        self.canvas = MplCanvas()
        self.vbl = QtWidgets.QVBoxLayout()
        self.vbl.addWidget(self.canvas)
        self.setLayout(self.vbl)