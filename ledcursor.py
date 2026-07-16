# noinspection PyTypeChecker
def dim(color, percent):
    dimmed_color = [None] * 3
    dimmed_color[0] = int(color[0] * percent)
    dimmed_color[1] = int(color[1] * percent)
    dimmed_color[2] = int(color[2] * percent)
    return dimmed_color


class CCursor:

    def __init__(self, led_strand, color_a, color_b, dim_level):
        self.dim_level = dim_level
        self.iLeadingLeds = 5 + 1
        self.iTrailingLeds = 5
        self.iPipLocation = 6
        self.iPipLength = 11
        self.iPipBase = self.iPipLocation - self.iPipLength
        self.aColorPrime = dim(color_a, self.dim_level)
        self.aColorSecond = dim(color_b, self.dim_level)
        self.CLedStrand = led_strand
        self.iFirstPixel = 0
        self.iPixelCount = 0
        self.lastPP = -1000
        self.pixelCount = 0

    def fill_pip(self, color):
        # print (self.iFirstPixel, self.iPixelCount)
        i = self.iFirstPixel
        for x in range(self.iPipLength):
            if (i >= self.CLedStrand.iLowestLed) and (i < self.CLedStrand.iHighestLed):
                self.CLedStrand.Strand[i] = color
            i += 1

    def draw(self, primary_pixel, pip_on):
        if pip_on:

            # print ("Primary Pixel :", PrimaryPixel)
            self.pixelCount += 1
            self.lastPP = primary_pixel

            self.fill_pip((0, 0, 0))
            self.CLedStrand.draw15s()

            self.iFirstPixel = primary_pixel + self.iPipBase
            self.fill_pip(self.aColorSecond)

            if (primary_pixel >= self.CLedStrand.iLowestLed) and (primary_pixel < self.CLedStrand.iHighestLed):
                self.CLedStrand.Strand[primary_pixel] = self.aColorPrime

            self.CLedStrand.Strand.write()
