import sys
from funky_lights import connection, messages


def main():
    tty_device = connection.DEFAULT_TTY_DEVICE
    baudrate = connection.LED_BAUDRATE
    uid = messages.BROADCAST_UID

    if len(sys.argv) > 1:
        baudrate = int(sys.argv[1])
    if len(sys.argv) > 2:
        tty_device = sys.argv[2]
    if len(sys.argv) > 3:
        uid = int(sys.argv[3])

    serial_port = connection.SetupSerial(tty_device)
    serial_port.write(messages.PrepareBaudrateMsg(uid, baudrate))
    serial_port.close()  


if __name__ == '__main__':
    main()
