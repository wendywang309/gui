# -*- coding: utf-8 -*-
"""
Created on Tue May 02 13:28:45 2017

@author: wendy
"""
from __future__ import with_statement
import sys
from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import QThread 
from FrontPanelAPI import ok #must have in site-packages for this to work
import os
import os.path
import csv
import time
import numpy as np
#import matplotlib.image as mpimg
from PIL import Image
from pathlib2 import Path
import cv2 #must have in site-packages for this to work
import threading


qtDesignerFile = "MBI_GUI.ui" 
#taken from sample code from Opal Kelly:
dev = ok.okCFrontPanel() #device

        
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtDesignerFile)

bitfile = ""
pattfile = ""
imgSave = 0
vidRec = 0
disp_on = 0



    

class MBI_GUI(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.setupUi(self)
        self.LoadBitFile.clicked.connect(self.bit_load) #when Load Bit File button is clicked
        self.LoadPattFile.clicked.connect(self.patt_load) #when Load Camera Pattern File button is clicked
        self.DispFrame.currentIndexChanged.connect(self.disp_change) #DispFrame selection changed
        self.DispImage.toggled.connect(self.disp_image) #when Display Image button is clicked
        self.RecVideo.toggled.connect(self.rec_video) #when Record Video button is clicked
        self.RecVideo.setEnabled(False) #disable saving images
        self.SaveImages.clicked.connect(self.save_img) #when save images button is clicked
        self.SaveImages.setEnabled(False) #disable saving images
        
        #img=mpimg.imread('test.png','L')
        #img=cv2.imread('test.png',0)
        
        #self.mplimg1.canvas.axes.imshow(img, 'gray')
        #self.mplhist1.canvas.axes.hist(img.ravel(),bins =256)
        #adjusting contrast:
        #newimg = cv2.equalizeHist(img)
        #self.mplimg2.canvas.axes.imshow(newimg, 'gray')
        #self.mplhist2.canvas.axes.hist(newimg.ravel(),bins =256)
        #clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        #cl1 = clahe.apply(img)
        #self.mplimg2.canvas.axes.imshow(cl1, 'gray')
        #self.mplhist2.canvas.axes.hist(cl1.ravel(),bins =256)
        #video = cv2.VideoWriter('testvid1.avi',0, 20, (184,160)) #20fps 184x160 video
        #video.write(img)
        #video.write(img)
        #video.write(img)
        #cv2.destroyAllWindows
        #video.release()
        #im = Image.fromarray(np.uint8(img))
        #currDir = os.getcwd()
        #folder= os.path.join(currDir,'Saved Images')
        #folderpath = Path(folder)
        #if not folderpath.exists():
            #os.mkdir(folder)
        #i = 0
        #filename = 'testsave'+str(i)+'.png'
        #imagefile = os.path.join(folder,filename)
        #while Path(imagefile).exists():
            #i+=1
            #filename = 'testsave'+str(i)+'.png'
            #imagefile = os.path.join(folder,filename)
        #im.save(imagefile)
        
    def bit_load(self): #load bit file for FPGA config
        global bitfile, dev
        bitfile, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', 
         'c:\\',"*bit")
        #according to Opal Kelly examples:
        dev.OpenBySerial("") 
        error= dev.ConfigureFPGA(str(bitfile))
        # IsFrontPanelEnabled returns true if FrontPanel is detected.
        if dev.IsFrontPanelEnabled():
            print("FrontPanel host interface enabled.")
        else:
            print("FrontPanel host interface not detected.")
    def patt_load(self): #load camera pattern file
        if str(bitfile)!='': #check if bit file is loaded first
            global pattfile
            pattfile, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open file', 'c:\\',"*csv")
            with open(str(pattfile), 'rb') as csvfile:
                pattern = csv.reader(csvfile)
                # Send brief reset signal to initialize the FIFO.(code from Opal Kelly)
                dev.SetWireInValue(0x10, 0xff, 0x01)
                dev.UpdateWireIns()
                dev.SetWireInValue(0x10, 0x00, 0x01)
                dev.UpdateWireIns()
                dataout = bytearray(str(pattern))
                #buf = bytearray(len(str(pattern)))
                # Send pattern to PipeIn endpoint with address 0x80
                data = dev.WriteToPipeIn(0x80, dataout) #data must be mutable type bytearray
                # Read pattern from PipeOut endpoint with address 0xB0
                #data = dev.ReadFromPipeOut(0xB0,buf) #why 0xB0?
        else:
            errorBox = QtWidgets.QMessageBox()
            errorBox.setWindowTitle('Error')
            errorBox.setText('Please load bit file first.')
            errorBox.addButton(QtWidgets.QPushButton('OK'), QtWidgets.QMessageBox.YesRole)
            errorBox.exec_()
    def disp_change(self): #if DispFrame selection has changed
        #stop displaying images and/or recording video
        pass
    def disp_image(self):
        #displays image based on settings
        if (self.DispImage.isChecked()): #if display image button is checked
            if str(bitfile)=="":
                #make error box pop up if bit file not loaded
                errorBox = QtWidgets.QMessageBox()
                errorBox.setWindowTitle('Error')
                errorBox.setText('Please load bit file first.')
                errorBox.addButton(QtWidgets.QPushButton('OK'), QtWidgets.QMessageBox.YesRole)
                errorBox.exec_()
                self.DispImage.setChecked(False) #reset button
            else:
                #get input values
                global exposure, numMasks, numMaskChanges, numSubPer, frame
                exposure = self.Exposure.text()
                numMasks = self.Masks.text()
                numMaskChanges = self.MaskChanges.text()
                numSubPer = self.SubChange.text()
                frame = self.DispFrame.currentText()
                valid = True #flag, 0 if any inputs are not valid
                #determine if exposure value is valid input:
                try:
                    exposure = int(exposure) #change into integer type
                    if exposure!=abs(exposure):
                        valid = False
                except ValueError: #if not an int
                    valid = False
                #determine if number of masks is valid:
                try:
                    numMasks = int(numMasks) #change into integer type
                    if numMasks!=abs(numMasks): #make sure its a positive integer
                        valid = False
                except ValueError: #if not an int
                    valid = False
                #determine if mask changes is valid:
                try:
                    numMaskChanges = int(numMaskChanges) #change into integer type
                    if numMaskChanges!=abs(numMaskChanges): #make sure its a positive integer
                        valid = False
                except ValueError: #if not an int
                    valid = False
                #determine if number of subscenes is valid:
                try:
                    numSubPer = int(numSubPer) #change into integer type
                    if numSubPer!=abs(numSubPer): #make sure its a positive integer
                        valid = False
                except ValueError: #if not an int
                    valid = False
                if valid:
                    self.RecVideo.setEnabled(True) #allow video to be recorded
                    self.SaveImages.setEnabled(True) #enable saving images
                    #write values to wirein endpoints
                    dev.SetWireInValue(0x11,exposure)
                    dev.UpdateWireIns()
                    dev.SetWireInValue(0x12,numMasks)
                    dev.UpdateWireIns()
                    dev.SetWireInValue(0x13,numMaskChanges)
                    dev.UpdateWireIns()
                    dev.SetWireInValue(0x14,numSubPer)
                    dev.UpdateWireIns()
                    #retrieve values on wireout endpoints
                    #dev.UpdateWireOuts()
                    #exposureRead = dev.GetWireOutValue(0x22)
                    #numMasksRead = dev.GetWireOutValue(0x23)
                    #numMaskChangesRead = dev.GetWireOutValue(0x24)
                    #activate the counter
                    dev.ActivateTriggerIn(0x53, 0x01)
                    #time.sleep(1)
                    global disp_on
                    disp_on = 1
                    capture_thread = threading.Thread(target=self.grab)
                    capture_thread.start()

                else:
                     #display error telling user to input valid parameters
                     errorBox = QtWidgets.QMessageBox()
                     errorBox.setWindowTitle('Error')
                     errorBox.setText('Please input valid parameter values.')
                     errorBox.addButton(QtWidgets.QPushButton('OK'), QtWidgets.QMessageBox.YesRole)
                     errorBox.exec_()
                     self.DispImage.setChecked(False) #reset button
                     disp_on =0 
                
        else: #if display image button is not checked
            self.RecVideo.setEnabled(False) #disable recording video button
            self.SaveImages.setEnabled(False) #disable saving images
            disp_on = 0
            #stop recording
            filler= ""
    
    def grab(self):
        global disp_on,imgSave, frame
        while disp_on == 1:
            dev.UpdateTriggerOuts()
            if dev.IsTriggered(0x6A, 0x01):
                frameData = bytearray(262144)
                data = dev.ReadFromPipeOut(0xA0,frameData)
                if imgSave>0:
                    imgSave = imgSave -1
                    save = 1 #should save the current image
                else:
                    save = 0
                    self.SaveImages.setEnabled(True)
                    self.SaveImages.setChecked(False)
                showFrame(self.mplimg1.canvas.axes,
                          self.mplhist1.canvas.axes, 
                          frameData, frame, 1,save)
                showFrame(self.mplimg2.canvas.axes,
                          self.mplhist2.canvas.axes, 
                          frameData, frame, 2,save)
            elif dev.IsTriggered(0x6A,0x02):
                frameData = bytearray(176640)
                data = dev.ReadFromPipeOut(0xA0,frameData)
                if imgSave>0:
                    imgSave = imgSave -1
                    save = 1 #should save the current image
                else:
                    save = 0
                    self.SaveImages.setEnabled(True)
                    self.SaveImages.setChecked(False)
                self.showFrame(self.mplimg1.canvas.axes,
                          self.mplhist1.canvas.axes, 
                          frameData, frame, 1,save)
                self.showFrame(self.mplimg2.canvas.axes,
                          self.mplhist2.canvas.axes, 
                          frameData, frame, 2,save)
    def showFrame(self,imgplot, histplot, frameData, DispFrame, figure, imgsave):
        '''Display the image and histogram of one bucket from camera data
        Parameters:
            implot: axes on which the image is shown
            histplot: axes on which the histogram of the image is shown
            frameData: data from camera
            DispFrame: string indicating which data to display
            figure: 1 represents figure on left (bucket 1), 2 represents figure on right
            imgsave: flag, if imgsave ==1, the image should be saved
        '''
        row = 160
        N_adc = 4
        N_adcCh = 3
        N_mux = 46
        col = N_adc*N_adc*N_mux
        indiCol = 184
        ZT = np.zeros((row, col), np.uint8)
        Z = np.zeros((row, indiCol), np.uint8)
        for i in range(0, row):
            for j in range(0, N_adc):
                for k in range(0,N_adcCh):
                    for l in range(0, N_mux):
                        ZT[row-i-1,col-1-(j*N_adcCh*N_mux+(2-k)*N_mux+45-l)] = frameData[i*col+l*N_adc*N_adcCh+k*N_adc+j]
        if figure ==1: #left figure
            Z = ZT[:, 139:507:2] 
        else:#figure ==2 (right figure)
            Z = ZT[:, 138:506:2] 
        print(Z)
        if DispFrame =='ALL': 
            img = np.zeros((row,indiCol), np.uint8)
            img = Z
        elif DispFrame =='CEP':
            img = np.zeros((80,60,), np.uint8)
            img = Z[0:80,2:62]
        else: #DispFrame==2 #CEP-TOF
            img = np.zeros((160,120), np.uint8)
            img = Z[0:160,62:182]
        print(img)
        imgplot.imshow(img, "gray");
        histplot.hist(img.ravel(), bins = 256)
        if imgsave ==1: #if images should be saved
            self.storeImage(img, figure)
        global vidRec,video1, video2
        if vidRec ==1:
            if figure ==1:
                video1.write(img)
            else:
                video2.write(img)
    def storeImage(nparray, figure):
        '''
        '''
        global exposure, numMasks, numMaskChanges, numSubPer, frame
        im = Image.fromarray(nparray)
        currDir = os.getcwd()
        folder= os.path.join(currDir,'Bucket' + str(figure)+'_Exp'+str(exposure) +'_Patt'+str(numMasks)+'_'+str(numMaskChanges)+'_'+str(numSubPer)+'_'+str(frame))
        folderpath = Path(folder)
        if not folderpath.exists(): #check if folder exists yet, if not, create one
            os.mkdir(folder)
        i = 0
        filename = 'Bucket' +str(figure)+ '_Image'+str(i)+'.png'
        imagefile = os.path.join(folder,filename)
        while Path(imagefile).exists(): #check if image by the same name exists, if so, increase counter
            i+=1
            filename = 'Bucket1_Image'+str(i)+'.png'
            imagefile = os.path.join(folder,filename)
        im.save(imagefile)
    
    def save_img(self):
        #check if number of images is valid input
        #if the input is valid, save in imgSave
        #imgSave >0 means that there are images left to save
        global imgSave
        try:
            imgSave = int(self.NumImages.text()) #change into integer type
            if imgSave > 0: #make sure >=1
                self.SaveImages.setEnabled(False) #disable button 
            else:
                #make error box pop up if negative
                errorBox = QtWidgets.QMessageBox()
                errorBox.setWindowTitle('Error')
                errorBox.setText('Please input a value greater than 0.')
                errorBox.addButton(QtWidgets.QPushButton('OK'), QtWidgets.QMessageBox.YesRole)
                errorBox.exec_()
                imgSave = 0 #reset value
        except ValueError: #if not an int
            #make error box pop up if invalid 
            errorBox = QtWidgets.QMessageBox()
            errorBox.setWindowTitle('Error')
            errorBox.setText('Please input a positive integer.')
            errorBox.addButton(QtWidgets.QPushButton('OK'), QtWidgets.QMessageBox.YesRole)
            errorBox.exec_()
            imgSave = 0 #reset value
        
    def rec_video(self):
        global vidRec, video1, video2
        if (self.RecVideo.isChecked()):
            if str(bitfile)=="":
                errorBox = QtWidgets.QMessageBox()
                errorBox.setWindowTitle('Error')
                errorBox.setText('Please load bit file first.')
                errorBox.addButton(QtWidgets.QPushButton('OK'), QtWidgets.QMessageBox.YesRole)
                errorBox.exec_()
            else:
                #record video 
                vidRec = 1
                currDir = os.getcwd()
                folder= os.path.join(currDir,'Saved Videos')
                folderpath = Path(folder)
                if not folderpath.exists(): #check if folder exists yet, if not, create one
                    os.mkdir(folder)
                i = 0
                filename1 = 'Arrangement1_'+str(i)+'.avi'
                vidfile1 = os.path.join(folder,filename1)
                while Path(vidfile1).exists(): #check if video by the same name exists, if so, increase counter
                    i+=1
                    filename1 = 'Arrangement1_'+str(i)+'.avi'
                    vidfile1 = os.path.join(folder,filename1)
                filename2 = 'Arrangement2_'+str(i)+'.avi'
                vidfile2 = os.path.join(folder,filename2)
                video1 = cv2.VideoWriter(vidfile1, -1, 1, (184,160))
                video2 = cv2.VideoWriter(vidfile2, -1, 1, (184,160))
        else:
            #stop video

            vidRec = 0
            cv2.destroyAllWindows()
            video1.release()
            video2.release()
            
def main():
    
    app = QtWidgets.QApplication(sys.argv)  # A new instance of QApplication
    form = MBI_GUI()  # We set the form to be our app
    form.show()  # Show the form
    app.exec_()  # and execute the app

    
if __name__ == "__main__":
    main()