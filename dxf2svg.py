#!/usr/bin/env python

import dxfgrabber
import math
import sys
import os

# SVG TEMPLATES

# TODO: support arbitrary, user-specifiable units
SVG_PREAMBLE = \
'<svg xmlns="http://www.w3.org/2000/svg" ' \
'version="1.1" viewBox="{0} {1} {2} {3}" width="{4}in" height="{5}in">\n'

# SVG_MOVE_TO = 'M {0} {1:.2f} '
# SVG_LINE_TO = 'L {0} {1:.2f} '
# SVG_ARC_TO  = 'A {0} {1:.2f} {2} {3} {4} {5:.2f} {6:.2f} '

SVG_MOVE_TO = 'M {0} {1} '
SVG_LINE_TO = 'L {0} {1} '
SVG_ARC_TO  = 'A {0} {1} {2} {3} {4} {5} {6} '
SVG_CURVE_TO = 'C {0} {1} {2} {3} {4} {5} '
SVG_CURVE_S_TO = 'S {0} {1} {2} {3} '

SVG_PATH = \
'<path d="{0}" fill="none" stroke="{1}" stroke-width="{2}" />\n'

SVG_LINE = \
'<line x1="{0}" y1="{1}" x2="{2}" y2="{3}" stroke="{4}" stroke-width="{5}" />\n'

SVG_CIRCLE = \
'<circle cx="{0}" cy="{1}" r="{2}" stroke="{3}" stroke-width="{4}" fill="none" />\n'

SVG_TEXT = \
'<text x="{0}" y="{1}" style="font-size: {3}">{2}</text>\n'

# from http://www.w3.org/TR/SVG/coords.html#Units
CUT_STROKE_COLOR = '#ff0000'
CUT_STROKE_WIDTH = 0.001/(90)  # TODO: user-specified, arbitrary units

ENGRAVE_STOKE_COLOR = '#000000'

# SVG DRAWING HELPERS

def angularDifference(startangle, endangle):
  result = endangle - startangle
  while result >= 360:
    result -= 360
  while result < 0:
    result += 360
  return result

def pathStringFromPoints(points):
  pathString = SVG_MOVE_TO.format(*points[0])
  for i in range(1,len(points)):
    pathString += SVG_LINE_TO.format(*points[i])
  return pathString

def curveStringFromControlPoints(points):
  pathString = SVG_MOVE_TO.format(*points[0])
  pathString += SVG_CURVE_TO.format(points[1][0], points[1][1], points[2][0], points[2][1], points[3][0], points[3][1])
  for i in range(4, len(points) - 1):
    pathString += SVG_CURVE_S_TO.format(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
  return pathString

# CONVERTING TO SVG

def handleEntity(svgFile, e):
  # TODO: handle colors and thinckness
  # TODO: handle elipse and spline and some other types

  if isinstance(e, dxfgrabber.dxfentities.Line):
    svgFile.write(SVG_LINE.format(
      e.start[0], e.start[1], e.end[0], e.end[1],
      'black', 1
    ))

  elif isinstance(e, dxfgrabber.dxfentities.LWPolyline):
    pathString = pathStringFromPoints(e)
    if e.is_closed:
      pathString += 'Z'
    svgFile.write(SVG_PATH.format(pathString, CUT_STROKE_COLOR, CUT_STROKE_WIDTH))

  elif isinstance(e, dxfgrabber.dxfentities.Polyline):
    pathString = pathStringFromPoints(e)
    if e.is_closed:
      pathString += 'Z'
    svgFile.write(SVG_PATH.format(pathString, CUT_STROKE_COLOR, CUT_STROKE_WIDTH))

  elif isinstance(e, dxfgrabber.dxfentities.Circle):
    svgFile.write(SVG_CIRCLE.format(e.center[0], e.center[1],
      e.radius, 'black', 1))

  elif isinstance(e, dxfgrabber.dxfentities.Arc):
    # compute end points of the arc
    x1 = e.center[0] + e.radius * math.cos(math.pi * e.startangle / 180)
    y1 = e.center[1] + e.radius * math.sin(math.pi * e.startangle / 180)
    x2 = e.center[0] + e.radius * math.cos(math.pi * e.endangle / 180)
    y2 = e.center[1] + e.radius * math.sin(math.pi * e.endangle / 180)

    pathString  = SVG_MOVE_TO.format(x1, y1)
    pathString += SVG_ARC_TO.format(e.radius, e.radius, 0,
      int(angularDifference(e.startangle, e.endangle) > 180), 1, x2, y2)

    svgFile.write(SVG_PATH.format(pathString, CUT_STROKE_COLOR, CUT_STROKE_WIDTH))

  elif isinstance(e, dxfgrabber.dxfentities.Solid):
    reordered_points = [e.points[0], e.points[1], e.points[3], e.points[2]]
    pathString = pathStringFromPoints(reordered_points)
    pathString += 'Z'
    svgFile.write(SVG_PATH.format(pathString, CUT_STROKE_COLOR, CUT_STROKE_WIDTH))

  elif isinstance(e, dxfgrabber.dxfentities.Spline):
    pathString = curveStringFromControlPoints(e.control_points)
    if e.is_closed:
        pathString += 'Z'
    svgFile.write(SVG_PATH.format(pathString, CUT_STROKE_COLOR, CUT_STROKE_WIDTH))

  elif isinstance(e, dxfgrabber.dxfentities.Insert):
    print "Can't handle INSERT yet"

  elif isinstance(e, dxfgrabber.dxfentities.MText):
    svgFile.write(SVG_TEXT.format(e.insert[0], e.insert[1], e.plain_text(), e.height))

  else:
    raise Exception("Unknown type %s" % e)
#end: handleEntity

def saveToSVG(svgFile, dxfData):

  minX = min(dxfData.header['$EXTMIN'][0], dxfData.header['$LIMMIN'][0])
  minY = min(dxfData.header['$EXTMIN'][1], dxfData.header['$LIMMIN'][1])
  maxX = max(dxfData.header['$EXTMAX'][0], dxfData.header['$LIMMAX'][0])
  maxY = max(dxfData.header['$EXTMAX'][1], dxfData.header['$LIMMAX'][1])
  
  # TODO: also handle groups
  svgFile.write(SVG_PREAMBLE.format(
    minX, minY, maxX - minX, maxY - minY,
    abs(maxX - minX), abs(maxY - minY)))

  for entity in dxfData.entities:
    layer = dxfData.layers[entity.layer]
    if layer.on and not layer.frozen:
      handleEntity(svgFile, entity)
    else:
      print "Not handeling entity " + str(entity)

  svgFile.write('</svg>\n')
#end: saveToSVG

if __name__ == '__main__':
  # TODO: error handling
  if len(sys.argv) < 2:
    sys.exit('Usage: {0} file-name'.format(sys.argv[0]))

  for filename in sys.argv[1:]:
    # grab data from file
    dxfData = dxfgrabber.readfile(filename)

    # TODO: alret if the file already exist
    # convert and save to svg
    svgName = '.'.join(filename.split('.')[:-1] + ['svg'])
    svgFile = open(svgName, 'w')

    label_basename = os.path.basename(filename).split('_')[0]
    print("Opening '%s' (%s)" % (filename, label_basename))

    saveToSVG(svgFile, dxfData)

    svgFile.close()
#end: __main__

