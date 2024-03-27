from opclib import opc
import time

ADDRESS = '192.168.86.50:7890'

# Create a client object
client = opc.Client(ADDRESS)

# Test if it can connect (optional)
if client.can_connect():
    print('connected to %s' % ADDRESS)
else:
    # We could exit here, but instead let's just print a warning
    # and then keep trying to send pixels in case the server
    # appears later
    print('WARNING: could not connect to %s' % ADDRESS)

# Send pixels forever at 30 frames per second
while True:
    my_pixels = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    if client.put_pixels(my_pixels, channel=1):
        print('...')
    else:
        print('not connected')
    time.sleep(1/30.0)