import json

import swimset


class BottomContourMaps:
    def __init__(self):
        self.bcms = []
        self.load()

    def load(self):
        with open('BottomContourMaps.json', 'rt') as f:
            self.bcms = json.load(f)
        return self.bcms

    def save(self):
        with open('BottomContourMaps.json', 'wt') as f:
            r = json.dumps(swimset.get_bottom_map())
            f.write(r)


if __name__ == "__main__":
    bcm = BottomContourMaps()
    bcm.save()
    bcm.load()
    print(bcm.bcms)
