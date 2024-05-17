import sys
import time
from funky_lights import connection, messages
import numpy as np
from opclib import opc
from itertools import repeat
import random

NUM_LEDS = 500
WHITE = 255


def main():
    address = '192.168.86.50:7890'

    if len(sys.argv) > 1:
        address = sys.argv[1]

    client = opc.Client(address, long_connection=True, verbose=False)
    if client.can_connect():
        print('connected to %s' % address)
    else:
        # We could exit here, but instead let's just print a warning
        # and then keep trying to send pixels in case the server
        # appears later
        print('WARNING: could not connect to %s' % address)

    # palette = np.array(
    #     [[242, 207, 51], [245, 112, 76], [32, 158, 179], [240, 167, 141]], dtype=np.uint8)
    palette = [
        (0.0, 0.5, 0.0),
        (0.0, 0.0, 0.5),
        (0.0, 1.0, 0.5),
        (0.0, 0.5, 1.0),
        (0.0, 0.5, 0.5),
        (0.5, 0.0, 0.0),
        (0.5, 0.5, 0.0),
        (0.5, 1.0, 0.0),
        (0.5, 0.0, 0.5),
        (0.5, 0.0, 1.0),
        (0.5, 1.0, 0.5),
        (0.5, 1.0, 1.0),
        (0.5, 0.5, 1.0),
        (1.0, 0.5, 0.0),
        (1.0, 0.0, 0.5),
        (1.0, 0.5, 0.5),
        (1.0, 1.0, 0.5),
        (1.0, 0.5, 1.0),
    ]
    palette = [[int(j*255) for j in i] for i in palette]

    # Send messages to all the bars
    while (True):
        pixels = \
            list(repeat(palette[random.randint(0, len(palette)-1)], 1)) + \
            list(repeat(palette[random.randint(0, len(palette)-1)], 8)) + \
            list(repeat(palette[random.randint(0, len(palette)-1)], 10)) + \
            list(repeat(palette[random.randint(0, len(palette)-1)], 1)) + \
            list(repeat(palette[random.randint(0, len(palette)-1)], 3)) + \
            list(repeat(palette[random.randint(0, len(palette)-1)], 9)) + \
            list(repeat(palette[random.randint(0, len(palette)-1)], 1))
        # pixels = \
        #     list(repeat(palette[random.randint(0, len(palette)-1)], 2)) + \
        #     list(repeat(palette[random.randint(0, len(palette)-1)], 2)) + \
        #     list(repeat(palette[random.randint(0, len(palette)-1)], 1)) + \
        #     list(repeat(palette[random.randint(0, len(palette)-1)], 1)) + \
        #     list(repeat(palette[random.randint(0, len(palette)-1)], 5)) + \
        #     list(repeat(palette[random.randint(0, len(palette)-1)], 3)) + \
        #     list(repeat(palette[random.randint(0, len(palette)-1)], 1)) + \
        #     list(repeat(palette[random.randint(0, len(palette)-1)], 3)) + \
        #     list(repeat(palette[random.randint(0, len(palette)-1)], 3)) + \
        #     list(repeat(palette[random.randint(0, len(palette)-1)], 4)) + \
        #     list(repeat(palette[random.randint(0, len(palette)-1)], 1)) + \
        #     list(repeat(palette[random.randint(0, len(palette)-1)], 1))
        for channel in range(8):
            client.put_pixels(pixels, channel=channel)
        time.sleep(1)


if __name__ == '__main__':
    main()
