# -*- coding: utf-8 -*-
"""
Created on Mon May 15 12:24:34 2017

@author: Wendy
"""
from FrontPanelAPI import ok #must have in site-packages for this to work
from PyQt5 import QtCore, QtGui, uic, QtWidgets
import sys
import cv2
import numpy as np
import threading
import time
import Queue
import math


running = False
capture_thread = None
hist_thread = None
Ui_MainWindow, QtBaseClass = uic.loadUiType("testui.ui")
q1 = Queue.Queue()
q2 = Queue.Queue()
dev = ok.okCFrontPanel()
deviceCount = dev.GetDeviceCount()
for i in range(deviceCount):
    print 'Device[{0}] Model: {1}'.format(i, dev.GetDeviceListModel(i))
    print 'Device[{0}] Serial: {1}'.format(i, dev.GetDeviceListSerial(i))

dev = ok.okCFrontPanel()
dev.OpenBySerial("")
error = dev.ConfigureFPGA("ok_imager.bit")
print error
# Its a good idea to check for errors here


# IsFrontPanelEnabled returns true if FrontPanel is detected.
if True == dev.IsFrontPanelEnabled():
    print "FrontPanel host interface enabled."
else:
    sys.stderr.write("FrontPanel host interface not detected.")

def grab(queue1,queue2, width, height, fps):
    global running, form
    row = 160
    N_adc = 4
    N_adcCh = 3
    N_mux = 46
    col = N_adc*N_adcCh*N_mux
    col_fifo = 552
    count = 1
    datain128 = bytearray(262144)
    datain1 = bytearray(88320)
    
    
    #im = np.array(img.open('imTest.jpg'))
    #imgplot = plt.imshow(im)
    im = np.zeros((row ,col), np.uint8)
    im1 = np.zeros((row ,184), np.uint8)
    im2 = np.zeros((row ,184), np.uint8)
    #plt.figure(3)
    #plt.imshow(im).set_cmap('gray')
    #plt.show()
    
    
    # assert reset signal to initialize the FIFO.
    dev.SetWireInValue(0x10, 0xff, 0x01);
    dev.UpdateWireIns();
    # deactivate reset signal and activate counter.
    dev.SetWireInValue(0x10, 0x00, 0x01);
    dev.UpdateWireIns();
    try:
        exposure = abs(int(form.Exposure.text()))
    except:
        exposure = 1
    try:
        masks= int(form.Masks.text())
    except:
        masks = 600
    try:
        maskchanges = int(form.MaskChanges.text())
    except:
        maskchanges = 0
    try:
        subchange = int(form.SubChange.text())
    except:
        subchange = 0
    
    dev.SetWireInValue(0x11,exposure)
    dev.UpdateWireIns()
    dev.SetWireInValue(0x12,masks)
    dev.UpdateWireIns()
    dev.SetWireInValue(0x13,maskchanges)
    dev.UpdateWireIns()
    dev.SetWireInValue(0x14,subchange)
    dev.UpdateWireIns()
    
    
    # Trigger the counter
    dev.ActivateTriggerIn(0x53, 0x01)

    while(running):
        frame = {}
        dev.UpdateTriggerOuts()
        # If the FIFO is full, read everything and display one frame only and exit the while loop
        if dev.IsTriggered(0x6A, 0x01) == True:
            # print 'FIFO full! ', count, ' times'
            # count = count + 1
            dev.ReadFromPipeOut(0xA0, datain128)
            for i in range(row):
                for j in range(N_adc):
                    for k in range(N_adcCh):
                        for l in range(N_mux):
                            im[row-1-i][col-1-(j*N_adcCh*N_mux+(2-k)*N_mux+45-l)] = datain128[i*col+l*N_adc*N_adcCh+k*N_adc+j]
            #im = im/255
            for i in range(row):
                im1[i] = im[i][139:507:2]
            for i in range(row):
                im2[i] = im[i][138:506:2]

            # break
        # If one frame is ready in FIFO
        elif dev.IsTriggered(0x6A, 0x02) == True:
            dev.ReadFromPipeOut(0xA0, datain1)
            for i in range(row):
                for j in range(N_adc):
                    for k in range(N_adcCh):
                        for l in range(N_mux):
                            im[row-1-i][col-1-(j*N_adcCh*N_mux+(2-k)*N_mux+45-l)] = datain1[i*col+l*N_adc*N_adcCh+k*N_adc+j]
            #im = im/255
            for i in range(row):
                im1[i] = im[i][139:507:2]
            for i in range(row):
                im2[i] = im[i][138:506:2]
        if queue1.qsize() < 10:
            queue1.put(im1)
            queue2.put(im2)
            #print queue1.qsize()
            #print queue2.qsize()
        else:
            print queue1.qsize()



class OwnImageWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(OwnImageWidget, self).__init__(parent)
        self.image = None
        self.x = 0
        self.y = 0
        self.zoom = 1

    def setImage(self, image, x, y, zoom):
        self.image = image
        self.x = x
        self.y = y
        self.zoom = zoom
        sz = image.size()
        self.setMinimumSize(sz)
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        if self.image:
            qp.drawImage(QtCore.QPoint(-self.x*2*math.sqrt(self.zoom), -self.y*2*math.sqrt(self.zoom)), self.image)
        qp.end()


