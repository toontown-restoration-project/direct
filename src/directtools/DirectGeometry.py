from PandaModules import *
from PandaObject import *
import math

X_AXIS = Vec3(1,0,0)
Y_AXIS = Vec3(0,1,0)
Z_AXIS = Vec3(0,0,1)
NEG_X_AXIS = Vec3(-1,0,0)
NEG_Y_AXIS = Vec3(0,-1,0)
NEG_Z_AXIS = Vec3(0,0,-1)
ZERO_VEC = ORIGIN = Vec3(0)
UNIT_VEC = Vec3(1)
ZERO_POINT = Point3(0)

class LineNodePath(NodePath):
    def __init__(self, parent = None, name = None,
                 thickness = 1.0, colorVec = VBase4(1)):

        # Initialize the superclass
        NodePath.__init__(self)

        if parent is None:
            parent = hidden

        # Attach a geomNode to the parent and set self to be
        # the resulting node path
        self.lineNode = GeomNode("lineNode")
        self.assign(parent.attachNewNode( self.lineNode ))
        if name:
            self.setName(name)

        # Create a lineSegs object to hold the line
        ls = self.lineSegs = LineSegs()
        # Initialize the lineSegs parameters
        ls.setThickness(thickness)
        ls.setColor(colorVec)

    def moveTo( self, *_args ):
        apply( self.lineSegs.moveTo, _args )

    def drawTo( self, *_args ):
        apply( self.lineSegs.drawTo, _args )

    def create( self, frameAccurate = 0 ):
        self.lineSegs.create( self.lineNode, frameAccurate )

    def reset( self ):
        self.lineSegs.reset()
        self.lineNode.removeAllGeoms()

    def isEmpty( self ):
        return self.lineSegs.isEmpty()

    def setThickness( self, thickness ):
        self.lineSegs.setThickness( thickness )

    def setColor( self, *_args ):
        apply( self.lineSegs.setColor, _args )

    def setVertex( self, *_args):
        apply( self.lineSegs.setVertex, _args )

    def setVertexColor( self, vertex, *_args ):
        apply( self.lineSegs.setVertexColor, (vertex,) + _args )

    def getCurrentPosition( self ):
        return self.lineSegs.getCurrentPosition()

    def getNumVertices( self ):
        return self.lineSegs.getNumVertices()

    def getVertex( self, index ):
        return self.lineSegs.getVertex(index)

    def getVertexColor( self ):
        return self.lineSegs.getVertexColor()
    
    def drawArrow(self, sv, ev, arrowAngle, arrowLength):
        """
        Do the work of moving the cursor around to draw an arrow from
        sv to ev. Hack: the arrows take the z value of the end point
        """
        self.moveTo(sv)
        self.drawTo(ev)
        v = sv - ev
        # Find the angle of the line
        angle = math.atan2(v[1], v[0])
        # Get the arrow angles
        a1 = angle + deg2Rad(arrowAngle)
        a2 = angle - deg2Rad(arrowAngle)
        # Get the arrow points
        a1x = arrowLength * math.cos(a1)
        a1y = arrowLength * math.sin(a1)
        a2x = arrowLength * math.cos(a2)
        a2y = arrowLength * math.sin(a2)
        z = ev[2]
        self.moveTo(ev)
        self.drawTo(Point3(ev + Point3(a1x, a1y, z)))
        self.moveTo(ev)
        self.drawTo(Point3(ev + Point3(a2x, a2y, z)))

    def drawArrow2d(self, sv, ev, arrowAngle, arrowLength):
        """
        Do the work of moving the cursor around to draw an arrow from
        sv to ev. Hack: the arrows take the z value of the end point
        """
        self.moveTo(sv)
        self.drawTo(ev)
        v = sv - ev
        # Find the angle of the line
        angle = math.atan2(v[2], v[0])
        # Get the arrow angles
        a1 = angle + deg2Rad(arrowAngle)
        a2 = angle - deg2Rad(arrowAngle)
        # Get the arrow points
        a1x = arrowLength * math.cos(a1)
        a1y = arrowLength * math.sin(a1)
        a2x = arrowLength * math.cos(a2)
        a2y = arrowLength * math.sin(a2)
        self.moveTo(ev)
        self.drawTo(Point3(ev + Point3(a1x, 0.0, a1y)))
        self.moveTo(ev)
        self.drawTo(Point3(ev + Point3(a2x, 0.0, a2y)))

    def drawLines(self, lineList):
        """
        Given a list of lists of points, draw a separate line for each list
        """
        for pointList in lineList:
            apply(self.moveTo, pointList[0])
            for point in pointList[1:]:
                apply(self.drawTo, point)

