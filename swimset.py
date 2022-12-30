#import gc 
#import array
#import random
#import sys
#import os
import machine
import neopixel
import time
#import random
from machine import Pin, PWM
from audioalert import CAudioAlert
from ledcursor import CCursor
from display import ST7789, Oled29       
import json

print('Micropython')


class BottomContourMaps:
    def __init__(self):
        self.bcms = []
        self.loadMaps()
    
    def loadMaps(self):
        with open('BottomContourMaps.json','rt') as f:
            self.bcms = json.load(f)
        return self.bcms
    
    def saveMaps(self):
        with open('BottomContourMaps.json','wt') as f:
            r = json.dumps(swimset.getBottomMap(False))
            f.write(r)



def getBottomMap(debug):
    bcm = BottomContourMaps()
    return bcm.loadMaps()

#    bsm = BottomSectionMap = [[5.5, 0, 10, 75]]
#    if not debug:
#        bsm = BottomSectionMap = [[5.5, 174, 251, 6], [12, 252, 326, 15], [12, 327, 526, 21], [5.5, 527, 890, 33]]
#    return bsm


class CLedStrand:
    def __init__(self, iPin, lowestLedNum, HighestLedNum):

        self.Strand = neopixel.NeoPixel(machine.Pin(iPin), HighestLedNum - lowestLedNum + 1)
        self.iLowestLed = lowestLedNum
        self.iHighestLed = HighestLedNum
        self.LightStrand()

        self.segment = 0
        
    def LightSegment(self):
        print(self.segment)
        self.Strand.fill((0,0,0))

        bsm = getBottomMap(debug)
        mark = bsm[self.segment]
        
        for x in range(mark[1], mark[2]):
            self.Strand[x] = (0,255,0)
        
        self.Strand.write()
        self.segment += 1
        if self.segment == len(bsm):
            self.segment = 0
            
            
    def LightStrand(self):
        self.Strand.fill((0,0,0))
        for x in range(self.iLowestLed,self.iHighestLed,5):
            self.Strand[x] = (255,255,255) 
        self.Strand.write()
        

    def ClearStrand(self):
        self.Strand.fill((0,0,0))
        self.Strand.write()
        

    def IgniteLedLoc(self, LedLoc, color = (255,255,255)):
        if (self.iLowestLed <= LedLoc <= self.iHighestLed):
            self.Strand.fill((0,0,0))
            self.Strand[LedLoc] = color
            self.Strand.write()
        


    def IgniteMarkers(self, debug):
        self.Strand.fill((0,0,0))
        self.Strand.write()
        
        bsm = getBottomMap(debug)
        for mark in bsm:
            self.Strand[mark[1]+self.iLowestLed] = (0,255,0) 
            self.Strand[mark[2]+self.iLowestLed] = (255,0,0) 
        self.Strand.write()
            

# Index Defines for BottomSectionMap array field
DEPTH = 0
LEDSTART = 1
LEDEND = 2
FEET = 3







