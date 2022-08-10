import sys
import time
from funky_lights import connection, messages

NUM_LEDS = 30


def main():
    tty_device = connection.DEFAULT_TTY_DEVICE
    baudrate = connection.LED_BAUDRATE
    test_byte = 65
    burst = 100
    num_bursts = 1000000

    if len(sys.argv) > 1:
        tty_device = sys.argv[1]
    if len(sys.argv) > 2:
        baudrate = int(sys.argv[2])
    if len(sys.argv) > 3:
        test_byte = int(sys.argv[3])
    if len(sys.argv) > 4:
        burst = int(sys.argv[4])
    if len(sys.argv) > 5:
        num_bursts = int(sys.argv[5])

    serial_port = connection.InitializeController(
        tty_device, baudrate=baudrate)

    # send the test byte
    for i in range(num_bursts):
        serial_port.write(bytearray([test_byte] * burst))
        time.sleep(0.05)

    serial_port.close()


if __name__ == '__main__':
    main()
