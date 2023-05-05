#!/usr/bin/env python

# setup and import
from picamera import PiCamera
import time
import adcUtil as adc
import numpy as np
import datetime
import RPi.GPIO as GPIO
from threading import Thread
import subprocess

# setup and initialize
gatePin = 27 # pin for microphone gate
GPIO.setmode(GPIO.BCM)
GPIO.setup(gatePin, GPIO.IN) # GPIO numbering

# initialize data set size and moving average window size
nData = 10000
micData = 10000
windowSize = 15

# linux command that will be called as a subprocess to stream camera to vlc player
cmd_str = "raspivid -o - -t 60000 -hf -w 800 -h 400 -fps 12 | cvlc --play-and-exit -vvv stream:///dev/stdin --sout '#rtp{sdp=rtsp://:8554/}' :demux=h264"

# -t is the timeout of the stream in ms, setting the -t flag to 0 will run stream indefinitely. 
# In VLC viewer, go to File > Open Network, in the text box type the following: rtsp://"pi_ip_address":8554/ to view
# on a device on the same network.




def getPiezoData(dataSize, windowSize): # function to read piezo data (motion detector)
    dPiezo = np.zeros(dataSize, dtype='float')
    
    for i in range(dataSize):
        dPiezo[i] = adc.readADC(channel=0, device=0)
    
    movingWindow = np.ones(windowSize)/windowSize
    movPie = np.convolve(dPiezo, movingWindow)
    global avgSum
    avgSum = np.average(movPie)
    





def getPhotoData(): # function to read photoresistor data (light detector)
    Vou = adc.readADC(channel=1, device=0)

    Vin = 3.3 # volts
    r2 = 10 #kOhm

    # photo resistance
    global R
    R = r2 * (Vin/Vou - 1)




def getMicData(dataSize, gatePin): # function to store microphone gate data (sound detector)
    dMic = np.zeros(dataSize)
    
    for i in range(dataSize):
        dMic[i] = GPIO.input(gatePin)
        
    micSum = np.sum(dMic)
    return micSum


# Main program
try:
    while True:

        while adc.readADC(channel=0, device=0) <=3.0: # while there is no motion detected do nothing
            pass


        # motion detected begin inspecting the area with the sensors.
        pi = Thread(target=getPiezoData, args=(nData, windowSize)) # initialize piezo thread
        photo = Thread(target=getPhotoData) # initialize photoresistor thread.

        pi.start() # begin threads for photo resistor and piezo to run in parallel execution
        photo.start()

        pi.join()
        photo.join() # wait to finish

        micSum = getMicData(micData, gatePin) # check the microphone data to detect voices/sound

        if (avgSum >= 0.2 and micSum >= 10) or R < 6.0: # turn camera on if sensor data are above thresholds
               subprocess.run(cmd_str, shell=True) # call bash command to stream to monitor and vlc via rtsp protocol.

except(KeyboardInterrupt, SystemExit):
    print("Interrupt!")

finally:
    print("Done!")
    GPIO.cleanup() # close GPIO