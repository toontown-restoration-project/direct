from PandaObject import *
from DirectCameraControl import *
from DirectManipulation import *
from DirectSelection import *
from DirectGrid import *
from DirectGeometry import *
from DirectLights import *
import OnscreenText
import types
import __builtin__

DIRECT_FLASH_DURATION = 1.5

class DirectSession(PandaObject):

    def __init__(self):
        # Establish a global pointer to the direct object early on
        # so dependant classes can access it in their code
        __builtin__.direct = self
        self.drList = DisplayRegionList()
        self.dr = self.drList[0]
        self.camera = self.dr.camera
        self.iRay = self.dr.iRay

        self.group = render.attachNewNode('DIRECT')
        self.cameraControl = DirectCameraControl()
        self.manipulationControl = DirectManipulationControl()
        self.useObjectHandles()
        self.grid = DirectGrid()
        self.grid.disable()
        self.lights = DirectLights(direct.group)
        # Create some default lights
        self.lights.createDefaultLights()
        # But turn them off
        self.lights.allOff()

        # Initialize the collection of selected nodePaths
        self.selected = SelectedNodePaths()
        # Ancestry of currently selected object
        self.ancestry = []
        self.ancestryIndex = 0

        self.readout = OnscreenText.OnscreenText( '', 0.1, -0.95 )
        # Make sure readout is never lit or drawn in wireframe
        useDirectRenderStyle(self.readout)
        # self.readout.textNode.setCardColor(0.5, 0.5, 0.5, 0.5)
        self.readout.reparentTo( hidden )

        self.fControl = 0
        self.fAlt = 0
        self.fShift = 0

        self.pos = VBase3()
        self.hpr = VBase3()
        self.scale = VBase3()

        self.hitPt = Point3(0.0)

        # Lists for managing undo/redo operations
        self.undoList = []
        self.redoList = []
        
        # One run through the context task to init everything
        self.drList.updateContext()

        self.actionEvents = [
            ['select', self.select],
            ['deselect', self.deselect],
            ['deselectAll', self.deselectAll],
            ['highlightAll', self.selected.highlightAll],
            ['preRemoveNodePath', self.deselect],
            # Scene graph explorer functions
            ['SGENodePath_Select', self.select],
            ['SGENodePath_Deselect', self.deselect],
            ['SGENodePath_Flash', self.flash],
            ['SGENodePath_Isolate', self.isolate],
            ['SGENodePath_Toggle Vis', self.toggleVis],
            ['SGENodePath_Show All', self.showAllDescendants],
            ['SGENodePath_Delete', self.removeNodePath],
            ]
        self.keyEvents = ['left', 'right', 'up', 'down',
                          'escape', 'space', 'delete',
                          'shift', 'shift-up', 'alt', 'alt-up',
                          'control', 'control-up',
                          'page_up', 'page_down', 'tab',
                          '[', '{', ']', '}',
                          'b', 'c', 'f', 'l', 's', 't', 'v', 'w']
        self.mouseEvents = ['mouse1', 'mouse1-up',
                            'mouse2', 'mouse2-up',
                            'mouse3', 'mouse3-up']

    def enable(self):
        # Make sure old tasks are shut down
        self.disable()
	# Start all display region context tasks
        self.drList.spawnContextTask()
	# Turn on mouse Flying
	self.cameraControl.enableMouseFly()
        # Turn on object manipulation
        self.manipulationControl.enableManipulation()
        # Make sure list of selected items is reset
        self.selected.reset()
	# Accept appropriate hooks
	self.enableKeyEvents()
	self.enableMouseEvents()
	self.enableActionEvents()

    def disable(self):
	# Shut down all display region context tasks
        self.drList.removeContextTask()
	# Turn off camera fly
	self.cameraControl.disableMouseFly()
        # Turn off object manipulation
        self.manipulationControl.disableManipulation()
	self.disableKeyEvents()
	self.disableMouseEvents()
	self.disableActionEvents()

    def minimumConfiguration(self):
	# Remove context task
        self.drList.removeContextTask()
	# Turn off camera fly
	self.cameraControl.disableMouseFly()
	# Ignore keyboard and action events
	self.disableKeyEvents()
	self.disableActionEvents()
	# But let mouse events pass through
	self.enableMouseEvents()

    def destroy(self):
	self.disable()

    def reset(self):
	self.enable()

    # EVENT FUNCTIONS

    def enableActionEvents(self):
        for event in self.actionEvents:
            self.accept(event[0], event[1], extraArgs = event[2:])

    def enableKeyEvents(self):
        for event in self.keyEvents:
            self.accept(event, self.inputHandler, [event])

    def enableMouseEvents(self):
        for event in self.mouseEvents:
            self.accept(event, self.inputHandler, [event])

    def disableActionEvents(self):
        for event, method in self.actionEvents:
            self.ignore(event)

    def disableKeyEvents(self):
        for event in self.keyEvents:
            self.ignore(event)

    def disableMouseEvents(self):
        for event in self.mouseEvents:
            self.ignore(event)

    def inputHandler(self, input):
	# Deal with keyboard and mouse input
        if input == 'mouse1':
            messenger.send('handleMouse1')
        elif input == 'mouse1-up':
            messenger.send('handleMouse1Up')
        elif input == 'mouse2': 
            messenger.send('handleMouse2')
        elif input == 'mouse2-up':
            messenger.send('handleMouse2Up')
        elif input == 'mouse3': 
            messenger.send('handleMouse3')
        elif input == 'mouse3-up':
            messenger.send('handleMouse3Up')
        elif input == 'shift':
            self.fShift = 1
        elif input == 'shift-up':
            self.fShift = 0
        elif input == 'control':
            self.fControl = 1
        elif input == 'control-up':
            self.fControl = 0
        elif input == 'alt':
            self.fAlt = 1
        elif input == 'alt-up':
            self.fAlt = 0
        elif input == 'page_up':
            self.upAncestry()
        elif input == 'page_down':
            self.downAncestry()
        elif input == 'escape':
            self.deselectAll()
        elif input == 'delete':
            self.removeAllSelected()
        elif input == 'tab':
            self.toggleWidgetVis()
        elif input == 'b':
            base.toggleBackface()
        elif input == 'l':
            self.lights.toggle()
        elif input == 's':
            if self.selected.last:
                self.select(self.selected.last)
        elif input == 't':
            base.toggleTexture()
        elif input == 'v':
            self.selected.toggleVisAll()
        elif input == 'w':
            base.toggleWireframe()
        elif (input == '[') | (input == '{'):
            self.undo()
        elif (input == ']') | (input == '}'):
            self.redo()
        
    def select(self, nodePath, fMultiselect = 0, fResetAncestry = 1):
        dnp = self.selected.select(nodePath, fMultiselect)
        if dnp:
            messenger.send('preSelectNodePath', [dnp])
            if fResetAncestry:
                # Update ancestry
                self.ancestry = dnp.getAncestry()
                self.ancestry.reverse()
                self.ancestryIndex = 0
            # Update the readout
            self.readout.reparentTo(render2d)
            self.readout.setText(dnp.name)
            # Show the manipulation widget
            self.reparentWidgetTo('direct')
            # Update camera controls coa to this point
            # Coa2Camera = Coa2Dnp * Dnp2Camera
            mCoa2Camera = dnp.mCoa2Dnp * dnp.getMat(self.camera)
            row = mCoa2Camera.getRow(3)
            coa = Vec3(row[0], row[1], row[2])
            self.cameraControl.updateCoa(coa)
            # Adjust widgets size
            # This uses the additional scaling factor used to grow and
            # shrink the widget            
            self.widget.setScalingFactor(dnp.getRadius())
            # Spawn task to have object handles follow the selected object
            taskMgr.removeTasksNamed('followSelectedNodePath')
            t = Task.Task(self.followSelectedNodePathTask)
            t.dnp = dnp
            taskMgr.spawnTaskNamed(t, 'followSelectedNodePath')
            # Send an message marking the event
            messenger.send('selectedNodePath', [dnp])

    def followSelectedNodePathTask(self, state):
        mCoa2Render = state.dnp.mCoa2Dnp * state.dnp.getMat(render)
        decomposeMatrix(mCoa2Render,
                        self.scale,self.hpr,self.pos,
                        CSDefault)
        self.widget.setPosHpr(self.pos,self.hpr)
        return Task.cont

    def deselect(self, nodePath):
        dnp = self.selected.deselect(nodePath)
        if dnp:
            # Hide the manipulation widget
            self.reparentWidgetTo('hidden')
            self.readout.reparentTo(hidden)
            self.readout.setText(' ')
            taskMgr.removeTasksNamed('followSelectedNodePath')
            self.ancestry = []
            # Send an message marking the event
            messenger.send('deselectedNodePath', [dnp])

    def deselectAll(self):
        self.selected.deselectAll()
        # Hide the manipulation widget
        self.reparentWidgetTo('hidden')
        self.readout.reparentTo(hidden)
        self.readout.setText(' ')
        taskMgr.removeTasksNamed('followSelectedNodePath')

    def flash(self, nodePath = 'None Given'):
        """ Highlight an object by setting it red for a few seconds """
        # Clean up any existing task
        taskMgr.removeTasksNamed('flashNodePath')
        # Spawn new task if appropriate
        if nodePath == 'None Given':
            # If nothing specified, try selected node path
            nodePath = self.selected.last
        if nodePath:
            if nodePath.hasColor():
                doneColor = nodePath.getColor()
                flashColor = VBase4(1) - doneColor
                flashColor.setW(1)
            else:
                doneColor = None
                flashColor = VBase4(1,0,0,1)
            # Temporarily set node path color
            nodePath.setColor(flashColor)
            # Clean up color in a few seconds
            t = taskMgr.spawnTaskNamed(
                Task.doLater(DIRECT_FLASH_DURATION,
                             # This is just a dummy task
                             Task.Task(self.flashDummy),
                             'flashNodePath'),
                'flashNodePath')
            t.nodePath = nodePath
            t.doneColor = doneColor
            # This really does all the work
            t.uponDeath = self.flashDone

    def flashDummy(self, state):
        # Real work is done in upon death function
        return Task.done
        
    def flashDone(self,state):
        # Return node Path to original state
        if state.doneColor:
            state.nodePath.setColor(state.doneColor)
        else:
            state.nodePath.clearColor()

    def isolate(self, nodePath = 'None Given'):
        """ Show a node path and hide its siblings """
        # First kill the flashing task to avoid complications
        taskMgr.removeTasksNamed('flashNodePath')
        # Use currently selected node path if node selected
        if nodePath == 'None Given':
            nodePath = self.selected.last
        # Do we have a node path?
        if nodePath:
            # Yes, show everything in level
            self.showAllDescendants(nodePath.getParent())
            # Now hide all of this node path's siblings
            nodePath.hideSiblings()

    def toggleVis(self, nodePath = 'None Given'):
        """ Toggle visibility of node path """
        # First kill the flashing task to avoid complications
        taskMgr.removeTasksNamed('flashNodePath')
        if nodePath == 'None Given':
            # If nothing specified, try selected node path
            nodePath = self.selected.last
        if nodePath:
            # Now toggle node path's visibility state
            nodePath.toggleVis()

    def removeNodePath(self, nodePath = 'None Given'):
        if nodePath == 'None Given':
            # If nothing specified, try selected node path
            nodePath = self.selected.last
        if nodePath:
            nodePath.remove()

    def removeAllSelected(self):
        self.selected.removeAll()

    def showAllDescendants(self, nodePath = render):
        """ Show the level and its descendants """
	nodePath.showAllDescendants()
	nodePath.hideCollisionSolids()

    def upAncestry(self):
        if self.ancestry:
            l = len(self.ancestry)
            i = self.ancestryIndex + 1
            if i < l:
                np = self.ancestry[i]
                name = np.getName()
                if (name != 'render') & (name != 'renderTop'):
                    self.ancestryIndex = i
                    self.select(np, 0, 0)
                    self.flash(np)

    def downAncestry(self):
        if self.ancestry:
            l = len(self.ancestry)
            i = self.ancestryIndex - 1
            if i >= 0:
                np = self.ancestry[i]
                name = np.getName()
                if (name != 'render') & (name != 'renderTop'):
                    self.ancestryIndex = i
                    self.select(np, 0, 0)
                    self.flash(np)

    # UNDO REDO FUNCTIONS
    
    def pushUndo(self, nodePathList, fResetRedo = 1):
        # Assemble group of changes
        undoGroup = []
        for nodePath in nodePathList:
            pos = nodePath.getPos()
            hpr = nodePath.getHpr()
            scale = nodePath.getScale()
            undoGroup.append([nodePath, pos,hpr,scale])
        # Now record group
        self.undoList.append(undoGroup)
        # Truncate list
        self.undoList = self.undoList[-25:]
        # Alert anyone who cares
        messenger.send('pushUndo')
        if fResetRedo & (nodePathList != []):
            self.redoList = []
            messenger.send('redoListEmpty')

    def popUndoGroup(self):
        # Get last item
        undoGroup = self.undoList[-1]
        # Strip last item off of undo list
        self.undoList = self.undoList[:-1]
        # Update state of undo button
        if not self.undoList:
            messenger.send('undoListEmpty')
        # Return last item
        return undoGroup
        
    def pushRedo(self, nodePathList):
        # Assemble group of changes
        redoGroup = []
        for nodePath in nodePathList:
            pos = nodePath.getPos()
            hpr = nodePath.getHpr()
            scale = nodePath.getScale()
            redoGroup.append([nodePath, pos,hpr,scale])
        # Now record redo group
        self.redoList.append(redoGroup)
        # Truncate list
        self.redoList = self.redoList[-25:]
        # Alert anyone who cares
        messenger.send('pushRedo')

    def popRedoGroup(self):
        # Get last item
        redoGroup = self.redoList[-1]
        # Strip last item off of redo list
        self.redoList = self.redoList[:-1]
        # Update state of redo button
        if not self.redoList:
            messenger.send('redoListEmpty')
        # Return last item
        return redoGroup
        
    def undo(self):
        if self.undoList:
            # Get last item off of redo list
            undoGroup = self.popUndoGroup()
            # Record redo information
            nodePathList = map(lambda x: x[0], undoGroup)
            self.pushRedo(nodePathList)
            # Now undo xform for group
            for pose in undoGroup:
                # Undo xform
                pose[0].setPosHprScale(pose[1], pose[2], pose[3])
            # Alert anyone who cares
            messenger.send('undo')

    def redo(self):
        if self.redoList:
            # Get last item off of redo list
            redoGroup = self.popRedoGroup()
            # Record undo information
            nodePathList = map(lambda x: x[0], redoGroup)
            self.pushUndo(nodePathList, fResetRedo = 0)
            # Redo xform
            for pose in redoGroup:
                pose[0].setPosHprScale(pose[1], pose[2], pose[3])
            # Alert anyone who cares
            messenger.send('redo')

    # UTILITY FUNCTIONS
    def useObjectHandles(self):
        self.widget = self.manipulationControl.objectHandles

    def hideReadout(self):
	self.readout.reparentTo(hidden)

    def reparentWidgetTo(self, parent):
        if parent == 'direct':
            self.widget.reparentTo(direct.group)
            self.widgetParent = 'direct'
        else:
            self.widget.reparentTo(hidden)
            self.widgetParent = 'hidden'

    def toggleWidgetVis(self):
        if self.widgetParent == 'direct':
            self.reparentWidgetTo('hidden')
        else:
            self.reparentWidgetTo('direct')

