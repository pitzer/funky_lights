
import serial
import time

from . import messages

START_BAUDRATE = 9600
LED_BAUDRATE = 250000
DEFAULT_TTY_DEVICE = '/dev/tty.usbserial-14210'

def InitializeController(tty_device, baudrate=LED_BAUDRATE, uid=messages.BROADCAST_UID):
    serial_port = SetupSerial(tty_device, baudrate=START_BAUDRATE)
    serial_port.write(messages.PrepareStartLedControllerMsg(uid))
    time.sleep(0.5)

    if baudrate != START_BAUDRATE:
        serial_port = ChangeBaudrate(serial_port, baudrate)
    
    return serial_port

def SetupSerial(device, baudrate=START_BAUDRATE):
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
    time.sleep(0.1)
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
    time.sleep(0.1)
    serial_port.close()
    serial_port = serial.Serial(devive, baudrate=new_baudrate)
    return serial_port
