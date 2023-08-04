# Author-
# Description-

import adsk.core
import adsk.fusion
import adsk.cam
import traceback
import csv
import math


SPLINE_SAMPLING_STEP_SIZE_M = 0.01
CSV_UNIT = 'm'
LED_DISTANCE_M = 5.0 / 150.0
MIRROR_ON_Z = False
CSV_FILENAME = '/Users/pitzer/Documents/workspace/funky_lights/config/led_config.csv'
MERGE_RESULTS = True
START_UID = 96
BUS = 'leg_back_left'
SUB_COMPONENT = 'leg_back_left'
NAME = 'leg_back_left/segment_1'


class Segment():
    """
    Represents the definition of line segment with 3D points and total length.
    """

    def __init__(self, uid, length, points):
        self.uid = uid
        self.points = points
        self.length = length

    def merge(self, other):
        # drop the first point in other segment becauce is should be the same as last point in self
        self.points.extend(other.points[1:])
        self.length += other.length


def convertInternalUnitsToCSV(app, length, points):
    """
    The converts the length and points parameters from the internal unit used by Fusion 360 to the unit specified by CSV_UNIT.
    """

    des = app.activeProduct
    unitsMgr = des.unitsManager

    for p in points:
        for i in range(len(p)):
            p[i] = unitsMgr.convert(p[i], unitsMgr.internalUnits, CSV_UNIT)
    length = unitsMgr.convert(
        length, unitsMgr.internalUnits, CSV_UNIT)

    return length, points


def evalateFittedSpline(app, entity):
    """
    Walks along the path formed by a spline entity and samples points in SPLINE_SAMPLING_STEP_SIZE_M intervals.
    Returns the total length of the resulting segments and a list of points.
    """

    des = app.activeProduct
    unitsMgr = des.unitsManager
    ui = app.userInterface
    geom = entity.worldGeometry
    eva = geom.evaluator

    returnValue, startPoint, endPoint = eva.getEndPoints()
    returnValue, total_length = eva.getLengthAtParameter(0.0, 1.0)

    unitsMgr = des.unitsManager
    step_size = unitsMgr.convert(
        SPLINE_SAMPLING_STEP_SIZE_M, CSV_UNIT, unitsMgr.internalUnits)

    inc_length = step_size
    points = [list(startPoint.asArray())]
    while inc_length < total_length:
        returnValue, inc_param = eva.getParameterAtLength(0.0, inc_length)
        if not returnValue:
            ui.messageBox('getParameterAtLength_NG')
            return

        returnValue, pnt3d = eva.getPointAtParameter(inc_param)
        if not returnValue:
            ui.messageBox('getPointAtParameter_NG')
            return

        points.append(list(pnt3d.asArray()))
        inc_length += step_size

    points.append(list(endPoint.asArray()))

    return convertInternalUnitsToCSV(app, total_length, points)


def evalateSketchLine(app, entity):
    """
    Uses the start and end point of a sketch line to form a line segment.
    Returns the length of the resulting segment and a list of points.
    """
    des = app.activeProduct
    unitsMgr = des.unitsManager
    geom = entity.worldGeometry
    eva = geom.evaluator

    _, startPoint, endPoint = eva.getEndPoints()
    _, length = eva.getLengthAtParameter(0.0, 1.0)

    points = []
    points.append(list(startPoint.asArray()))
    points.append(list(endPoint.asArray()))

    return convertInternalUnitsToCSV(app, length, points)


def evalateBRepEdge(app, entity):
    """
    Uses the start and end point of a sketch line to form a line segment.
    Returns the length of the resulting segment and a list of points.
    """
    des = app.activeProduct
    unitsMgr = des.unitsManager
    eva = entity.evaluator

    _, startPoint, endPoint = eva.getEndPoints()
    length = entity.length

    points = []
    points.append(list(startPoint.asArray()))
    points.append(list(endPoint.asArray()))

    return convertInternalUnitsToCSV(app, length, points)


def createCSVRow(segment_id, num_leds, total_length, points):
    return [segment_id,
            NAME,
            num_leds,
            '{:.2f}'.format(total_length),
            'FALSE',
            0,
            SUB_COMPONENT,
            num_leds,
            BUS,
            'done',
            repr(points)
            ]


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Generate line segments
        segment_id = START_UID
        segments = []
        for selection in ui.activeSelections:
            entity = selection.entity
            if entity.objectType == adsk.fusion.SketchFittedSpline.classType():
                length, points = evalateFittedSpline(app, entity)
            elif entity.objectType == adsk.fusion.SketchLine.classType():
                length, points = evalateSketchLine(app, entity)
            elif entity.objectType == adsk.fusion.BRepEdge.classType():
                length, points = evalateBRepEdge(app, entity)
            else:
                continue

            segments.append(Segment(segment_id, length, points))
            segment_id += 1

            # Merge if necessary
            if MIRROR_ON_Z:
                for p in points:
                    p[2] = -p[2]
                segments.append(Segment(segment_id, length, points))
                segment_id += 1

        # Merge if necessary
        if MERGE_RESULTS and len(segments) > 1:
            merge_segment = segments[0]
            for i in range(len(segments) - 1, 0, -1):
                other = segments.pop(i)
                merge_segment.merge(other)

        # Output as CSV
        csv_header = ['uid', 'name', 'num_leds', 'length', 'reversed', 'offset',
                      'sub_component', 'num_adressable_leds', 'bus', 'status', 'points']
        csv_data = []
        for segment in segments:
            num_leds = math.floor(segment.length / LED_DISTANCE_M) + 1
            csv_data.append(createCSVRow(segment.uid, num_leds,
                            segment.length, segment.points))

        with open(CSV_FILENAME, 'w', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(csv_header)
            for row in csv_data:
                writer.writerow(row)

        ui.messageBox('Done')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
