#Author-
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback, json, os, itertools, sys
app = adsk.core.Application.get() 
ui = app.userInterface 

FILENAME = '/tmp/coordinates.csv'
with open('/tmp/dbg.txt', 'w') as dbg_outfile:
    sys.stdout = dbg_outfile
    sys.stderr = dbg_outfile

    # Load existing coordinates from file
    if os.path.exists(FILENAME):
        with open(FILENAME) as file:
            json_data = json.load(file)
    else:
        json_data = {}

    leds_name, _ = ui.inputBox('Input the LED string name, then select the relevant points and press <ESC> when done', 'LED string name')

    points = []
    for led_num in itertools.count():
        try:
            point_entity = ui.selectEntity('Select Point #%d' % (led_num + 1), 'Vertices') 
            point = adsk.fusion.BRepVertex.cast(point_entity.entity)
            points.append([point.geometry.x, point.geometry.y, point.geometry.z])
        except:
            break

    json_data[leds_name] = points

    # Dump the data back to file
    with open(FILENAME, 'w') as file:
        json.dump(json_data, file, indent=2)