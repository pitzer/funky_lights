import sys
import time
from funky_lights import connection, messages

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

    rgbs = []
    for i in range(NUM_LEDS):
        rgbs += [(255, 255, 255)]
   
    serial_port = connection.InitializeController(
        tty_device, baudrate=baudrate)

    # Send messages to all the bars
    for i in range(100000):
        serial_port.write(messages.PrepareLedMsg(uid, rgbs))
        time.sleep(0.05)

    serial_port.close()


if __name__ == '__main__':
    main()
