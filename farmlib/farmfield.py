import os
import random
import time


from farmlib.seed import Seed
from farmlib.dictmapper import DictMapper
from farmlib.farmobject import FarmObject, objects

MAXANTHILLS = 10
WILT_TIME = 12 # in hours

class FarmField:

    def __init__(self):
        """ Init FarmField"""

        self.farmtiles = {}

    def count_anthills(self):
        anthills = 0
        for f in self.farmtiles.values():
            if f["object"] and f["object"].id == 1:
                anthills += 1
        return anthills

    def get_farmtile(self, posx, posy):
        """Get farmtile from given position"""

        arg = str(posx) + 'x' + str(posy)
        if self.farmtiles.has_key(arg):
            return self.farmtiles[arg]

        else:
            self.farmtiles[arg] = self.newfarmtile()
            return self.farmtiles[arg]

    def get_farmtile_position(self, farmtile):
        """
            Return farmtile position by spliting farmtile key in 
            farmtiles dict.
        """
        for ft in self.farmtiles.keys():
            if self.farmtiles[ft] == farmtile:
                px = int(ft.split('x')[0])
                py = int(ft.split('x')[1])
                return (px, py)

    def set_farmtile(self, posx, posy, farmtile):
        """Set farmtile at given position"""

        arg = str(posx) + 'x' + str(posy)
        self.farmtiles[arg] = farmtile

    def newfarmtile(self, farmobject = None):
        """return new farmtile with keys set"""
        ft = {"water":0, "object":farmobject}
        return ft

    def plant(self, posx, posy, seed):
        """Plant a seed on the given farmtile position"""

        farmtile = self.get_farmtile(posx, posy)
        if not farmtile['object'] and isinstance(seed, Seed):
            #plant a new seed on empty place
            farmtile['object'] = seed
            seed.start_grow()
        else:
            return 1 #  error there something on that position

    def harvest(self, posx, posy, player):
        """Harvest growed seed from farmtile"""

        farmtile = self.get_farmtile(posx, posy)
        if not farmtile["object"]:return False

        if farmtile["object"].type == "seed":
            if not farmtile['object'].growing and \
                farmtile['object'].to_harvest:
                #harvest seeds
                for i in xrange(farmtile['object'].growquantity):
                    #
                    player.event_harvest(farmtile['object'])

                    itemid = farmtile['object'].id
                    if itemid not in player.inventory:
                        player.inventory.append(itemid)
                        player.itemscounter[str(itemid)] = 1
                    else:
                        player.itemscounter[str(itemid)] += 1
                #TODO: add feature to many years seeds
                farmtile['object'] = None
                farmtile['water'] = 0
                return True

    def wilt_plant(self, posx, posy):
        fobject = FarmObject()
        fobject.id = 8 #  Wilted plant
        fobject.apply_dict(objects[fobject.id])
        farmtile = self.newfarmtile(fobject)
        self.set_farmtile(posx, posy, farmtile)
        return True

    def removewilted(self, posx, posy, player):
        self.remove(posx, posy, player)

    def remove(self, posx, posy, player):
        self.set_farmtile(posx, posy, self.newfarmtile())

    def water(self, posx, posy):
        """Watering a farm tile"""

        farmtile = self.get_farmtile(posx, posy)
        if farmtile["object"] is None:return False
        if farmtile["object"].type != "seed":return False

        #only one per seed
        if farmtile['water'] < 30:
            farmtile['water'] = 100 #  min(farmtile['water']+10,100)
            watereffect = int(0.2 * farmtile['object'].growtime)
            farmtile['object'].growendtime -= watereffect
            return True
        else:return False

    def create_random_anthill(self, farmtile):
        fobject = FarmObject()
        fobject.id = 7 #  Anthill
        fobject.apply_dict(objects[fobject.id])
        farmtile["object"] = fobject
        return fobject

    def generate_random_stones(self):
        for x in xrange(random.randint(10, 15)):
            xx = random.randint(0, 11)
            yy = random.randint(0, 11)
            fobject = FarmObject()
            fobject.id = 6 #  Stone
            fobject.apply_dict(objects[fobject.id])
            farmtile = self.newfarmtile(fobject)
            self.set_farmtile(xx, yy, farmtile)

    def check_wilted(self, farmtile):
        if not farmtile['object']:return False

        fobject = farmtile['object']
        if fobject.type != "seed":return False

        if fobject.to_harvest:
            if time.time() > fobject.growendtime + WILT_TIME * 3600:

                #get position
                position = self.get_farmtile_position(farmtile)
                if not position:return False
                posx, posy = position

                self.wilt_plant(posx, posy)
                return True
        return False

    #UPDATE
    def update(self):
        """update a farmtiles"""

        modified = False

        #update each farmtile
        for farmtile in self.farmtiles.values():

            #Update objects
            if farmtile['object']:
                ret = farmtile['object'].update(farmtile)
                if ret:modified = True
                ret = self.check_wilted(farmtile)
                if ret:modified = True

            else:
                #Create anthills
                chance = random.randint(0, 10000)
                if chance == 1 and int(time.time()) % 600 == 0\
                    and self.count_anthills() < MAXANTHILLS:
                    self.create_random_anthill(farmtile)
                    return True
        return modified

    def save_farmfield(self, filename, player):
        data = DictMapper()
        data["inventory"] = player.inventory
        data["itemscounter"] = player.itemscounter
        data["money"] = player.money
        data["tiles"] = []

        #fill tiles
        for ftt in self.farmtiles.keys():
            ft = self.farmtiles[ftt]
            #skip when no seed
            if not ft['object']:continue

            gameobject = ft['object']
            tile = {}
            tile["px"] = int(ftt.split('x')[0])
            tile["py"] = int(ftt.split('x')[1])
            tile["water"] = ft["water"]

            tile["object"] = {}
            #seed data
            tile["object"]["type"] = gameobject.type
            tile["object"]['id'] = gameobject.id

            if gameobject.type == "seed":
                tile["object"]['growstarttime'] = gameobject.growstarttime
                tile["object"]['growendtime'] = gameobject.growendtime
                tile["object"]['growing'] = bool(gameobject.growing)
                tile["object"]['wilted'] = bool(gameobject.wilted)
                tile["object"]['to_harvest'] = bool(gameobject.to_harvest)
            #set tile
            data["tiles"].append(tile)
        #save data
        data.save("field.json")
        return True

    def load_farmfield(self, filename, player):
        if not os.path.isfile(filename):return False
        data = DictMapper()
        data.load(filename)
        player.inventory = data["inventory"]
        player.itemscounter = data["itemscounter"]
        player.money = data["money"]
        #load tiles
        for tile in data["tiles"]:
            px = tile["px"]
            py = tile["py"]
            #Port from old saves
            if "seed" in tile:
                tile["object"] = tile["seed"]
                tile["object"]["type"] == "seed"
            #Avoid null objects
            if not tile["object"]:continue

            #Restore seed or object
            if tile["object"]["type"] == "seed":
                newobject = Seed()

                newobject.id = tile["object"]["id"]
                newobject.type = tile["object"]["type"]

                newobject.to_harvest = tile["object"]["to_harvest"]
                newobject.wilted = tile["object"]["wilted"]
                newobject.growing = tile["object"]["growing"]
                newobject.growendtime = tile["object"]["growendtime"]
                newobject.growstarttime = tile["object"]["growstarttime"]

                farmtile = self.newfarmtile(newobject)
                farmtile["water"] = tile["water"]
                newobject.apply_dict(objects[newobject.id])
            else:
                newobject = FarmObject()

                newobject.id = tile["object"]["id"]
                newobject.type = tile["object"]["type"]
                #apply dict
                newobject.apply_dict(objects[newobject.id])
                farmtile = self.newfarmtile(newobject)
            #set farmtile
            self.set_farmtile(px, py, farmtile)
        #return
        return True
