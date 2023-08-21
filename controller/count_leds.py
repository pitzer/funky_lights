import sys
from funky_lights import connection, messages
import numpy as np

NUM_LEDS = 230


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
    if len(sys.argv) > 4:
        count = int(sys.argv[4])
    else:
        count = 20

    serial_port = connection.InitializeController(
        tty_device, baudrate=baudrate)

    # Send messages to all the bars
    while True:
        rgbs = np.zeros((NUM_LEDS, 3), int)
        for i in range(NUM_LEDS):
            rgbs[i, :] = (0, 0, 0)
        for i in range(count - 1):
            rgbs[i, :] = (255, 255, 255)
        rgbs[count - 1, :] = (255, 0, 0)
        serial_port.write(messages.PrepareLedMsg(uid, rgbs))
        count = int(input("Number of LEDs: "))

    serial_port.close()


if __name__ == '__main__':
    main()
