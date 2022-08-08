import sys
import time
from funky_lights import connection, messages

def main():
    tty_device = connection.DEFAULT_TTY_DEVICE
    uid = messages.BROADCAST_UID
    baudrate = 9600

    if len(sys.argv) > 1:
        tty_device = sys.argv[1]
    if len(sys.argv) > 2:
        baudrate = int(sys.argv[2])
    if len(sys.argv) > 3:
        uid = int(sys.argv[3])

    serial_port = connection.InitializeController(
        tty_device, baudrate=baudrate)

    serial_port.close()


if __name__ == '__main__':
    main()
