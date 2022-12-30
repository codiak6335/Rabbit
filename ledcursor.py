import machine


def dim(color, percent): 
    dimmedColor = [None] * 3
    dimmedColor[0] = int(color[0] * percent)
    dimmedColor[1] = int(color[1] * percent)
    dimmedColor[2] = int(color[2] * percent)
    return dimmedColor

class CCursor:

    def __init__(self, LedStrand, colora, colorb, dimLevel):
        self.dimLevel = dimLevel
        self.iLeadingLeds = 5 + 1
        self.iTrailingLeds = 5
        self.iPipLocation = 6
        self.iPipLength = 11
        self.iPipBase = self.iPipLocation -self.iPipLength 
        self.aColorPrime = dim(colora, self.dimLevel)
        self.aColorSecond = dim(colorb, self.dimLevel)
        self.CLedStrand = LedStrand
        self.iFirstPixel = 0
        self.iPixelCount = 0
        self.lastPP = -1000


    def fillpip(self, color):
        # print (self.iFirstPixel, self.iPixelCount)
        i = self.iFirstPixel 
        for x in range(self.iPipLength):
             if (i >= self.CLedStrand.iLowestLed) and (i < self.CLedStrand.iHighestLed):
                self.CLedStrand.Strand[i] = color
             i+=1

    def Draw(self, PrimaryPixel, PipOn):
        if PipOn:
            
            print ("Primary Pixel :", PrimaryPixel)
            self.lastPP = PrimaryPixel

            self.fillpip((0,0,0))
            self.CLedStrand.draw15s()


            self.iFirstPixel = PrimaryPixel + self.iPipBase;
            self.fillpip(self.aColorSecond)

            if (PrimaryPixel >= self.CLedStrand.iLowestLed) and (PrimaryPixel < self.CLedStrand.iHighestLed):
                self.CLedStrand.Strand[PrimaryPixel] = self.aColorPrime

            self.CLedStrand.Strand.write()

