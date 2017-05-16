# -*- coding: utf-8 -*-
"""
Created on Fri May 05 17:38:01 2017

@author: wendy
"""

from __future__ import division
import sys
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from numpy import *
from scipy.integrate import odeint
import mpl_toolkits.mplot3d as p3
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5 import QtCore, QtGui, uic, QtWidgets

class MyForm(QtWidgets.QMainWindow):
    def __init__(self, parent = None):
        super(MyForm, self).__init__(parent)
        self.plot = LorenzPlot()
        self.setCentralWidget(self.plot)

class LorenzPlot(FigureCanvas):
    def __init__(self, *args):
        
        self.fig = Figure()
        self.ax = p3.Axes3D(self.fig)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
    
    def resizeEvent(self, ev):
        self.ax.clear()
        self.canvas.draw()
        self.fig.set_size_inches(self.size().width()/self.fig.get_dpi(),
                self.size().height()/self.fig.get_dpi())
        self.draw_plot()
        print self.fig.get_size_inches()*self.fig.get_dpi()
        print self.size()

    def Lorenz(self, w, t, s, r, b):
        x, y, z = w
        return array([s*(y-x), r*x-y-x*z, x*y-b*z])

    def draw_plot(self, s=8.0, r=28.1, b=8/3.0):
        # Parameters
        self.s, self.r, self.b = s, r, b
        
        self.w_0 = array([0., 0.8, 0.])         # initial condition
        self.time = arange(0., 100., 0.01)      # time vector 
        #integrate a system of ordinary differential equations
        self.trajectory = odeint(self.Lorenz, self.w_0, self.time, args=(self.s, self.r, self.b))
        
        self.x = self.trajectory[:, 0]
        self.y = self.trajectory[:, 1]
        self.z = self.trajectory[:, 2]
        
        self.ax = p3.Axes3D(self.fig)
        self.ax.plot3D(self.x, self.y, self.z)
        self.canvas.draw()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = MyForm()
    form.show()
    sys.exit(app.exec_())