import sys
import time
from funky_lights import connection, messages
import numpy as np
from opclib import opc

NUM_LEDS = 500
WHITE = 255

def main():
    address = '192.168.86.50:7890'

    if len(sys.argv) > 1:
        address = sys.argv[1]

    # Some test pattern
    rgbs = np.zeros((NUM_LEDS, 3), int)
    idx = 0
    for i in range(int(NUM_LEDS / 2)):
        col = int(i / (NUM_LEDS / 2) * WHITE)
        rgbs[idx, :] = (col, WHITE-col, 0)
        idx += 1
    for i in range(int(NUM_LEDS / 2)):
        col = int(WHITE - (i / (NUM_LEDS / 2) * WHITE))
        rgbs[idx, :] = (col, WHITE - col, 0)
        idx += 1
    #rgbs = np.ones((NUM_LEDS, 3), int) * WHITE
    rgbs[0] = (0, 0, 0)

    client = opc.Client(address, long_connection=True, verbose=False)
    if client.can_connect():
        print('connected to %s' % address)
    else:
        # We could exit here, but instead let's just print a warning
        # and then keep trying to send pixels in case the server
        # appears later
        print('WARNING: could not connect to %s' % address)


    # Send messages to all the bars
    while(True):
        for channel in range(8):
            client.put_pixels(rgbs, channel=channel)
        rgbs = np.roll(rgbs, 1, axis=0)
        time.sleep(1/60)


if __name__ == '__main__':
    main()
