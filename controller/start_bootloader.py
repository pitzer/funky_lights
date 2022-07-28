import sys
from funky_lights import connection, messages


def main():
    tty_device = connection.DEFAULT_TTY_DEVICE
    uid = messages.BROADCAST_UID

    if len(sys.argv) > 1:
        tty_device = sys.argv[1]
    if len(sys.argv) > 2:
        uid = int(sys.argv[2])

    serial_port = connection.SetupSerial(tty_device, baudrate=connection.LED_BAUDRATE)
    serial_port.write(messages.PrepareBootloaderMsg(uid))
    serial_port.close()  

if __name__ == '__main__':
    main()