class SwimSet:
    def __init__(self,  display, debug=True):
        self.display = display
        self.Direction = True
        self.dimLevel = 1  # This is a percentage
        self.STRANDLENGTH = 910
        self.FIRSTPIXEL = 174
        self.Stopped = True
        self.debug = debug
        if debug:
            self.dimLevel = .1  # This is a percentage
            self.FIRSTPIXEL = 0
            self.STRANDLENGTH = 21
            #self.BottomSectionMap = [[1, 0, 3, 37.5], [2, 4, 7, 7.5], [3, 8, 10, 30]]

        self.numpix = self.STRANDLENGTH - self.FIRSTPIXEL

        self.LedStrand = CLedStrand(16, 0,
                                    self.STRANDLENGTH - 1)  # numpix -1 is actually the highest pixel index, not the number of pixels


        self.Cursor = CCursor(self.LedStrand, (255, 255, 255), (255, 0, 0), self.dimLevel)


  
        self.ms_at_pixel_down = [0] * self.numpix
        self.ms_at_pixel_back = [0] * self.numpix

        self.lowestLed = 1000000
        self.highestLed = -1
        self.ms_buffer = [0] * 1000
        self.RunningMode = False
        
        self.AudioAlert = CAudioAlert()


    
    def useAudio(self,flag):
        self.AudioAlert.useAudio(flag)
        
    def SetBottomTimes(self, duration=120, distance = 200, interval = 180, repetitions = 20, length=25, direction=True):  # length in yards
        if direction:
            print("Near")
        else:
            print("Far")
        self.BottomSectionMap = getBottomMap(self.debug)
        self.Direction = direction
        self.duration = duration 
        self.distance = distance
        self.length = length
        self.interval = interval
        self.repetitions = repetitions
        print(self.duration,self.distance,self.length)
        self.seconds_per_length = (self.duration / (self.distance / self.length))
        print(self.seconds_per_length,self.numpix)
        self.seconds_per_pixel = (self.seconds_per_length / (self.numpix))
        self.ms_sleep = int(self.seconds_per_length * 0.99999999)
        self.ms_per_length = self.seconds_per_length * 1000
        self.ms_per_pixel = int(self.seconds_per_pixel * 1000)
        self.ms_total_time = self.duration * 1000
        
        duration = self.ms_per_length
        poolLength = self.length
        # print(self.duration)
        Led = self.FIRSTPIXEL
        du = 0
        poolLengthInFeet = float(poolLength * 3.0)

        print("duration : ", duration)
        totalFeet = 0
        for section in self.BottomSectionMap:
            print("Sections : ", section)
            if section[LEDSTART] < self.lowestLed:
                self.lowestLed = section[LEDSTART]
            if self.highestLed <= section[LEDEND]:
                self.highestLed = section[LEDEND]
            percentageOfLength = float(float(section[FEET]) / poolLengthInFeet)
            sectionDuration = duration * percentageOfLength

            sectionLedCount = section[LEDEND] - section[LEDSTART] + 1
            ledMSStep = int(sectionDuration / sectionLedCount)
            # print ("percentageOfLength, sectionDuration, sectionLedCount, ledMSStep : ",percentageOfLength, sectionDuration, sectionLedCount, ledMSStep)

            for l in range(section[LEDSTART], section[LEDEND] + 1):
                du = ledMSStep
                self.ms_buffer[Led] = du
                Led += 1

        #self.ms_buffer[2] = 5000
        print(self.FIRSTPIXEL, self.lowestLed, self.highestLed)
        print("ms buffer : ", self.ms_buffer)
        
        self.TimeHacks = {} 
        self.TimeHacks[True] = [0] * 1000
        for x in range(self.lowestLed, self.highestLed):
            self.TimeHacks[True][x] = self.ms_buffer[x] + self.TimeHacks[True][x-1]
            
        self.TimeHacks[False] = [0] * 1000
        for x in range(self.highestLed, self.lowestLed,-1):
            self.TimeHacks[False][x] = self.ms_buffer[x] + self.TimeHacks[False][x+1]

        print("l buffer : ", self.TimeHacks[True])
        print("l buffer : ", self.TimeHacks[False])
        
        
        

    def StopSet(self):
        self.RunningMode = False


    def DirectionChanged(self):
        self.Direction = not self.Direction
        self.lapcount += 1
        if (self.currentPixel != self.lastPixel):
            self.lastPixel = self.currentPixel
            self.drawcount += 1
            self.Cursor.Draw(self.currentPixel, self.PipOn)

        t = self.ms_per_length 
        print(f"Direction Changed : {self.lapcount} {self.ms_per_length} {time.ticks_ms()} {self.startTimeOfThisLength} {time.ticks_diff(time.ticks_ms(),self.startTimeOfThisLength)} {self.drawcount}")
        self.drawcount = 0

        delay = int(self.ms_per_length -  (time.ticks_ms() - self.startTimeOfThisLength))      
        print(f"delay : {delay}")
        time.sleep_ms(delay)
        self.startTimeOfThisLength = time.ticks_ms()

        
        
    def NextPixel(self):
        #print(self.accumulatedTime, self.Direction, self.timeIndex, self.ms_buffer[self.timeIndex])
        returnValue = True
        currentPace = time.ticks_diff(time.ticks_ms(),self.startTimeOfThisLength) 
 #       print(f"in : {currentPace} {self.TimeHacks[True][self.currentPixel]} {self.currentPixel}")
        if self.Direction == True:
            while (currentPace > self.TimeHacks[True][self.currentPixel]):
                self.currentPixel += 1
                if self.currentPixel > self.maxtimeindex:
                    self.currentPixel = self.maxtimeindex
                    self.DirectionChanged()
                    returnValue = False
                    
                    break
        else:
            while (currentPace > self.TimeHacks[False][self.currentPixel]):
                self.currentPixel -= 1
                if self.currentPixel < self.lowestLed:
                    self.currentPixel = self.lowestLed
                    self.DirectionChanged()
                    returnValue = False
                    break
