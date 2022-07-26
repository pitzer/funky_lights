import sys
from python import connection, messages


def main():
    tty_device = '/dev/tty.usbserial-14430'
    uid = 1

    if len(sys.argv) > 1:
        tty_device = sys.argv[1]
    if len(sys.argv) > 2:
        uid = int(sys.argv[2])

    # Configure the serial port. Do it twice to exercise the speed change on 
    serial_port = connection.SetupSerial(tty_device)
    serial_port.write(messages.PrepareBootloaderMsg(uid))
    serial_port.close()  

if __name__ == '__main__':
    main()