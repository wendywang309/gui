# -*- coding: utf-8 -*-
"""
Created on Mon May 15 12:24:34 2017

@author: Wendy
"""
from FrontPanelAPI import ok #must have FrontPanelAPI folder in site-packages
from PyQt5 import QtCore, QtGui, uic, QtWidgets
#from PyQt5.QtGui import QPixmap
import sys
import cv2
import numpy as np
import threading
import time
import Queue
import math
import os
import csv
#from pathlib2 import Path
#initialize global variables
FPS = 20 #set fps of video output 
running = False
capture_thread = None
bitfile = ''
recording = 0 #1--video is recording, 0--video not recording
toSave = 0 #images left to save
TEST_SIZE = 20
calib_on = 0
equalize = 0
bg_calib = 0
black_calib = 0
b_count = TEST_SIZE
b_set = 0
bg_count = TEST_SIZE
bg_set = 0

bg_img1 = np.zeros((80,60))
b_img1 = np.zeros((80,60))
bg_img2 = np.zeros((80,60))
b_img2 = np.zeros((80,60))

Ui_MainWindow, QtBaseClass = uic.loadUiType("GUILayout.ui")
#initialize fifo queues to hold camera data before being displayed
q1 = Queue.Queue() 
q2 = Queue.Queue()

dev = ok.okCFrontPanel()
deviceCount = dev.GetDeviceCount()
for i in range(deviceCount):
    print 'Device[{0}] Model: {1}'.format(i, dev.GetDeviceListModel(i))
    print 'Device[{0}] Serial: {1}'.format(i, dev.GetDeviceListSerial(i))

dev = ok.okCFrontPanel()
dev.OpenBySerial("")
#error = dev.ConfigureFPGA("ok_imager.bit")
#print error
# Its a good idea to check for errors here


# IsFrontPanelEnabled returns true if FrontPanel is detected.
#if True == dev.IsFrontPanelEnabled():
#    print "FrontPanel host interface enabled."
#else:
#    sys.stderr.write("FrontPanel host interface not detected.")

def grab(queue1,queue2):
    '''
    Reset fifo, set camera parameters (exposure, masks, etc), activate trigger,
    and continuously grab camera output and put into queues while "Display Image"
    button is checked. 
    
    Args:
        queue1 -- queue for camera bucket 1 output
        queue2 -- queue for camera bucket 2 output
    '''
    global running, form, exposure, masks, maskchanges, subchange
    row = 160
    N_adc = 4
    N_adcCh = 3
    N_mux = 46
    col = N_adc*N_adcCh*N_mux
    datain128 = bytearray(262144)
    datain1 = bytearray(88320)
    
    im = np.zeros((row ,col), np.uint8)
    im1 = np.zeros((row ,184), np.uint8)
    im2 = np.zeros((row ,184), np.uint8)
    
    # assert reset signal to initialize the FIFO.
    dev.SetWireInValue(0x10, 0xff, 0x01)
    dev.UpdateWireIns()
    # deactivate reset signal and activate counter.
    dev.SetWireInValue(0x10, 0x00, 0x01)
    dev.UpdateWireIns()
    time.sleep(0.01) #allow time for FIFO to reset
    try:
        exposure = abs(int(form.Exposure.text()))
    except:
        exposure = 1
    try:
        masks= abs(int(form.Masks.text()))
    except:
        masks = 600
    try:
        maskchanges = abs(int(form.MaskChanges.text()))
    except:
        maskchanges = 0
    try:
        subchange = abs(int(form.SubChange.text()))
    except:
        subchange = 0

    dev.SetWireInValue(0x11,exposure)
    #.UpdateWireIns()
    dev.SetWireInValue(0x12,masks)
    #dev.UpdateWireIns()
    dev.SetWireInValue(0x13,maskchanges)
    #dev.UpdateWireIns()
    dev.SetWireInValue(0x14,subchange)
    #dev.UpdateWireIns()
    dev.SetWireInValue(0x15, 0xf003ff) #patgen_stop,patgen_start,patgen_in
    time.sleep(0.1)
    dev.UpdateWireIns()
    time.sleep(0.1)
    dev.ActivateTriggerIn(0x53, 0x01)

    while(running):
        dev.UpdateTriggerOuts()
        # If the FIFO is full, read everything and display one frame only
        if dev.IsTriggered(0x6A, 0x01) == True:
            dev.ReadFromPipeOut(0xA0, datain128)
            for i in range(row):
                for j in range(N_adc):
                    for k in range(N_adcCh):
                        for l in range(N_mux):
                            im[row-1-i][col-1-(j*N_adcCh*N_mux+(2-k)*N_mux+45-l)] = datain128[i*col+l*N_adc*N_adcCh+k*N_adc+j]
            #im = im/255
            for i in range(row):
                im1[i] = im[i][138:506:2]
                im2[i] = im[i][139:507:2]
             
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
                im1[i] = im[i][138:506:2]
                im2[i] = im[i][139:507:2]
                
        if queue1.qsize() < 15:
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
        self.save =0
        self.resize(184*2,160*2)

    def setImage(self, image, x, y, zoom):
        '''Add the arguments to the OwnImageWidget class and call
        for a repaint of the widget contents.
        
        Args:
            image -- QImage holding the data needed to paint the widget
            x -- current position of the x axis slider
            y -- current position of the y axis slider
            zoom -- current value of the zoom slider 
        '''
        self.image = image
        self.x = x
        self.y = y
        self.zoom = zoom
        #sz = image.size()
        #self.setMinimumSize(sz)
        self.update() #schedules a repaint

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        if self.image is not None:
            #set the image to be drawn at a point according to the x and y axis sliders
            qp.drawImage(QtCore.QPoint(-self.x*2*math.sqrt(self.zoom), 
                                       -self.y*2*math.sqrt(self.zoom)), self.image)
        qp.end()

