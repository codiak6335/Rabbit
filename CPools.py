import ujson


class CPool:
    def __init__(self, data):
        self.lanes = None
        self.__dict__ = data

    def add_lane(self, lane_number, segments):
        self.lanes["number"] = lane_number
        self.lanes["segments"] = segments

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)


class CPools:
    def __init__(self):
        self.pools_filename = "/data/Pools.json"
        self.pools = []

    def save(self):
        with open(self.pools_filename, 'w') as file:
            for pool in self.pools:
                file.write(str(pool.__dict__) + '\n')

    def load(self):

        self.pools = []

        with open(self.pools_filename, 'r') as f:
            for line in f:
                settings_string = line

                n = settings_string.replace("\'", "\"")

                print("[", n, "]")
                uj = ujson.loads(n)
                print(uj)
                pool = CPool(uj)
                self.pools.append(pool)

        return self.pools


if __name__ == "__main__":

    pools = CPools()
    lp = pools.load()
    print("list")

    for p in lp:
        print(p.__dict__)

    pools.save()

"""    
    pool = CPool("Bellevue East")
    pool.addLane(5, [[5.5, 174, 251, 6], [12, 252, 326, 15], [12, 327, 526, 21], [5.5, 527, 890, 33]])
    pools.AddPool(pool)

    pool = CPool("Bellevue West")
    pool.addLane(3, [[5.5, 174, 251, 6], [12, 252, 326, 15], [12, 327, 526, 21], [5.5, 527, 890, 33]])
    pools.AddPool(pool)

    pool = CPool("Brownell Talbot")
    pool.addLane(3, [])
    pools.AddPool(pool)

    pool = CPool("Ralston")
    pool.addLane(3, [])
    pools.AddPool(pool)

"""