class MyWindowClass(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(self.__class__,self).__init__()
        self.setupUi(self)

        self.startButton.toggled.connect(self.start_clicked)
        
        self.X1.valueChanged.connect(lambda: self.slideChange('x1'))
        self.X2.valueChanged.connect(lambda: self.slideChange('x2'))
        self.Y1.valueChanged.connect(lambda: self.slideChange('y1'))
        self.Y2.valueChanged.connect(lambda: self.slideChange('y2'))
        
        self.X1box.textChanged.connect(lambda: self.boxChange('x1'))
        self.X2box.textChanged.connect(lambda: self.boxChange('x2'))
        self.Y1box.textChanged.connect(lambda: self.boxChange('y1'))
        self.Y2box.textChanged.connect(lambda: self.boxChange('y2'))
        
        self.bitLoad.clicked.connect(self.bit_load)
        #could also use returnPressed()
        #self.window_width = self.ImgWidget.frameSize().width()
        #self.window_height = self.ImgWidget.frameSize().height()
        self.ImgWidget1 = OwnImageWidget(self.ImgWidget1)
        self.ImgWidget2 = OwnImageWidget(self.ImgWidget2)
        
        
        
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(1)
        
    def bit_load(self): #load bit file for FPGA config
        global bitfile, dev
        bitfile, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', 
         'C:\Users\Wendy\gui',"*bit")
        #according to Opal Kelly examples:
        dev.OpenBySerial("") 
        error= dev.ConfigureFPGA(str(bitfile))
        # IsFrontPanelEnabled returns true if FrontPanel is detected.
        if dev.IsFrontPanelEnabled():
            print("FrontPanel host interface enabled.")
        else:
            print("FrontPanel host interface not detected.")
        
    
    def slideChange(self, slider):
        if slider =='x1':
            self.X1box.setText(str(self.X1.value()))
        elif slider =='x2':
            self.X2box.setText(str(self.X2.value()))
        elif slider =='y1':
            self.Y1box.setText(str(self.Y1.value()))
        else: #slider ==y2
            self.Y2box.setText(str(self.Y2.value()))
    
    def boxChange(self,box):
        if box =='x1':
            if self.X1box.text() != str(self.X1.value()):
                try:
                    self.X1.setValue(int(self.X1box.text()))
                except:
                    self.X1.setValue(0)
        elif box =='x2':
            if self.X2box.text() != str(self.X2.value()):
                try:
                    self.X2.setValue(int(self.X2box.text()))
                except:
                    self.X2.setValue(0)
        elif box =='y1':
            if self.Y1box.text() != str(self.Y1.value()):
                try:
                    self.Y1.setValue(int(self.Y1box.text()))
                except:
                    self.Y1.setValue(0)
        else: #box == y2
            if self.Y2box.text() != str(self.Y2.value()):
                try:
                    self.Y2.setValue(int(self.Y2box.text()))
                except:
                    self.Y2.setValue(0)
    def update_frame(self):
        zoom1 = self.Zoom1.value()
        zoom2 = self.Zoom2.value()
        x1 = self.X1.value()
        x2 = self.X2.value()
        y1 = self.Y1.value()
        y2 = self.Y2.value()
        disp_type = self.DispType.currentText()
        if not q1.empty():
            img1 = q1.get()
            if disp_type=='ALL':
                img1 = QtGui.QImage(img1, 184,160, QtGui.QImage.Format_Grayscale8)
                img1 = img1.scaled(184*2*math.sqrt(zoom1), 160*2*math.sqrt(zoom1))
            elif disp_type == 'CEP':
                Z = np.zeros((80,60), np.uint8)
                for i in range(80):
                    Z[i] = img1[i][2:62]
                img1 = QtGui.QImage(Z,60,80, QtGui.QImage.Format_Grayscale8)
                img1 = img1.scaled(60*2*math.sqrt(zoom1), 80*2*math.sqrt(zoom1))
            else: #CEP-TOF
                Z = np.zeros((160,120), np.uint8)
                for i in range(160):
                    Z[i] = img1[i][62:182]
                img1 = QtGui.QImage(Z,120,160, QtGui.QImage.Format_Grayscale8)
                img1 = img1.scaled(120*2*math.sqrt(zoom1), 160*2*math.sqrt(zoom1))
            self.ImgWidget1.setImage(img1,x1,y1,zoom1)
        if not q2.empty():
            img2 = q2.get()
            if disp_type=='ALL':
                img2 = QtGui.QImage(img2, 184,160, QtGui.QImage.Format_Grayscale8)
                img2 = img2.scaled(184*2*math.sqrt(zoom2), 160*2*math.sqrt(zoom2))
            elif disp_type == 'CEP':
                Z = np.zeros((80,60), np.uint8)
                for i in range(80):
                    Z[i] = img2[i][2:62]
                img2 = QtGui.QImage(Z,60,80, QtGui.QImage.Format_Grayscale8)
                img2 = img2.scaled(60*2*math.sqrt(zoom2), 80*2*math.sqrt(zoom2))
            else: #CEP-TOF
                Z = np.zeros((160,120), np.uint8)
                for i in range(160):
                    Z[i] = img2[i][62:182]
                img2 = QtGui.QImage(Z,120,160, QtGui.QImage.Format_Grayscale8)
                img2 = img2.scaled(120*2*math.sqrt(zoom2), 160*2*math.sqrt(zoom2))
            self.ImgWidget2.setImage(img2,x2,y2,zoom2)
    def start_clicked(self):
        global running
        if self.startButton.isChecked():
            running = True
            capture_thread = threading.Thread(target=grab, args = (q1,q2, 184, 160, 30))
            capture_thread.start()
            self.startButton.setText('Stop Displaying Image')
        else:
            running = False
            self.startButton.setText('Display Image')

    def closeEvent(self, event):
        global running
        running = False



if __name__ == "__main__":
    capture_thread = threading.Thread(target=grab, args = (q1,q2, 184, 160, 30))
    app = QtWidgets.QApplication(sys.argv)  # A new instance of QApplication
    form = MyWindowClass()  # We set the form to be our app
    form.show()  # Show the form
    app.exec_()  # and execute the app