#        print(f"out : {currentPace} {self.TimeHacks[True][self.currentPixel]} {self.currentPixel}")
        return returnValue

            

    def Rep(self, reps):        
        self.PipOn = True
        
        self.maxtimeindex = self.highestLed
        self.currentPixel = self.lowestLed
        if self.Direction == False:
            self.timeIndex = self.maxtimeindex

        print("Direction Change : ", self.Direction)
        print(f"Rep starting: {self.currentPixel}")
        self.AudioAlert.Beep()

        s = time.ticks_ms() #Pycharm needs a *1000
        self.staticStartTime = s

        self.laptimeadjustment = 0
        self.lapcount = 0
        self.drawcount = 0
        
        self.startTimeOfThisLength = time.ticks_ms()
        while self.RunningMode:
            if time.ticks_diff(time.ticks_ms(),self.staticStartTime) >= self.ms_total_time:
                break;
            self.NextPixel()
            if (self.currentPixel != self.lastPixel):
                self.lastPixel = self.currentPixel
                self.drawcount += 1
                self.Cursor.Draw(self.currentPixel, self.PipOn)
            
        self.lastRepEnd = time.ticks_ms()
        self.LedStrand.Strand.fill((0, 0, 0))
        self.LedStrand.Strand.write()


    def Loop(self):
        self.Stopped = False
        self.RunningMode = True
        self.lastPixel = -1
        reps = 0
        while self.RunningMode and (self.repetitions==0 or reps < self.repetitions):
            self.display.fill(self.display.black) 
            self.display.text("FTL Fish v2.0",1,2,self.display.white)
            #self.OLED.text(netstr[0],1,12,self.OLED.white)
            self.display.text(f"Status: {reps} of {self.repetitions}",1,22,self.display.white)  
            self.display.show()
            
            
            startTime = time.ticks_ms()
    
            self.Rep(reps)
            
            if self.RunningMode:
                reps += 1;
                
                elapsedTime = time.ticks_diff(time.ticks_ms(),startTime)
                print (self.interval, elapsedTime)
                restInterval = (self.interval*1000 - elapsedTime) / 1000

                print(f"{reps} of {self.repetitions} repetitions completed.")
                
                if restInterval < 0 :
                    print("Slow poke, elapsedTime exceeded the interval!")  # should validate this on input and not allow it to happen
                    print("No rest for you!")
                else:
                    if reps < self.repetitions:
                        print("Resting Interval : ", restInterval)
                        time.sleep(restInterval)  
            
        self.Stopped = False            
        self.display.fill(self.display.black) 
        self.display.text("FTL Fish v2.0",1,2,self.display.white)
        #self.OLED.text(netstr[0],1,12,self.OLED.white)
        self.display.text(f"Status: Idle",1,22,self.display.white)  
        self.display.show()

if __name__ == "__main__":
    

    s = SwimSet(ST7789(),False)
    s.LedStrand.IgniteMarkers(s.debug)
    #s.SetBottomTimes(duration=120, distance = 200, interval = 150, repetitions = 0, length=25)
    s.SetBottomTimes(duration=120, distance = 200, interval =150, repetitions = 10, length=25, direction=True)
    s.Loop()
