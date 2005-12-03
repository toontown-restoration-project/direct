
from direct.showbase.ShowBaseGlobal import *
#from DirectGui import *
#from PythonUtil import *
#from IntervalGlobal import *

#from otp.avatar import Avatar
from direct.directnotify import DirectNotifyGlobal
#import GhostWalker
#import GravityWalker
#import NonPhysicsWalker
#import PhysicsWalker
#if __debug__:
#    import DevWalker
from direct.task import Task


class ControlManager:
    notify = DirectNotifyGlobal.directNotify.newCategory("ControlManager")
    wantAvatarPhysicsIndicator = base.config.GetBool('want-avatar-physics-indicator', 0)
    wantAvatarPhysicsDebug = base.config.GetBool('want-avatar-physics-debug', 0)
    wantWASD = base.config.GetBool('want-WASD', 0)

    def __init__(self):
        assert self.notify.debugCall(id(self))
        self.enableJumpCounter = 1
        self.controls = {}
        self.currentControls = None
        self.isEnabled = 1
        #self.monitorTask = taskMgr.add(self.monitor, "ControlManager-%s"%(id(self)), priority=-1)
        inputState.watch("run", "running-on", "running-off")
        
        inputState.watch("forward", "arrow_up", "arrow_up-up")
        inputState.watch("forward", "control-arrow_up", "arrow_up-up")
        inputState.watch("forward", "shift-control-arrow_up", "arrow_up-up")
        inputState.watch("forward", "alt-arrow_up", "arrow_up-up")
        inputState.watch("forward", "control-alt-arrow_up", "arrow_up-up")
        inputState.watch("forward", "shift-arrow_up", "arrow_up-up")
        inputState.watch("forward", "force-forward", "force-forward-stop")
        
        inputState.watch("reverse", "arrow_down", "arrow_down-up")
        inputState.watch("reverse", "control-arrow_down", "arrow_down-up")
        inputState.watch("reverse", "shift-control-arrow_down", "arrow_down-up")
        inputState.watch("reverse", "alt-arrow_down", "arrow_down-up")
        inputState.watch("reverse", "control-alt-arrow_down", "arrow_down-up")
        inputState.watch("reverse", "shift-arrow_down", "arrow_down-up")
        
        inputState.watch("reverse", "mouse4", "mouse4-up")
        inputState.watch("reverse", "control-mouse4", "mouse4-up")
        inputState.watch("reverse", "shift-control-mouse4", "mouse4-up")
        inputState.watch("reverse", "alt-mouse4", "mouse4-up")
        inputState.watch("reverse", "control-alt-mouse4", "mouse4-up")
        inputState.watch("reverse", "shift-mouse4", "mouse4-up")

        inputState.watch("turnLeft", "arrow_left", "arrow_left-up")
        inputState.watch("turnLeft", "control-arrow_left", "arrow_left-up")
        inputState.watch("turnLeft", "shift-control-arrow_left", "arrow_left-up")
        inputState.watch("turnLeft", "alt-arrow_left", "alt-arrow_left-up")
        inputState.watch("turnLeft", "control-alt-arrow_left", "alt-arrow_left-up")
        inputState.watch("turnLeft", "shift-arrow_left", "arrow_left-up")
        inputState.watch("turnLeft", "mouse-look_left", "mouse-look_left-done")
        inputState.watch("turnLeft", "force-turnLeft", "force-turnLeft-stop")

        inputState.watch("turnRight", "arrow_right", "arrow_right-up")
        inputState.watch("turnRight", "control-arrow_right", "arrow_right-up")
        inputState.watch("turnRight", "shift-control-arrow_right", "arrow_right-up")
        inputState.watch("turnRight", "alt-arrow_right", "arrow_right-up")
        inputState.watch("turnRight", "control-alt-arrow_right", "arrow_right-up")
        inputState.watch("turnRight", "shift-arrow_right", "arrow_right-up")
        inputState.watch("turnRight", "mouse-look_right", "mouse-look_right-done")
        inputState.watch("turnRight", "force-turnRight", "force-turnRight-stop")

        if self.wantWASD:
            inputState.watch("forward", "w", "w-up")
            inputState.watch("forward", "control-w", "w-up")
            inputState.watch("forward", "shift-control-w", "w-up")
            inputState.watch("forward", "alt-w", "w-up")
            inputState.watch("forward", "control-alt-w", "w-up")
            inputState.watch("forward", "shift-w", "w-up")

            inputState.watch("reverse", "s", "s-up")
            inputState.watch("reverse", "control-s", "s-up")
            inputState.watch("reverse", "shift-control-s", "s-up")
            inputState.watch("reverse", "alt-s", "s-up")
            inputState.watch("reverse", "control-alt-s", "s-up")
            inputState.watch("reverse", "shift-s", "s-up")

            inputState.watch("slideLeft", "a", "a-up")
            inputState.watch("slideLeft", "control-a", "a-up")
            inputState.watch("slideLeft", "shift-control-a", "a-up")
            inputState.watch("slideLeft", "alt-a", "alt-a-up")
            inputState.watch("slideLeft", "control-alt-a", "alt-a-up")
            inputState.watch("slideLeft", "shift-a", "a-up")

            inputState.watch("slideRight", "d", "d-up")
            inputState.watch("slideRight", "control-d", "d-up")
            inputState.watch("slideRight", "shift-control-d", "d-up")
            inputState.watch("slideRight", "alt-d", "d-up")
            inputState.watch("slideRight", "control-alt-d", "d-up")
            inputState.watch("slideRight", "shift-d", "d-up")


            inputState.watch("turnLeft", "q", "q-up")
            inputState.watch("turnLeft", "control-q", "q-up")
            inputState.watch("turnLeft", "shift-control-q", "q-up")
            inputState.watch("turnLeft", "alt-q", "alt-q-up")
            inputState.watch("turnLeft", "control-alt-q", "alt-q-up")
            inputState.watch("turnLeft", "shift-q", "q-up")

            inputState.watch("turnRight", "e", "e-up")
            inputState.watch("turnRight", "control-e", "e-up")
            inputState.watch("turnRight", "shift-control-e", "e-up")
            inputState.watch("turnRight", "alt-e", "e-up")
            inputState.watch("turnRight", "control-alt-e", "e-up")
            inputState.watch("turnRight", "shift-e", "e-up")

        # Jump controls
        if self.wantWASD:
            inputState.watch("jump", "space", "space-up")
        else:
            inputState.watch("jump", "control", "control-up")



    def add(self, controls, name="basic"):
        """
        controls is an avatar control system.
        name is any key that you want to use to refer to the
            the controls later (e.g. using the use(<name>) call).
        
        Add a control instance to the list of available control systems.
        
        See also: use().
        """
        assert self.notify.debugCall(id(self))
        assert controls is not None
        oldControls = self.controls.get(name)
        if oldControls is not None:
            print "Replacing controls:", name
            oldControls.disableAvatarControls()
            oldControls.setCollisionsActive(0)
            oldControls.delete()
        controls.disableAvatarControls()
        controls.setCollisionsActive(0)
        self.controls[name] = controls

    def remove(self, name):
        """
        name is any key that was used to refer to the
            the controls when they were added (e.g. 
            using the add(<controls>, <name>) call).
        
        Remove a control instance from the list of available control systems.
        
        See also: add().
        """
        assert self.notify.debugCall(id(self))
        oldControls = self.controls.get(name)
        if oldControls is not None:
            print "Removing controls:", name
            oldControls.disableAvatarControls()
            oldControls.setCollisionsActive(0)
            oldControls.delete()
            del self.controls[name]

    if __debug__:
        def lockControls(self):
            self.ignoreUse=True

        def unlockControls(self):
            if hasattr(self, "ignoreUse"):
                del self.ignoreUse
    
    def use(self, name, avatar):
        """
        name is a key (string) that was previously passed to add().
        
        Use a previously added control system.
        
        See also: add().
        """
        assert self.notify.debugCall(id(self))
        if __debug__ and hasattr(self, "ignoreUse"):
            return
        controls = self.controls.get(name)

        if controls is not None:
            if controls is not self.currentControls:
                if self.currentControls is not None:
                    self.currentControls.disableAvatarControls()
                    self.currentControls.setCollisionsActive(0)
                    self.currentControls.setAvatar(None)
                self.currentControls = controls
                self.currentControls.setAvatar(avatar)
                self.currentControls.setCollisionsActive(1)
                if self.isEnabled:
                    self.currentControls.enableAvatarControls()
                messenger.send('use-%s-controls'%(name,), [avatar])
            #else:
            #    print "Controls are already", name
        else:
            print "Unkown controls:", name

    def setSpeeds(self, forwardSpeed, jumpForce,
            reverseSpeed, rotateSpeed):
        assert self.notify.debugCall(id(self))
        for controls in self.controls.values():
            controls.setWalkSpeed(
                forwardSpeed, jumpForce, reverseSpeed, rotateSpeed)

    def delete(self):
        assert self.notify.debugCall(id(self))
        self.disable()
        del self.controls
        del self.currentControls

        inputState.ignore("forward")
        inputState.ignore("reverse")
        inputState.ignore("turnLeft")
        inputState.ignore("turnRight")
        inputState.ignore("jump")
        inputState.ignore("run")

        if self.wantWASD:
            inputState.ignore("slideLeft")
            inputState.ignore("slideRight")
        
        #self.monitorTask.remove()
    
    def getSpeeds(self):
        return self.currentControls.getSpeeds()

    def setTag(self, key, value):
        assert self.notify.debugCall(id(self))
        for controls in self.controls.values():
            controls.setTag(key, value)

    def deleteCollisions(self):
        assert self.notify.debugCall(id(self))
        for controls in self.controls.values():
            controls.deleteCollisions()

    def collisionsOn(self):
        assert self.notify.debugCall(id(self))
        self.currentControls.setCollisionsActive(1)

    def collisionsOff(self):
        assert self.notify.debugCall(id(self))
        self.currentControls.setCollisionsActive(0)

    def placeOnFloor(self):
        assert self.notify.debugCall(id(self))
        self.currentControls.placeOnFloor()

    def enable(self):
        assert self.notify.debugCall(id(self))
        self.isEnabled = 1
        self.currentControls.enableAvatarControls()
    
    def disable(self):
        assert self.notify.debugCall(id(self))
        self.isEnabled = 0
        self.currentControls.disableAvatarControls()

    def enableAvatarJump(self):
        """
        Stop forcing the ctrl key to return 0's
        """
        assert self.notify.debugCall(id(self))
        self.enableJumpCounter+=1
        if self.enableJumpCounter:
            assert self.enableJumpCounter == 1
            self.enableJumpCounter = 1
            inputState.unforce("jump")

    def disableAvatarJump(self):
        """
        Force the ctrl key to return 0's
        """
        assert self.notify.debugCall(id(self))
        self.enableJumpCounter-=1
        if self.enableJumpCounter <= 0:
            inputState.force("jump", 0)
    
    def monitor(self, foo):
        #assert(self.debugPrint("monitor()"))
        #if 1:
        #    airborneHeight=self.avatar.getAirborneHeight()
        #    onScreenDebug.add("airborneHeight", "% 10.4f"%(airborneHeight,))
        if 0:
            onScreenDebug.add("InputState forward", "%d"%(inputState.isSet("forward")))
            onScreenDebug.add("InputState reverse", "%d"%(inputState.isSet("reverse")))
            onScreenDebug.add("InputState turnLeft", "%d"%(inputState.isSet("turnLeft")))
            onScreenDebug.add("InputState turnRight", "%d"%(inputState.isSet("turnRight")))
        return Task.cont
