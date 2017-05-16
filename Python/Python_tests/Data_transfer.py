import ok
import sys

dev = ok.okCFrontPanel()

deviceCount = dev.GetDeviceCount()
for i in range(deviceCount):
    print 'Device[{0}] Model: {1}'.format(i, dev.GetDeviceListModel(i))
    print 'Device[{0}] Serial: {1}'.format(i, dev.GetDeviceListSerial(i))

# data buffer in Python (mutable type bytearray) must be initialized upon declaration
dataout = bytearray('abcdefghijklmnopqrstuvwxyzabcdef')
datain = bytearray('00000000000000000000000000000000')

dev.OpenBySerial("")
error = dev.ConfigureFPGA("data_transfer.bit")
# Its a good idea to check for errors here

# IsFrontPanelEnabled returns true if FrontPanel is detected.
if True == dev.IsFrontPanelEnabled():
    print "FrontPanel host interface enabled."
else:
    sys.stderr.write("FrontPanel host interface not detected.")

# Send brief reset signal to initialize the FIFO.
dev.SetWireInValue(0x10, 0xff, 0x01);
dev.UpdateWireIns();
dev.SetWireInValue(0x10, 0x00, 0x01);
dev.UpdateWireIns();

# Retreive values from FIFO
dev.UpdateWireOuts()
A = dev.GetWireOutValue(0x21)
print ("Initial FIFO outputs: ", A)

# Send buffer to PipeIn endpoint with address 0x80
data = dev.WriteToPipeIn(0x80, dataout)
print ("data length write: " + str(data))
# Read to buffer from PipeOut endpoint with address 0xA0
data = dev.ReadFromPipeOut(0xA0, datain)
print ("data length read: " + str(data))
print ("data read from XEM6310: " + datain)

dev.UpdateWireOuts()
A = dev.GetWireOutValue(0x21)
print ("Initial FIFO outputs: ", A)
