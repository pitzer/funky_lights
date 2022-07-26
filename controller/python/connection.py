
import serial
import time

from . import messages

BAUDRATE = 333333

def SetupSerial(device, baudrate=BAUDRATE):
    """ Configure both the target LEDs and the local UART for a new baudrate
     Args:
      device: string with the device name
      baudrate: desired baudrate. This will be rounded to the closest baudrate
        that the ATTINY85 can support
     Returns:
      A new serial object
    """
    prescaler = int(16000000 / baudrate / 8)
    baudrate = int(16000000 / (8 * prescaler))
    serial_port = serial.Serial(device, baudrate=baudrate)
    print("Opened serial port %s with baudrate %d" %
          (serial_port.name, serial_port.baudrate))
    time.sleep(1)
    return serial_port


def ChangeBaudrate(serial_port, new_baudrate):
    """ Change the baudrate of an active connection.
     Args:
      serial_port: an active serial port
      baudrate: desired baudrate. This will be rounded to the closest baudrate
        that the ATTINY85 can support
     Returns:
      A new serial object
    """
    prescaler = int(16000000 / new_baudrate / 8)
    new_baudrate = int(16000000 / (8 * prescaler))
    # We are already initialized. We should send a message to the LEDs to
    #  change baudrate
    devive = serial_port.name
    serial_port.write(messages.PrepareBaudrateMsg(messages.BROADCAST_UID, prescaler))
    serial_port.close()
    serial_port = serial.Serial(devive, baudrate=new_baudrate)
    print("Opened serial port %s with baudrate %d" %
          (serial_port.name, serial_port.baudrate))
    time.sleep(1)
    return serial_port