##
## Given a point in space, and a direction, find the point of intersection
## of that ray with a plane at the specified origin, with the specified normal
def planeIntersect (lineOrigin, lineDir, planeOrigin, normal):
    t = 0
    offset = planeOrigin - lineOrigin
    t = offset.dot(normal) / lineDir.dot(normal)
    hitPt = lineDir * t
    return hitPt + lineOrigin

def ROUND_TO(value, divisor):
    return round(value/float(divisor)) * divisor
def ROUND_INT(val):
    return int(round(val))
def CLAMP(val, min, max):
    if val < min:
        return min
    elif val > max:
        return max
    else:
        return val

def getNearProjectionPoint(nodePath):
    # Find the position of the projection of the specified node path
    # on the near plane
    origin = nodePath.getPos(direct.camera)
    # project this onto near plane
    if origin[1] != 0.0:
        return origin * (direct.dr.near / origin[1])
    else:
        # Object is coplaner with camera, just return something reasonable
        return Point3(0, direct.dr.near, 0)

def getScreenXY(nodePath):
    # Where does the node path's projection fall on the near plane
    nearVec = getNearProjectionPoint(nodePath)
    # Clamp these coordinates to visible screen
    nearX = CLAMP(nearVec[0], direct.dr.left, direct.dr.right)
    nearY = CLAMP(nearVec[2], direct.dr.bottom, direct.dr.top)
    # What percentage of the distance across the screen is this?
    percentX = (nearX - direct.dr.left)/direct.dr.nearWidth
    percentY = (nearY - direct.dr.bottom)/direct.dr.nearHeight
    # Map this percentage to the same -1 to 1 space as the mouse
    screenXY = Vec3((2 * percentX) - 1.0,nearVec[1],(2 * percentY) - 1.0)
    # Return the resulting value
    return screenXY

def getCrankAngle(center):
    # Used to compute current angle of mouse (relative to the coa's
    # origin) in screen space
    x = direct.dr.mouseX - center[0]
    y = direct.dr.mouseY - center[2]
    return (180 + rad2Deg(math.atan2(y,x)))

def relHpr(nodePath, base, h, p, r):
    # Compute nodePath2newNodePath relative to base coordinate system
    # nodePath2base
    mNodePath2Base = nodePath.getMat(base)
    # delta scale, orientation, and position matrix
    mBase2NewBase = Mat4()
    composeMatrix(mBase2NewBase, UNIT_VEC, VBase3(h,p,r), ZERO_VEC,
                  CSDefault)
    # base2nodePath
    mBase2NodePath = base.getMat(nodePath)
    # nodePath2 Parent
    mNodePath2Parent = nodePath.getMat()
    # Compose the result
    resultMat = mNodePath2Base * mBase2NewBase
    resultMat = resultMat * mBase2NodePath
    resultMat = resultMat * mNodePath2Parent
    # Extract and apply the hpr
    hpr = Vec3(0)
    decomposeMatrix(resultMat, VBase3(), hpr, VBase3(),
                    CSDefault)
    nodePath.setHpr(hpr)

# Set direct drawing style for an object
# Never light object or draw in wireframe
def useDirectRenderStyle(nodePath):
    nodePath.node().setAttrib(LightAttrib.makeAllOff())
    nodePath.setRenderModeFilled()
