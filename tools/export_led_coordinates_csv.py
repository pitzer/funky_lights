#Author-
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback, csv, os, itertools, sys, math
app = adsk.core.Application.get() 
ui = app.userInterface 

CSV_HEADER = ['uid', 'name', 'num_leds', 'length', 'reversed', 'offset',
              'sub_component', 'num_adressable_leds', 'bus', 'status', 'points']
FILENAME = '/tmp/coordinates.csv'
LED_DISTANCE_M = 5.0 / 150.0

def createRow(bus, segment, uid, points):
    lengths = []
    for a, b in zip(points[0:-1], points[1:]):
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        dz = b[2] - a[2]
        lengths.append(math.sqrt(dx * dx + dy * dy + dz * dz))
    total_length = sum(lengths)

    num_leds = math.floor(total_length / LED_DISTANCE_M) + 1

    print(total_length)

    return {
        'uid': uid,
        'name': bus + '/' + segment,
        'num_leds': num_leds,
        'length': total_length,
        'reversed': False,
        'offset': 0,
        'sub_component': bus,
        'num_adressable_leds': num_leds,
        'bus': bus,
        'status': 'done',
        'points': points
    }

def createRow(bus, segment, uid, points):
    lengths = []
    for a, b in zip(points[0:-1], points[1:]):
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        dz = b[2] - a[2]
        lengths.append(math.sqrt(dx * dx + dy * dy + dz * dz))
    total_length = sum(lengths)

    num_leds = math.floor(total_length / LED_DISTANCE_M) + 1

    return {
        'uid': uid,
        'name': bus + '/' + segment,
        'num_leds': num_leds,
        'length': total_length,
        'reversed': False,
        'offset': 0,
        'sub_component': bus,
        'num_adressable_leds': num_leds,
        'bus': bus,
        'status': 'done',
        'points': points
    }

def RowDictToList(row_dict):
    row_list = []
    for name in CSV_HEADER:
        row_list.append(row_dict[name])
    return row_list





try:

    with open('/tmp/dbg.txt', 'w') as dbg_outfile:
        sys.stdout = dbg_outfile
        sys.stderr = dbg_outfile

        # Load existing coordinates from file
        csv_data = {}
        if os.path.exists(FILENAME):
            with open(FILENAME) as file:
                reader = csv.reader(file)
                headers = next(reader)
                if headers != CSV_HEADER:
                    raise Exception('Wrong headers %s vs %s' % (headers, CSV_HEADER))
                for row in reader:
                    row_data = {}
                    for name, value in zip(CSV_HEADER, row):
                        row_data[name] = value
                    segment_name = row_data['name']
                    csv_data[segment_name] = row_data
        else:
            csv_data = {}

        leds_string, _ = ui.inputBox('Input the LED string name: <bus>/<segment>/<uid> or <bus>/<segment>, then select the relevant points and press <ESC> when done', 'LED string name')
        vals = leds_string.split('/')
        if len(vals) == 3:
            bus, segment, uid = vals
        elif len(vals) == 2:
            bus, segment = vals
            uid = 0
        else:
            raise Exception('Wrong format %s' % leds_string)

        points_m = []
        for led_num in itertools.count():
            try:
                point_entity = ui.selectEntity('Select Point #%d' % (led_num + 1), 'Vertices') 
                point = adsk.fusion.BRepVertex.cast(point_entity.entity)
                points_m.append([point.geometry.x * 1e-2, point.geometry.y * 1e-2, point.geometry.z * 1e-2])
            except:
                break

        row_dict = createRow(bus, segment, uid, points_m)
        csv_data[bus + '/' + segment] = row_dict

        # Dump the data back to file
        with open(FILENAME, 'w', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            for name, value in csv_data.items():
                row_list = RowDictToList(value)
                writer.writerow(row_list)

except:
    if ui:
        ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))