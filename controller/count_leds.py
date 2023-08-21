import sys
from funky_lights import connection, messages

NUM_LEDS = 20


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
        NUM_LEDS = int(sys.argv[4])

    # Some test pattern
    rgbs = [(255, 255, 255)] * NUM_LEDS
    rgbs[-1] = (255, 0, 0)

    serial_port = connection.InitializeController(
        tty_device, baudrate=baudrate)

    # Send messages to all the bars
    while True:
        serial_port.write(messages.PrepareLedMsg(uid, rgbs))
        NUM_LEDS = int(input("Number of LEDs: "))

    serial_port.close()


if __name__ == '__main__':
    main()
