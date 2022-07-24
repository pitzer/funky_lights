import sys
import time
from python import protocol

serial_port = None

NUM_LEDS = 30

tty_device = '/dev/tty.usbserial-14430'
baudrate = 250000

if len(sys.argv) > 1:
  tty_device = sys.argv[1]
if len(sys.argv) > 2:
  baudrate = int(sys.argv[2])

# Configure the serial port. Do it twice to exercise the speed change on 
serial_port = protocol.SetupSerial(tty_device)
serial_port = protocol.SetupSerial(tty_device, baudrate, serial_port)
serial_port.close()  
