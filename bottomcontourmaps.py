import json

import swimset


class BottomContourMaps:
    def __init__(self):
        self.bcms = []
        self.loadMaps()

    def loadMaps(self):
        with open('BottomContourMaps.json', 'rt') as f:
            self.bcms = json.load(f)
        return self.bcms

    def saveMaps(self):
        with open('BottomContourMaps.json', 'wt') as f:
            r = json.dumps(swimset.getBottomMap(False))
            f.write(r)


if __name__ == "__main__":
    bcm = BottomContourMaps()
    bcm.saveMaps()
    bcm.loadMaps()
    print(bcm.bcms)
