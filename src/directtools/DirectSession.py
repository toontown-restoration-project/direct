from PandaObject import *
from DirectUtil import*
from DirectCameraControl import *
from DirectManipulation import *
from DirectSelection import *
from DirectGrid import *
from DirectGeometry import *
from DirectLights import *
from DirectSessionPanel import *
from ClusterClient import *
from ClusterServer import *
from tkSimpleDialog import askstring
import Placer
import Slider
import SceneGraphExplorer
import OnscreenText
import types
import string
import __builtin__

DIRECT_FLASH_DURATION = 1.5

class DirectSession(PandaObject):

    def __init__(self):
        # Establish a global pointer to the direct object early on
        # so dependant classes can access it in their code
        __builtin__.direct = self
        # These come early since they are used later on
        self.group = render.attachNewNode('DIRECT')
        # Set priority to 100 so it always is textured
        # Call class method to avoid conflict with ToontownLoader
        self.font = Loader.Loader.loadFont(loader,
                                           "models/fonts/Comic",
                                           priority = 100)
        self.fEnabled = 0
        self.drList = DisplayRegionList()
        self.iRayList = map(lambda x: x.iRay, self.drList)
        self.dr = self.drList[0]
        self.camera = base.cameraList[0]
        self.trueCamera = self.camera
        self.iRay = self.dr.iRay

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
        self.activeParent = None

        self.selectedNPReadout = OnscreenText.OnscreenText(
            pos = (-1.0, -0.9), bg=Vec4(1,1,1,1),
            scale = 0.05, align = TextNode.ALeft,
            mayChange = 1, font = self.font)
        # Make sure readout is never lit or drawn in wireframe
        useDirectRenderStyle(self.selectedNPReadout)
        self.selectedNPReadout.reparentTo( hidden )

        self.activeParentReadout = OnscreenText.OnscreenText(
            pos = (-1.0, -0.975), bg=Vec4(1,1,1,1),
            scale = 0.05, align = TextNode.ALeft,
            mayChange = 1, font = self.font)
        # Make sure readout is never lit or drawn in wireframe
        useDirectRenderStyle(self.activeParentReadout)
        self.activeParentReadout.reparentTo( hidden )

        self.directMessageReadout = OnscreenText.OnscreenText(
            pos = (-1.0, 0.9), bg=Vec4(1,1,1,1),
            scale = 0.05, align = TextNode.ALeft,
            mayChange = 1, font = self.font)
        # Make sure readout is never lit or drawn in wireframe
        useDirectRenderStyle(self.directMessageReadout)
        self.directMessageReadout.reparentTo( hidden )

        # Create a vrpn client vrpn-server or default
        self.deviceManager = None
        self.joybox = None
        self.radamec = None
        self.fastrak = []
        if base.config.GetBool('want-vrpn', 0):
            import DirectDeviceManager
            self.deviceManager = DirectDeviceManager.DirectDeviceManager()
            # Automatically create any devices specified in config file
            joybox = base.config.GetString('vrpn-joybox-device', '')
            radamec = base.config.GetString('vrpn-radamec-device', '')
            fastrak = base.config.GetString('vrpn-fastrak-device', '')
            if joybox:
                import DirectJoybox
                self.joybox = DirectJoybox.DirectJoybox(joybox)
            if radamec:
                import DirectRadamec
                self.radamec = DirectRadamec.DirectRadamec(radamec)
            if fastrak:
                import DirectFastrak
                # parse string into format device:N where N is the sensor name
                fastrak = string.split(fastrak)
                for i in range(len(fastrak))[1:]:
                    self.fastrak.append(DirectFastrak.DirectFastrak(fastrak[0] + ':' + fastrak[i]))
                
            
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
        self.drList.camUpdate('')

        self.actionEvents = [
            ['select', self.select],
            ['deselect', self.deselect],
            ['deselectAll', self.deselectAll],
            ['highlightAll', self.selected.highlightAll],
            ['preRemoveNodePath', self.deselect],
            # Scene graph explorer functions
            ['SGE_Select', self.select],
            ['SGE_Deselect', self.deselect],
            ['SGE_Set Parent', self.setActiveParent],
            ['SGE_Reparent', self.reparent],
            ['SGE_WRT Reparent', lambda np, s=self: s.reparent(np, fWrt = 1)],
            ['SGE_Flash', self.flash],
            ['SGE_Isolate', self.isolate],
            ['SGE_Toggle Vis', self.toggleVis],
            ['SGE_Show All', self.showAllDescendants],
            ['SGE_Fit', self.fitOnNodePath],
            ['SGE_Place', Placer.place],
            ['SGE_Set Color', Slider.rgbPanel],
            ['SGE_Explore', SceneGraphExplorer.explore],
            ['SGE_Delete', self.removeNodePath],
            ['SGE_Set Name', self.getAndSetName],
            ]
        self.keyEvents = ['escape', 'delete', 'control', 'control-up',
                          'shift', 'shift-up', 'alt', 'alt-up',
                          'page_up', 'page_down', 
                          '[', '{', ']', '}',
                          'shift-a', 'b', 'l', 'shift-l', 'o', 'p', 'r',
                          'shift-r', 's', 't', 'v', 'w']
        self.mouseEvents = ['mouse1', 'shift-mouse1', 'control-mouse1',
                            'alt-mouse1', 'mouse1-up',
                            'mouse2', 'shift-mouse2', 'control-mouse2',
                            'alt-mouse2', 'mouse2-up',
                            'mouse3', 'mouse3-up']

        if base.wantTk:
            import TkGlobal
            self.panel = DirectSessionPanel(parent = tkroot)

        self.clusterMode = base.config.GetString("cluster-mode", '')
        if self.clusterMode == 'client':
            self.cluster = createClusterClient()
        elif self.clusterMode == 'server':
            self.cluster = ClusterServer(base.cameraList[0], base.camList[0])
        else:
            self.cluster = DummyClusterClient()
        __builtin__.cluster = self.cluster
            
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
        # Set flag
        self.fEnabled = 1

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
        # Set flag
        self.fEnabled = 0

    def toggleDirect(self):
        if self.fEnabled:
            self.disable()
        else:
            self.enable()

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

    def oobe(self):
        # If oobeMode was never set, set it to false and create the
        # structures we need to implement OOBE.
        try:
            self.oobeMode
        except:
            self.oobeMode = 0

            self.oobeCamera = hidden.attachNewNode('oobeCamera')

            self.oobeVis = loader.loadModelOnce('models/misc/camera')
            if self.oobeVis:
                self.oobeVis.node().setFinal(1)

        if self.oobeMode:
            # Position a target point to lerp the oobe camera to
            direct.cameraControl.camManipRef.iPosHpr(self.trueCamera)
            t = self.oobeCamera.lerpPosHpr(
                Point3(0), Vec3(0), 2.0,
                other = direct.cameraControl.camManipRef,
                task = 'manipulateCamera',
                blendType = 'easeInOut')
            # When move is done, switch to oobe mode
            t.uponDeath = self.endOOBE
        else:
            # Place camera marker at true camera location
            self.oobeVis.reparentTo(self.trueCamera)
            # Remove any transformation on the models arc
            self.oobeVis.clearMat()
            # Make oobeCamera be a sibling of wherever camera is now.
            cameraParent = self.camera.getParent()
            # Prepare oobe camera
            self.oobeCamera.reparentTo(cameraParent)
            self.oobeCamera.iPosHpr(self.trueCamera)
            # Put camera under new oobe camera
            base.cam.reparentTo(self.oobeCamera)
            # Position a target point to lerp the oobe camera to
            direct.cameraControl.camManipRef.setPos(
                self.trueCamera, Vec3(-2,-20, 5))
            direct.cameraControl.camManipRef.lookAt(self.trueCamera)
            t = self.oobeCamera.lerpPosHpr(
                Point3(0), Vec3(0), 2.0,
                other = direct.cameraControl.camManipRef,
                task = 'manipulateCamera',
                blendType = 'easeInOut')
            # When move is done, switch to oobe mode
            t.uponDeath = self.beginOOBE

    def beginOOBE(self, state):
        # Make sure we've reached our final destination
        self.oobeCamera.iPosHpr(direct.cameraControl.camManipRef)
        direct.camera = self.oobeCamera
        self.oobeMode = 1

    def endOOBE(self, state):
        # Make sure we've reached our final destination
        self.oobeCamera.iPosHpr(self.trueCamera)
        # Disable OOBE mode.
        base.cam.reparentTo(self.trueCamera)
        direct.camera = self.trueCamera
        # Get rid of ancillary node paths
        self.oobeVis.reparentTo(hidden)
        self.oobeCamera.reparentTo(hidden)
        self.oobeMode = 0

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
        if ((input == 'mouse1') or (input == 'shift-mouse1') or
            (input == 'control-mouse1') or (input == 'alt-mouse1')):
            messenger.send('DIRECT_mouse1')
        elif input == 'mouse1-up':
            messenger.send('DIRECT_mouse1Up')
        elif ((input == 'mouse2') or (input == 'shift-mouse2') or
              (input == 'control-mouse2') or (input == 'alt-mouse2')): 
            messenger.send('DIRECT_mouse2')
        elif input == 'mouse2-up':
            messenger.send('DIRECT_mouse2Up')
        elif input == 'mouse3': 
            messenger.send('DIRECT_mouse3')
        elif input == 'mouse3-up':
            messenger.send('DIRECT_mouse3Up')
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
        elif input == 'v':
            self.toggleWidgetVis()
        elif input == 'b':
            base.toggleBackface()
        elif input == 'l':
            self.lights.toggle()
        elif input == 'shift-l':
            self.cameraControl.toggleCOALock()
        elif input == 'o':
            self.oobe()
        elif input == 'p':
            if self.selected.last:
                self.setActiveParent(self.selected.last)
        elif input == 'r':
            # Do wrt reparent
            if self.selected.last:
                self.reparent(self.selected.last, fWrt = 1)
        elif input == 'shift-r':
            # Do regular reparent
            if self.selected.last:
                self.reparent(self.selected.last)
        elif input == 's':
            if self.selected.last:
                self.select(self.selected.last)
        elif input == 't':
            base.toggleTexture()
        elif input == 'shift-a':
            self.selected.toggleVisAll()
        elif input == 'w':
            base.toggleWireframe()
        elif (input == '[') or (input == '{'):
            self.undo()
        elif (input == ']') or (input == '}'):
            self.redo()

        #Pass along certain events if this display is a cluster client
        if self.clusterMode == 'client':
            if input in ('v','b','l','p', 'r', 'shift-r', 's', 't',
                         'shift-a', 'w'):
                self.cluster.cmd('messenger.send("%s")' % input,0)
        
    def select(self, nodePath, fMultiSelect = 0, fResetAncestry = 1):
        dnp = self.selected.select(nodePath, fMultiSelect)
        if dnp:
            messenger.send('DIRECT_preSelectNodePath', [dnp])
            if fResetAncestry:
                # Update ancestry
                self.ancestry = dnp.getAncestry()
                self.ancestry.reverse()
                self.ancestryIndex = 0
            # Update the selectedNPReadout
            self.selectedNPReadout.reparentTo(aspect2d)
            self.selectedNPReadout.setText(
                'Selected:' + dnp.getName())
            # Show the manipulation widget
            self.widget.showWidget()
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
            taskMgr.remove('followSelectedNodePath')
            t = Task.Task(self.followSelectedNodePathTask)
            t.dnp = dnp
            taskMgr.add(t, 'followSelectedNodePath')
            # Send an message marking the event
            messenger.send('DIRECT_selectedNodePath', [dnp])

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
            self.widget.hideWidget()
            self.selectedNPReadout.reparentTo(hidden)
            self.selectedNPReadout.setText(' ')
            taskMgr.remove('followSelectedNodePath')
            self.ancestry = []
            # Send an message marking the event
            messenger.send('DIRECT_deselectedNodePath', [dnp])

    def deselectAll(self):
        self.selected.deselectAll()
        # Hide the manipulation widget
        self.widget.hideWidget()
        self.selectedNPReadout.reparentTo(hidden)
        self.selectedNPReadout.setText(' ')
        taskMgr.remove('followSelectedNodePath')

    def setActiveParent(self, nodePath = None):
        # Record new parent
        self.activeParent = nodePath
        # Update the activeParentReadout
        self.activeParentReadout.reparentTo(aspect2d)
        self.activeParentReadout.setText(
            'Active Parent:' + nodePath.getName())
        # Alert everyone else
        messenger.send('DIRECT_activeParent', [self.activeParent])
        
    def reparent(self, nodePath = None, fWrt = 0):
        if (nodePath and self.activeParent and
            self.isNotCycle(nodePath, self.activeParent)):
            oldParent = nodePath.getParent()
            if fWrt:
                nodePath.wrtReparentTo(self.activeParent)
            else:
                nodePath.reparentTo(self.activeParent)
            # Alert everyone else
            messenger.send('DIRECT_reparent',
                           [nodePath, oldParent, self.activeParent])

    def isNotCycle(self, nodePath, parent):
        if nodePath.id() == parent.id():
            print 'DIRECT.reparent: Invalid parent'
            return 0
        elif parent.hasParent():
            return self.isNotCycle(nodePath, parent.getParent())
        else:
            return 1
        
    def flash(self, nodePath = 'None Given'):
        """ Highlight an object by setting it red for a few seconds """
        # Clean up any existing task
        taskMgr.remove('flashNodePath')
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
            t = taskMgr.add(
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

    def fitOnNodePath(self, nodePath = 'None Given'):
        if nodePath == 'None Given':
            # If nothing specified, try selected node path
            nodePath = self.selected.last
        direct.select(nodePath)
        def fitTask(state, self = self):
            self.cameraControl.fitOnWidget()
            return Task.done
        taskMgr.doMethodLater(0.1, fitTask, 'manipulateCamera')

    def isolate(self, nodePath = 'None Given'):
        """ Show a node path and hide its siblings """
        # First kill the flashing task to avoid complications
        taskMgr.remove('flashNodePath')
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
        taskMgr.remove('flashNodePath')
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
                if (name != 'render') and (name != 'renderTop'):
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
                if (name != 'render') and (name != 'renderTop'):
                    self.ancestryIndex = i
                    self.select(np, 0, 0)
                    self.flash(np)

    def getAndSetName(self, nodePath):
        """ Prompt user for new node path name """
        newName = askstring('Node Path: ' + nodePath.getName(),
                            'Enter new name:')
        if newName:
            nodePath.setName(newName)
            messenger.send('DIRECT_nodePathSetName', [nodePath, newName])

    # UNDO REDO FUNCTIONS
    def pushUndo(self, nodePathList, fResetRedo = 1):
        # Assemble group of changes
        undoGroup = []
        for nodePath in nodePathList:
            m = Mat4()
            m.assign(nodePath.getMat())
            undoGroup.append([nodePath, m])
        # Now record group
        self.undoList.append(undoGroup)
        # Truncate list
        self.undoList = self.undoList[-25:]
        # Alert anyone who cares
        messenger.send('DIRECT_pushUndo')
        if fResetRedo and (nodePathList != []):
            self.redoList = []
            messenger.send('DIRECT_redoListEmpty')

    def popUndoGroup(self):
        # Get last item
        undoGroup = self.undoList[-1]
        # Strip last item off of undo list
        self.undoList = self.undoList[:-1]
        # Update state of undo button
        if not self.undoList:
            messenger.send('DIRECT_undoListEmpty')
        # Return last item
        return undoGroup
        
    def pushRedo(self, nodePathList):
        # Assemble group of changes
        redoGroup = []
        for nodePath in nodePathList:
            m = Mat4()
            m.assign(nodePath.getMat())
            redoGroup.append([nodePath, m])
        # Now record redo group
        self.redoList.append(redoGroup)
        # Truncate list
        self.redoList = self.redoList[-25:]
        # Alert anyone who cares
        messenger.send('DIRECT_pushRedo')

    def popRedoGroup(self):
        # Get last item
        redoGroup = self.redoList[-1]
        # Strip last item off of redo list
        self.redoList = self.redoList[:-1]
        # Update state of redo button
        if not self.redoList:
            messenger.send('DIRECT_redoListEmpty')
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
                pose[0].setMat(pose[1])
            # Alert anyone who cares
            messenger.send('DIRECT_undo')

    def redo(self):
        if self.redoList:
            # Get last item off of redo list
            redoGroup = self.popRedoGroup()
            # Record undo information
            nodePathList = map(lambda x: x[0], redoGroup)
            self.pushUndo(nodePathList, fResetRedo = 0)
            # Redo xform
            for pose in redoGroup:
                pose[0].setMat(pose[1])
            # Alert anyone who cares
            messenger.send('DIRECT_redo')

    # UTILITY FUNCTIONS
    def message(self, text):
        taskMgr.remove('hideDirectMessage')
        taskMgr.remove('hideDirectMessageLater')
        self.directMessageReadout.reparentTo(aspect2d)
        self.directMessageReadout.setText(text)
        self.hideDirectMessageLater()

    def hideDirectMessageLater(self):
        seq = Task.doLater(3.0, Task.Task(self.hideDirectMessage),
                           'hideDirectMessage')
        t = taskMgr.add(seq, 'hideDirectMessageLater')

    def hideDirectMessage(self, state):
        self.directMessageReadout.reparentTo(hidden)
        return Task.done

    def useObjectHandles(self):
        self.widget = self.manipulationControl.objectHandles
        self.widget.reparentTo(direct.group)

    def hideSelectedNPReadout(self):
        self.selectedNPReadout.reparentTo(hidden)

    def hideActiveParentReadout(self):
        self.activeParentReadout.reparentTo(hidden)

    def toggleWidgetVis(self):
        self.widget.toggleWidget()

    def isEnabled(self):
        return self.fEnabled

    def addUnpickable(self, item):
        for iRay in self.iRayList:
            iRay.addUnpickable(item)

    def removeUnpickable(self, item):
        for iRay in self.iRayList:
            iRay.removeUnpickable(item)

class DisplayRegionList(PandaObject):
    def __init__(self):
        self.displayRegionList = []
        self.displayRegionLookup = {}
        i = 0

        for cameraGroup in base.cameraList:
            # This is following the old way of setting up
            # display regions.  A display region is set up for
            # each camera node in the scene graph.  This was done
            # so that only display regions in the scene graph are
            # considered.  The right way to do this is to set up
            # a display region for each real display region, and then
            # keep track of which are currently active (e.g. use a flag)
            # processing only them.
            camList=cameraGroup.findAllMatches('**/+Camera')
            for cameraIndex in range(camList.getNumPaths()):
                camera = camList[cameraIndex]
                if camera.getName()=='<noname>':
                    camera.setName('Camera%d' % cameraIndex)
                group = base.groupList[cameraIndex]
                self.displayRegionList.append(
                    DisplayRegionContext(base.win,
                                         camera,group))
                if camera.getName()!='<noname>' or len(camera.getName())==0:
                    self.displayRegionLookup[camera.getName()]=i
                    i = i + 1
        self.accept("CamChange",self.camUpdate)
        self.accept("DIRECT_mouse1",self.mouseUpdate)
        self.accept("DIRECT_mouse2",self.mouseUpdate)
        self.accept("DIRECT_mouse3",self.mouseUpdate)
        self.accept("DIRECT_mouse1Up",self.mouseUpdate)
        self.accept("DIRECT_mouse2Up",self.mouseUpdate)
        self.accept("DIRECT_mouse3Up",self.mouseUpdate)

        #setting up array of camera nodes
        cameraList = []
        for dr in self.displayRegionList:
            cameraList.append(dr.cam)

    def __getitem__(self, index):
        return self.displayRegionList[index]

    def __len__(self):
        return len(self.displayRegionList)

    def updateContext(self):
        self.contextTask(None)

    def setNearFar(self, near, far):
        for dr in self.displayRegionList:
            dr.camLens.setNearFar(near, far)
    
    def setNear(self, near):
        for dr in self.displayRegionList:
            dr.camLens.setNear(near)
    
    def setFar(self, far):
        for dr in self.displayRegionList:
            dr.camLens.setFar(far)

    def setFov(self, hfov, vfov):
        for dr in self.displayRegionList:
            dr.setFov(hfov, vfov)

    def setHfov(self, fov):
        for dr in self.displayRegionList:
            dr.setHfov(fov)

    def setVfov(self, fov):
        for dr in self.displayRegionList:
            dr.setVfov(fov)

    def camUpdate(self, camName):
        if self.displayRegionLookup.has_key(camName):
            self.displayRegionList[self.displayRegionLookup[camName]].camUpdate()
        else:
            for dr in self.displayRegionList:
                dr.camUpdate()

    def mouseUpdate(self):
        for dr in self.displayRegionList:
            dr.mouseUpdate()
        direct.dr = self.getCurrentDr()

    def getCurrentDr(self):
        for dr in self.displayRegionList:
            if (dr.mouseX >= -1.0 and dr.mouseX <= 1.0 and
                dr.mouseY >= -1.0 and dr.mouseY <= 1.0):
                return dr
        return self.displayRegionList[0]

    def start(self):
        # First shutdown any existing task
        self.stop()
        # Start a new context task
        self.spawnContextTask()

    def stop(self):
        # Kill the existing context task
        taskMgr.remove('DIRECTContextTask')

    def spawnContextTask(self):
        taskMgr.add(self.contextTask, 'DIRECTContextTask')

    def removeContextTask(self):
        taskMgr.remove('DIRECTContextTask')

    def contextTask(self, state):
        # Window Data
        self.mouseUpdate()
        # hack to test movement
        return Task.cont

class DisplayRegionContext:
    def __init__(self, win, cam, group):
        self.win = win
        self.cam = cam
        self.camNode = self.cam.node()
        self.camLens = self.camNode.getLens()
        self.group = group
        self.iRay = SelectionRay(self.cam)
        self.nearVec = Vec3(0)
        self.mouseX = 0.0
        self.mouseY = 0.0
        # A Camera node can have more than one display region
        # associated with it.  Here I assume that there is only
        # one display region per camera, since we are defining a
        # display region on a per-camera basis.  See note in
        # DisplayRegionList.__init__()
        try:
            self.dr = self.camNode.getDr(0)
        except:
            self.dr = self.camNode.getDisplayRegion(0)
        left = self.dr.getLeft()
        right = self.dr.getRight()
        bottom = self.dr.getBottom()
        top = self.dr.getTop()
        self.originX = left+right-1
        self.originY = top+bottom-1
        self.scaleX = 1.0/(right-left)
        self.scaleY = 1.0/(top-bottom)
        self.setOrientation()
        self.camUpdate()

    def __getitem__(self,key):
        return self.__dict__[key]

    def setOrientation(self):
        hpr = self.cam.getHpr(base.cameraList[self.group])
        if hpr[2] < 135 and hpr[2]>45 or hpr[2]>225 and hpr[2]<315:
            self.isSideways = 1
        elif hpr[2] > -135 and hpr[2] < -45 or hpr[2] < -225 and hpr[2] > -315:
            self.isSideways = 1
        else:
            self.isSideways = 0

    # The following take into consideration sideways displays
    def getHfov(self):
        if self.isSideways:
            return self.camLens.getVfov()
        else:
            return self.camLens.getHfov()

    def getVfov(self):
        if self.isSideways:
            return self.camLens.getHfov()
        else:
            return self.camLens.getVfov()

    def setHfov(self,hfov):
        if self.isSideways:
            self.camLens.setFov(self.camLens.getHfov(), hfov)
        else:
            self.camLens.setFov(hfov, self.camLens.getVfov())

    def setVfov(self,vfov):
        if self.isSideways:
            self.camLens.setFov(vfov, self.camLens.getVfov())
        else:
            self.camLens.setFov(self.camLens.getHfov(), vfov)

    def setFov(self,hfov,vfov):
        if self.isSideways:
            self.camLens.setFov(vfov, hfov)
        else:
            self.camLens.setFov(hfov, vfov)
            
    def camUpdate(self):
        # Window Data
        self.width = self.win.getWidth()
        self.height = self.win.getHeight()
        self.near = self.camLens.getNear()
        self.far = self.camLens.getFar()
        self.fovH = self.camLens.getHfov()
        self.fovV = self.camLens.getVfov()
        self.nearWidth = math.tan(deg2Rad(self.fovH * 0.5)) * self.near * 2.0
        self.nearHeight = math.tan(deg2Rad(self.fovV * 0.5)) * self.near * 2.0
        self.left = -self.nearWidth * 0.5
        self.right = self.nearWidth * 0.5
        self.top = self.nearHeight * 0.5
        self.bottom = -self.nearHeight * 0.5

    def mouseUpdate(self):
        # Mouse Data
        # Last frame
        self.mouseLastX = self.mouseX
        self.mouseLastY = self.mouseY
        # Values for this frame
        # This ranges from -1 to 1
        if (base.mouseWatcherNode.hasMouse()):
            self.mouseX = base.mouseWatcherNode.getMouseX()
            self.mouseY = base.mouseWatcherNode.getMouseY()
            self.mouseX = (self.mouseX-self.originX)*self.scaleX
            self.mouseY = (self.mouseY-self.originY)*self.scaleY
        # Delta percent of window the mouse moved
        self.mouseDeltaX = self.mouseX - self.mouseLastX
        self.mouseDeltaY = self.mouseY - self.mouseLastY
        self.nearVec.set((self.nearWidth*0.5) * self.mouseX,
                         self.near,
                         (self.nearHeight*0.5) * self.mouseY)

# Create one
__builtin__.direct = base.direct = DirectSession()