class DisplayRegionList:
    def __init__(self):
        self.displayRegionList = []
        for camera in base.cameraList:
            self.displayRegionList.append(
                DisplayRegionContext(base.win, camera))

    def __getitem__(self, index):
        return self.displayRegionList[index]

    def updateContext(self):
        for dr in self.displayRegionList:
            dr.contextTask(None)
        
    def spawnContextTask(self):
        for dr in self.displayRegionList:
            dr.start()

    def removeContextTask(self):
        for dr in self.displayRegionList:
            dr.stop()

    def setNearFar(self, near, far):
        for dr in self.displayRegionList:
            dr.camNode.setNearFar(near, far)
    
    def setNear(self, near):
        for dr in self.displayRegionList:
            dr.camNode.setNear(near)
    
    def setFar(self, far):
        for dr in self.displayRegionList:
            dr.camNode.setFar(far)

    def setFov(self, hfov, vfov):
        for dr in self.displayRegionList:
            dr.camNode.setFov(hfov, vfov)

    def setHfov(self, fov):
        for dr in self.displayRegionList:
            dr.camNode.setHfov(fov)

    def setVfov(self, fov):
        for dr in self.displayRegionList:
            dr.camNode.setVfov(fov)

class DisplayRegionContext:
    def __init__(self, win, camera):
        self.win = win
        self.camera = camera
        self.cam = self.camera.find('**/+Camera')
        self.camNode = self.cam.getNode(0)
        self.iRay = SelectionRay(self.camera)
        self.nearVec = Vec3(0)
        self.mouseX = 0.0
        self.mouseY = 0.0

    def __getitem__(self,key):
        return self.__dict__[key]

    def start(self):
        # First shutdown any existing task
        self.stop()
        # Start a new context task
        self.spawnContextTask()

    def stop(self):
        # Kill the existing context task
        taskMgr.removeTasksNamed('DIRECTContextTask')

    def spawnContextTask(self):
        taskMgr.spawnTaskNamed(Task.Task(self.contextTask),
                               'DIRECTContextTask')

    def removeContextTask(self):
        taskMgr.removeTasksNamed('DIRECTContextTask')

    def contextTask(self, state):
        # Window Data
        self.width = self.win.getWidth()
        self.height = self.win.getHeight()
        self.near = self.camNode.getNear()
        self.far = self.camNode.getFar()
        self.fovH = self.camNode.getHfov()
        self.fovV = self.camNode.getVfov()
        self.nearWidth = math.tan(deg2Rad(self.fovH / 2.0)) * self.near * 2.0
        self.nearHeight = math.tan(deg2Rad(self.fovV / 2.0)) * self.near * 2.0
        self.left = -self.nearWidth/2.0
        self.right = self.nearWidth/2.0
        self.top = self.nearHeight/2.0
        self.bottom = -self.nearHeight/2.0
        # Mouse Data
        # Last frame
        self.mouseLastX = self.mouseX
        self.mouseLastY = self.mouseY
        # Values for this frame
        # This ranges from -1 to 1
        if (base.mouseWatcher.node().hasMouse()):
            self.mouseX = base.mouseWatcher.node().getMouseX()
            self.mouseY = base.mouseWatcher.node().getMouseY()
        # Delta percent of window the mouse moved
        self.mouseDeltaX = self.mouseX - self.mouseLastX
        self.mouseDeltaY = self.mouseY - self.mouseLastY
        self.nearVec.set((self.nearWidth/2.0) * self.mouseX,
                         self.near,
                         (self.nearHeight/2.0) * self.mouseY)
        # Continue the task
        return Task.cont

