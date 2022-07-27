import sys
import time
from python import connection, messages

NUM_LEDS = 30


def main():
    tty_device = connection.DEFAULT_TTY_DEVICE
    uid = messages.BROADCAST_UID

    if len(sys.argv) > 1:
        tty_device = sys.argv[1]
    if len(sys.argv) > 2:
        uid = int(sys.argv[2])

    # Some test pattern
    rgbs = []
    for i in range(int(NUM_LEDS / 2)):
        col = int(i / (NUM_LEDS / 2) * 255)
        rgbs += [(col, 255-col, 0)]
    for i in range(int(NUM_LEDS / 2)):
        col = int(255 - (i / (NUM_LEDS / 2) * 255))
        rgbs += [(col, 255 - col, 0)]

    serial_port = connection.InitializeController(tty_device)

    # Send messages to all the bars
    for i in range(100000):
        serial_port.write(messages.PrepareLedMsg(uid, rgbs))
        rgbs = rgbs[1:] + rgbs[:1]
        time.sleep(0.05)

    serial_port.close()


if __name__ == '__main__':
    main()