class MyWindowClass(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(self.__class__,self).__init__()
        self.setupUi(self)
        
        self.XSlider.valueChanged.connect(self.slide_x)
        self.YSlider.valueChanged.connect(self.slide_y)
        
        self.Xbox.textChanged.connect(self.box_x)
        self.Ybox.textChanged.connect(self.box_y)
        #could also use returnPressed instead of textChanged to reduce frequency of occurence
        
        #define what buttons do when clicked or toggled
        self.BitLoad.clicked.connect(self.bit_load)
        self.DispImage.toggled.connect(self.disp_img)
        self.SaveImages.clicked.connect(self.save)
        self.RecVideo.toggled.connect(self.rec_video)
        self.PattLoad.clicked.connect(self.patt_load)
        self.Reset.clicked.connect(self.reset_frame)
        self.CalibBlack.clicked.connect(self.calib_b)
        self.CalibBG.clicked.connect(self.calib_bg)
        self.ApplyImg.toggled.connect(self.apply_calib)
        self.EqualizeImg.toggled.connect(self.equalize)
        
        self.DispType.currentIndexChanged.connect(self.disp_change)
        
        #disable buttons at startup
        self.SaveImages.setEnabled(False)
        self.RecVideo.setEnabled(False)
        self.ApplyImg.setEnabled(False)
        self.CalibBlack.setEnabled(False)
        self.CalibBG.setEnabled(False)
        
        #self.window_width = self.ImgWidget.frameSize().width()
        #self.window_height = self.ImgWidget.frameSize().height()
        
        #promote QWidgets to OwnImageWidget 
        self.ImgWidget1 = OwnImageWidget(self.ImgWidget1) 
        self.ImgWidget2 = OwnImageWidget(self.ImgWidget2)
        
        #start timer with 1ms timeout at which the frame is updated
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(1)
    def calib_b(self):
        global b_count, b_img1, b_img2
        self.CalibBlack.setEnabled(False)
        b_img1 = np.zeros((80,60))
        b_img2 = np.zeros((80,60))
        b_count = 0
        
        
    def calib_bg(self):
        global bg_count, bg_img1, bg_img2
        self.CalibBG.setEnabled(False)
        bg_img1 = np.zeros((80,60))
        bg_img2 = np.zeros((80,60))
        bg_count =0
        
    def apply_calib(self):
        global calib_on
        if self.ApplyImg.isChecked():
            calib_on = 1
        else:
            calib_on = 0
    
    def equalize(self):
        global equalize
        if self.EqualizeImg.isChecked():
            equalize = 1
        else:
            equalize = 0
    
    def bit_load(self): 
        '''Open a window to allow user to select bit file to configure the FPGA'''
        global bitfile, dev
        bitfile, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', os.getcwd(),"*bit")
        #according to Opal Kelly examples:
        dev.OpenBySerial("") 
        error= dev.ConfigureFPGA(str(bitfile))
        # IsFrontPanelEnabled returns true if FrontPanel is detected.
        if dev.IsFrontPanelEnabled():
            print("FrontPanel host interface enabled.")
        else:
            bitfile = 'error' #to prevent user from trying to display image when no interface detected
            print("FrontPanel host interface not detected.")
    
    def patt_load(self):
        if bitfile=='': #check if no bit file is loaded
            errorBox = QtWidgets.QMessageBox()
            errorBox.setWindowTitle('Error')
            errorBox.setText('Please load bit file first.')
            errorBox.addButton(QtWidgets.QPushButton('OK'), QtWidgets.QMessageBox.YesRole)
            errorBox.exec_()
        elif bitfile == 'error':
            errorBox = QtWidgets.QMessageBox()
            errorBox.setWindowTitle('Error')
            errorBox.setText('FrontPanel host interface not detected.')
            errorBox.addButton(QtWidgets.QPushButton('OK'), QtWidgets.QMessageBox.YesRole)
            errorBox.exec_()
        else:
            pattfile, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', os.getcwd(),"*csv")
            if pattfile != '':
                with open(str(pattfile), 'rb') as csvfile:
                    pattern = []
                    csvRead = csv.reader(csvfile)
                    for row in csvRead:
                        pattern.extend(row)
                    pattern = map(int, pattern)
                    # Send brief reset signal to initialize the FIFO.
                    dev.SetWireInValue(0x10, 0xff, 1)
                    dev.UpdateWireIns()
                    dev.SetWireInValue(0x10, 0x00, 1)
                    dev.UpdateWireIns()
                    # Send pattern to PipeIn endpoint with address 0x80
                    data = dev.WriteToPipeIn(0x80, bytearray(pattern)) 
                    #out = bytearray(len(pattern))
                    #data = dev.ReadFromPipeOut(0xB0, out)
                    #print str(out)
            
    def save(self):
        '''Create folder to contain images based on the settings (exposure, masks, etc) '''
        global toSave,folder1, folder2, disp_type, exposure, masks, maskchanges, subchange
        self.SaveImages.setEnabled(False)
        toSave = int(form.NumImages.text())
        currDir = os.getcwd()
        folder1 = os.path.join(currDir, 'Bucket1' +'_Exp'+str(exposure) + '_Masks' 
                               + str(masks)+'_' + str(maskchanges) + '_' + str(subchange) + '_' + disp_type)
        folder2 = os.path.join(currDir, 'Bucket2' +'_Exp'+str(exposure) + '_Masks' 
                               + str(masks)+'_' + str(maskchanges) + '_' + str(subchange) + '_' + disp_type)
        if not os.path.isdir(folder1): #check if folder by the same name exists already
            os.mkdir(folder1)
            os.mkdir(folder2)
    
    def rec_video(self):
        '''Create video folder if one does not exist and manage creation and 
        release of video file.
        '''
        global recording, video1, video2,FPS,disp_type 
        if self.RecVideo.isChecked():
            if disp_type =='ALL':
                w = 184
                h = 160
            elif disp_type == 'CEP':
                w = 60
                h = 80
            else:#CEP-TOF
                w = 120
                h = 160    
            currDir = os.getcwd()
            folder= os.path.join(currDir,'Saved Videos')
            if not os.path.exists(folder): #check if folder exists yet, if not, create one
                os.mkdir(folder)
            i = 0
            filename1 = ('B1'+'_Exp'+str(exposure) + '_Masks' + str(masks)+'_' 
                         + str(maskchanges) + '_' + str(subchange) + '_Vid' +str(i)+'.avi')
            vidpath1 = os.path.join(folder,filename1)
            #check if video by the same name exists, if so, increase counter 
            while os.path.isfile(vidpath1): 
                i+=1
                filename1 = ('B1' +'_Exp'+str(exposure) + '_Masks' + str(masks) 
                            + '_' + str(maskchanges) + '_' + str(subchange) + '_Vid' +str(i)+'.avi')
                vidpath1 = os.path.join(folder,filename1)
            filename2 = ('B2' +'_Exp'+str(exposure) + '_Masks' + str(masks)+'_' 
                         + str(maskchanges) + '_' + str(subchange) + '_Vid' +str(i)+'.avi')
            vidpath2 = os.path.join(folder,filename2)
            video1 = cv2.VideoWriter(vidpath1, 541215044, FPS, (w,h)) #541215044 is no compression codec
            video2 = cv2.VideoWriter(vidpath2, 541215044, FPS, (w,h))
            recording = 1 
            self.RecVideo.setText('Stop Recording Video')
        else:
            recording = 0
            video1.release()
            video2.release()
            self.RecVideo.setText('Record Video')
    
    def reset_frame(self):
        '''Reset the position and zoom of the images'''
        self.XSlider.setValue(0)
        self.YSlider.setValue(0)
        self.Zoom.setValue(1)
        
    def disp_change(self):
        '''Stop video recording and any other processes dependent on type 
        of image displayed.
        '''
        self.RecVideo.setChecked(False) #stop recording video 
        
    def slide_x(self):
        ''' '''
        self.Xbox.setText(str(self.XSlider.value()))

    def slide_y(self):
        ''' '''
        self.Ybox.setText(str(self.YSlider.value()))
        
    def box_x(self):
        '''Set X axis slider to match the value of its QLineEdit box if a user has
        manually input a change in the box.'''
        if self.Xbox.text() != str(self.XSlider.value()):
            try:
                self.XSlider.setValue(int(self.Xbox.text()))
            except:
                self.XSlider.setValue(0)
    def box_y(self):
        '''Set Y axis slider to match the value of its QLineEdit box if a user has
        manually input a change in the box.'''
        if self.Ybox.text() != str(self.YSlider.value()):
            try:
                self.YSlider.setValue(int(self.Ybox.text()))
            except:
                self.YSlider.setValue(0)
    
    def update_frame(self):
        '''Tell the image widget what to display based on parameters selected by
        the user by calling OwnImageWidget.setImage().
        '''
        global toSave, disp_type,folder1, folder2, video1, video2
        global bg_count,b_count, bg_img1, b_img1, bg_img2, b_img2, bg_set, b_set, equalize
        zoom = self.Zoom.value()
        x = self.XSlider.value()
        y = self.YSlider.value()
        disp_type = self.DispType.currentText()

        if not q1.empty():
            img1 = q1.get()
            img2 = q2.get()
            if toSave>0:
                toSave = toSave -1
                i = 0
                filename1 = 'Bucket1_Image'+str(i)+'.png'
                imagepath1 = os.path.join(folder1,filename1)
                while os.path.isfile(imagepath1):
                    i +=1
                    filename1 = 'Bucket1_Image'+str(i)+'.png'
                    imagepath1 = os.path.join(folder1,filename1)
                imagepath2 = os.path.join(folder2, 'Bucket2_Image'+str(i)+'.png')
                save = 1 
                #to save exactly what is displayed on screen:
                #p = self.ImgWidget1.grab()
                #p.save(imagepath1,'png',100)
                #p = self.ImgWidget2.grab()
                #p.save(imagepath2,'png',100)
            else:
                save = 0
                self.SaveImages.setEnabled(True)
               
            if disp_type=='ALL':
                if recording ==1:
                    video1.write(img1)
                    video2.write(img2) #must be in nparray format
                img1 = QtGui.QImage(img1, 184,160, QtGui.QImage.Format_Grayscale8)
                img2 = QtGui.QImage(img2, 184,160, QtGui.QImage.Format_Grayscale8)
                if save ==1:
                    img1.save(imagepath1,'png',100)
                    img2.save(imagepath2,'png',100) #must be QImage format
                img1 = img1.scaled(184*2*math.sqrt(zoom), 160*2*math.sqrt(zoom))
                img2 = img2.scaled(184*2*math.sqrt(zoom), 160*2*math.sqrt(zoom))
                #self.ImgWidget1.resize(184*2,160*2)
            elif disp_type == 'CEP':
                Z1 = np.zeros((80,60), np.uint8)
                Z2 = np.zeros((80,60), np.uint8)
                for i in range(80):
                    Z1[i] = img1[i][2:62]
                    Z2[i] = img2[i][2:62]
                
                if bg_count <TEST_SIZE:
                    bg_img1 += Z1
                    bg_img2 += Z2
                    if bg_count ==TEST_SIZE-1:
                        bg_img1 = bg_img1/TEST_SIZE
                        bg_img2 = bg_img2/TEST_SIZE
                        bg_set = 1
                        self.CalibBG.setEnabled(True)
                        if b_set ==1:
                            self.ApplyImg.setEnabled(True)     
                    bg_count+=1
                if b_count <TEST_SIZE:
                    b_img1 += Z1
                    b_img2 += Z2
                    if b_count ==TEST_SIZE-1:
                        b_img1 = b_img1/TEST_SIZE
                        b_img2 = b_img2/TEST_SIZE
                        b_set = 1
                        self.CalibBlack.setEnabled(True)
                        if bg_set ==1:
                            self.ApplyImg.setEnabled(True) 
                    b_count +=1
                if calib_on:
                    if np.count_nonzero(bg_img1-b_img1) == (80*60) and np.count_nonzero(bg_img2-b_img2) ==(80*60):
                        Z1 = abs((Z1-b_img1)*(np.mean(bg_img1-b_img1))/(bg_img1-b_img1))
                        Z2 = abs((Z2-b_img2)*(np.mean(bg_img2-b_img2))/(bg_img2-b_img2))
                        Z1 = Z1.astype(np.uint8)
                        Z2 = Z2.astype(np.uint8)
                    
                if recording ==1:
                    video1.write(Z1)
                    video2.write(Z2)
                if equalize==1:
                    Z1 = cv2.equalizeHist(Z1)
                    Z2 = cv2.equalizeHist(Z2)
                img1 = QtGui.QImage(Z1,60,80, QtGui.QImage.Format_Grayscale8)
                img2 = QtGui.QImage(Z2,60,80, QtGui.QImage.Format_Grayscale8)
                if save ==1:
                    img1.save(imagepath1,'png',100)
                    img2.save(imagepath2,'png',100)
                img1 = img1.scaled(60*2*math.sqrt(zoom), 80*2*math.sqrt(zoom))
                img2 = img2.scaled(60*2*math.sqrt(zoom), 80*2*math.sqrt(zoom))
                #self.ImgWidget1.resize(60*2,80*2)
            else: #CEP-TOF
                Z1 = np.zeros((160,120), np.uint8)
                Z2 = np.zeros((160,120), np.uint8)
                for i in range(160):
                    Z1[i] = img1[i][62:182]
                    Z2[i] = img2[i][62:182]
                if recording ==1:
                    video1.write(Z1)
                    video2.write(Z2)
                img1 = QtGui.QImage(Z1,120,160, QtGui.QImage.Format_Grayscale8)
                img2 = QtGui.QImage(Z2,120,160, QtGui.QImage.Format_Grayscale8)
                if save ==1:
                    img1.save(imagepath1,'png',100)
                    img2.save(imagepath2,'png',100)
                img1 = img1.scaled(120*2*math.sqrt(zoom), 160*2*math.sqrt(zoom))
                img2 = img2.scaled(120*2*math.sqrt(zoom), 160*2*math.sqrt(zoom))
                #self.ImgWidget1.resize(120*2,160*2)
            self.ImgWidget1.setImage(img1,x,y,zoom)
            self.ImgWidget2.setImage(img2,x,y,zoom)

    def disp_img(self):
        '''Start and end thread which displays camera output based on state 
        of the Display Image button.
        '''
        global running, bitfile, calib_on, b_set, bg_set
        if self.DispImage.isChecked():
            if bitfile == '':
                #make error box pop up if bit file not loaded
                errorBox = QtWidgets.QMessageBox()
                errorBox.setWindowTitle('Error')
                errorBox.setText('Please load bit file first.')
                errorBox.addButton(QtWidgets.QPushButton('OK'), QtWidgets.QMessageBox.YesRole)
                errorBox.exec_()
                self.DispImage.setChecked(False) #reset button
            elif bitfile =='error':
                errorBox = QtWidgets.QMessageBox()
                errorBox.setWindowTitle('Error')
                errorBox.setText('FrontPanel host interface not detected.')
                errorBox.addButton(QtWidgets.QPushButton('OK'), QtWidgets.QMessageBox.YesRole)
                errorBox.exec_()
            else:
                self.RecVideo.setEnabled(True)
                self.SaveImages.setEnabled(True)
                self.CalibBlack.setEnabled(True)
                self.CalibBG.setEnabled(True)
                running = True
                capture_thread = threading.Thread(target=grab, args = (q1,q2))
                capture_thread.start()
                self.DispImage.setText('Stop Displaying Image')
                b_set = 0
                bg_set = 0
        else:
            running = False
            self.RecVideo.setChecked(False) #stop recording video
            self.RecVideo.setEnabled(False)
            self.SaveImages.setEnabled(False)
            self.ApplyImg.setEnabled(False)
            self.ApplyImg.setChecked(False)
            self.DispImage.setText('Display Image')

    def closeEvent(self, event):
        global running
        running = False


if __name__ == "__main__":
    #capture_thread = threading.Thread(target=grab, args = (q1,q2))
    app = QtWidgets.QApplication(sys.argv)  # A new instance of QApplication
    form = MyWindowClass()  # We set the form to be our app
    form.show()  # Show the form
    app.exec_()  # and execute the app