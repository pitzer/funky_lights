import sys
import time
from funky_lights import connection, messages
import numpy as np

NUM_LEDS = 230
WHITE = 255

def main():
    tty_device = connection.DEFAULT_TTY_DEVICE
    uid = messages.BROADCAST_UID
    baudrate = connection.LED_BAUDRATE

    if len(sys.argv) > 1:
        tty_device = sys.argv[1]
    if len(sys.argv) > 2:
        baudrate = int(sys.argv[2])
    if len(sys.argv) > 3:
        uid = int(sys.argv[3])

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

    serial_port = connection.InitializeController(
        tty_device, baudrate=baudrate)

    # Send messages to all the bars
    for i in range(500):
        serial_port.write(messages.PrepareLedMsg(uid, rgbs))
        rgbs = np.roll(rgbs, 1, axis=0)
        time.sleep(0.01)

    serial_port.close()


if __name__ == '__main__':
    main()
