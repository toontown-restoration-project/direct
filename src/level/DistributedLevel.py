"""DistributedLevel.py: contains the DistributedLevel class"""

from ClockDelta import *
from PythonUtil import Functor, sameElements, list2dict, uniqueElements
import ToontownGlobals
import DistributedObject
import LevelBase
import DirectNotifyGlobal
import EntityCreator

class DistributedLevel(DistributedObject.DistributedObject,
                       LevelBase.LevelBase):
    """DistributedLevel"""
    notify = DirectNotifyGlobal.directNotify.newCategory('DistributedLevel')

    WantVisibility = config.GetBool('level-visibility', 0)
    HideZones = config.GetBool('level-hidezones', 1)

    def __init__(self, cr):
        DistributedObject.DistributedObject.__init__(self, cr)
        LevelBase.LevelBase.__init__(self)

    def generate(self):
        self.notify.debug('generate')
        DistributedObject.DistributedObject.generate(self)

        self.setLevelId(self.doId)

        # this dict stores entity reparents if the parent hasn't been
        # created yet
        self.pendingEntId2ParentId = {}

        # Most (if not all) of the timed entities of levels
        # run on looping intervals that are started once based on
        # the level's start time.
        # This sync request is *NOT* guaranteed to finish by the time
        # the entities get created.
        # We should listen for any and all time-sync events and re-sync
        # all our entities at that time.
        toonbase.tcr.timeManager.synchronize('DistributedLevel.generate')

    # required fields
    def setZoneIds(self, zoneIds):
        self.notify.debug('setZoneIds: %s' % zoneIds)
        self.zoneIds = zoneIds

    def setStartTimestamp(self, timestamp):
        self.notify.debug('setStartTimestamp: %s' % timestamp)
        self.startTime = globalClockDelta.networkToLocalTime(timestamp,bits=32)

    def setScenarioIndex(self, scenarioIndex):
        self.scenarioIndex = scenarioIndex

    def initializeLevel(self, spec):
        """ subclass should call this as soon as it's located its spec data """
        LevelBase.LevelBase.initializeLevel(self, spec, self.scenarioIndex)
        # load stuff
        self.geom = loader.loadModel(self.spec['modelFilename'])

        def findNumberedNodes(baseString, model=self.geom, self=self):
            # finds nodes whose name follows the pattern 'baseString#'
            # where there are no characters after #
            # returns dictionary that maps # to node
            potentialNodes = model.findAllMatches(
                '**/%s*' % baseString).asList()
            num2node = {}
            for potentialNode in potentialNodes:
                name = potentialNode.getName()
                self.notify.debug('potential match for %s: %s' %
                                  (baseString, name))
                try:
                    num = int(name[len(baseString):])
                except:
                    continue
                
                num2node[num] = potentialNode

            return num2node

        # find the zones in the model and fix them up
        self.zoneNum2Node = findNumberedNodes('Zone')
        # add the UberZone
        self.zoneNum2Node[0] = self.geom

        # fix up the floor collisions for walkable zones
        for zoneNum, zoneNode in self.zoneNum2Node.items():
            # if this is a walkable zone, fix up the model
            floorColl = zoneNode.find('**/*FloorCollision*')
            if not floorColl.isEmpty():
                # rename the floor collision node, and make sure no other
                # nodes under the ZoneNode have that name
                floorCollName = 'Zone%sFloor' % zoneNum
                others = zoneNode.findAllMatches(
                    '**/%s' % floorCollName).asList()
                for other in others:
                    other.setName('%s_renamed' % floorCollName)
                floorColl.setName(floorCollName)

                # listen for zone enter events from floor collisions
                def handleZoneEnter(collisionEntry,
                                    self=self, zoneNum=zoneNum):
                    # eat the collisionEntry
                    self.enterZone(zoneNum)
                self.accept('enter%s' % floorCollName, handleZoneEnter)

        self.zoneNums = self.zoneNum2Node.keys()
        self.zoneNums.sort()
        self.notify.debug('zones: %s' % self.zoneNums)
        assert sameElements(self.zoneNums, self.spec['zones'].keys() + [0])

        # find the doorway nodes
        self.doorwayNum2Node = findNumberedNodes('Doorway')

        self.initVisibility()

        # create client-side Entities
        # TODO: only create client-side Entities for the
        # currently-visible zones?
        self.localEntities = {}
        for entId, spec in self.entId2Spec.iteritems():
            entity = EntityCreator.createEntity(spec['type'], self, entId)
            if entity is not None:
                self.localEntities[entId] = entity

        # there should not be any pending reparents left
        assert len(self.pendingEntId2ParentId) == 0

    def announceGenerate(self):
        self.notify.debug('announceGenerate')
        DistributedObject.DistributedObject.announceGenerate(self)

    def disable(self):
        self.notify.debug('disable')
        DistributedObject.DistributedObject.disable(self)
        self.ignoreAll()

        # destroy all of the local entities
        for entId, entity in self.localEntities.items():
            entity.destroy()
        del self.localEntities

        self.destroyLevel()

    def delete(self):
        self.notify.debug('delete')
        DistributedObject.DistributedObject.delete(self)

    def getDoorwayNode(self, doorwayNum):
        # returns node that doors should parent themselves to
        return self.doorwayNum2Node[doorwayNum]

    def requestReparent(self, entity, parent):
        if parent is 'zone':
            entity.reparentTo(self.zoneNum2Node[entity.zone])
        else:
            parentId = parent
            assert(entity.entId != parentId)

            if self.entities.has_key(parentId):
                # parent has already been created
                entity.reparentTo(self.entities[parentId])
            else:
                # parent hasn't been created yet; schedule the reparent
                self.notify.debug(
                    'entity %s requesting reparent to %s, not yet created' %
                    (entity, parent))
                entId = entity.entId
                self.pendingEntId2ParentId[entId] = parentId
                entity.reparentTo(hidden)
                # do the reparent once the parent is initialized
                def doReparent(entId=entId, parentId=parentId, self=self):
                    entity=self.getEntity(entId)
                    parent=self.getEntity(parentId)
                    self.notify.debug(
                        'performing pending reparent of %s to %s' %
                        (entity, parent))
                    entity.reparentTo(parent)
                    del self.pendingEntId2ParentId[entId]
                self.accept(self.getEntityCreateEvent(parentId), doReparent)

    def showZone(self, zoneNum):
        self.zoneNum2Node[zoneNum].show()

    def hideZone(self, zoneNum):
        self.zoneNum2Node[zoneNum].hide()

    def setTransparency(self, alpha, zone=None):
        self.geom.setTransparency(1)
        if zone is None:
            node = self.geom
        else:
            node = self.zoneNum2Node[zone]
        node.setAlphaScale(alpha)

    def initVisibility(self):
        # start out with every zone visible, since none of the zones have
        # been hidden
        self.curVisibleZoneNums = list2dict(self.zoneNums)
        # we have not entered any zone yet
        self.curZoneNum = None

        # TODO: make this data-driven
        firstZone = 16
        self.enterZone(firstZone)

    def enterZone(self, zoneNum):
        if not DistributedLevel.WantVisibility:
            return

        if zoneNum == self.curZoneNum:
            return
        
        print "enterZone %s" % zoneNum
        zoneSpec = self.spec['zones'][zoneNum]
        # use dicts to efficiently ensure that there are no duplicates
        visibleZoneNums = list2dict([zoneNum])
        visibleZoneNums.update(list2dict(zoneSpec['visibility']))

        if DistributedLevel.HideZones:
            # figure out which zones are new and which are going invisible
            # use dicts because it's faster to use dict.has_key(x)
            # than 'x in list'
            addedZoneNums = []
            removedZoneNums = []
            allVZ = dict(visibleZoneNums)
            allVZ.update(self.curVisibleZoneNums)
            for vz,None in allVZ.items():
                new = vz in visibleZoneNums
                old = vz in self.curVisibleZoneNums
                if new and old:
                    continue
                if new:
                    addedZoneNums.append(vz)
                else:
                    removedZoneNums.append(vz)
            # show the new, hide the old
            self.notify.debug('showing zones %s' % addedZoneNums)
            for az in addedZoneNums:
                self.showZone(az)
            self.notify.debug('hiding zones %s' % removedZoneNums)
            for rz in removedZoneNums:
                self.hideZone(rz)

        # convert the zone numbers into their actual zoneIds
        # always include Toontown and factory uberZones
        visibleZoneIds = [ToontownGlobals.UberZone, self.getZoneId(0)]
        for vz in visibleZoneNums.keys():
            visibleZoneIds.append(self.getZoneId(vz))
        assert(uniqueElements(visibleZoneIds))
        self.notify.debug('new viz list: %s' % visibleZoneIds)

        toonbase.tcr.sendSetZoneMsg(self.getZoneId(zoneNum), visibleZoneIds)
        self.curZoneNum = zoneNum
        self.curVisibleZoneNums = visibleZoneNums
