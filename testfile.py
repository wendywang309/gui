# -*- coding: utf-8 -*-
"""
Created on Mon May 15 12:14:00 2017

@author: Wendy
"""


import sys
from FrontPanelAPI import ok #must have in site-packages for this to work
import matplotlib.pylab as plt
import matplotlib.image as mpimg
import PIL.Image as img
import numpy as np
import cv2
from IPython.display import clear_output
get_ipython().magic(u'matplotlib tk')


dev = ok.okCFrontPanel()
deviceCount = dev.GetDeviceCount()
for i in range(deviceCount):
    print 'Device[{0}] Model: {1}'.format(i, dev.GetDeviceListModel(i))
    print 'Device[{0}] Serial: {1}'.format(i, dev.GetDeviceListSerial(i))


dev = ok.okCFrontPanel()
dev.OpenBySerial("")
error = dev.ConfigureFPGA("ok_imager.bit")
# Its a good idea to check for errors here


# IsFrontPanelEnabled returns true if FrontPanel is detected.
if True == dev.IsFrontPanelEnabled():
    print "FrontPanel host interface enabled."
else:
    sys.stderr.write("FrontPanel host interface not detected.")


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
im = np.zeros(shape=(row ,col))
im1 = np.zeros(shape=(row ,184))
im2 = np.zeros(shape=(row ,184))
#plt.figure(3)
#plt.imshow(im).set_cmap('gray')
#plt.show()


# assert reset signal to initialize the FIFO.
dev.SetWireInValue(0x10, 0xff, 0x01);
dev.UpdateWireIns();
# deactivate reset signal and activate counter.
dev.SetWireInValue(0x10, 0x00, 0x01);
dev.UpdateWireIns();
dev.SetWireInValue(0x11,1)
dev.UpdateWireIns()
dev.SetWireInValue(0x12,600)
dev.UpdateWireIns()
dev.SetWireInValue(0x13,2)
dev.UpdateWireIns()
dev.SetWireInValue(0x14,100)
dev.UpdateWireIns()


# Trigger the counter
dev.ActivateTriggerIn(0x53, 0x01)
cv2.namedWindow("im",cv2.WINDOW_NORMAL)
cv2.namedWindow("im1",cv2.WINDOW_NORMAL)
cv2.namedWindow("im2",cv2.WINDOW_NORMAL)
while True:
    # Check for FIFO flag
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
        im = im/255
        for i in range(row):
            im1[i] = im[i][139:507:2]
        for i in range(row):
            im2[i] = im[i][138:506:2]
        cv2.imshow('im1',im1)
        cv2.imshow('im2',im2)
        cv2.waitKey(1)
        # break
    # If one frame is ready in FIFO
    elif dev.IsTriggered(0x6A, 0x02) == True:
        dev.ReadFromPipeOut(0xA0, datain1)
        for i in range(row):
            for j in range(N_adc):
                for k in range(N_adcCh):
                    for l in range(N_mux):
                        im[row-1-i][col-1-(j*N_adcCh*N_mux+(2-k)*N_mux+45-l)] = datain1[i*col+l*N_adc*N_adcCh+k*N_adc+j]
        im = im/255
        for i in range(row):
            im1[i] = im[i][139:507:2]
        for i in range(row):
            im2[i] = im[i][138:506:2]
        cv2.imshow('im',im)
        cv2.imshow('im1',im1)
        cv2.imshow('im2',im2)
        cv2.waitKey(1)

