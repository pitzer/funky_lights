import crc8
import serial
import time

MAGIC = 0x55
CMD_LEDS = 1
CMD_SERIAL_BAUDRATE = 2
CMD_BOOTLOADER = 3
BROADCAST_UID = 0
BAUDRATE = 333333

def SetupSerial(device, baudrate=BAUDRATE, serial_port=None):
  """ Configure both the target LEDs and the local UART for a new baudrate
   Args:
    device: string with the device name
    baudrate: desired baudrate. This will be rounded to the closest baudrate
      that the ATTINY85 can support
    init: should be set to true on the first call to this
   Returns:
    A new serial obect
  """
  prescaler = int(16000000 / baudrate / 8)
  baudrate = int(16000000 / (8 * prescaler))
  if serial_port:
    # We are already initialized. We should send a message to the LEDs to
    #  change baudrate
    serial_port.write(PrepareBaudrateMsg(BROADCAST_UID, prescaler))
    serial_port.close()
  serial_port = serial.Serial(device, baudrate=baudrate)
  print("Opened serial port %s with baudrate %d" %
        (serial_port.name, serial_port.baudrate))
  time.sleep(1)
  return serial_port


def RgbToBits(rgbs):
  """ Convert RGB value given as a 3-tuple to a list of two bytes that can
       be sent to the LEDs. We pack data as 16 bits:
         RRRRRGGGGGGBBBBB
  Args:
   rgbs: list of rgb tuples
  Returns:
   a list of bytes
  """
  out = []
  for rgb in rgbs:
    r, g, b = rgb
    out += [((g << 3) & 0xE0) | ((b >> 3) & 0x1F),
            (r & 0xF8) | ((g >> 5) & 0x07)]
  return out


def PrepareLedMsg(bar_uid, rgbs):
  """ Prepare a message from a list of RGB colors
  Args:
   serial: Serial port object. Should be already initialized
   bar_uid: UID of the bar to which we want to send the message
   rgbs: list of rgb tuples
  Returns:
   a bytearray, ready to send on the serial port
  """
  header = [MAGIC, bar_uid, CMD_LEDS]
  header += [len(rgbs)]
  data = RgbToBits(rgbs)
  crc_compute = crc8.crc8()
  crc_compute.update(bytearray(data))
  crc = [crc_compute.digest()[0]]
  msg = header + data + crc
  return bytearray(msg)


def PrepareBaudrateMsg(bar_uid, prescaler):
  """ Prepare a message from a list of RGB colors
  Args:
   serial: Serial port object. Should be already initialized
   bar_uid: UID of the bar to which we want to send the message
   prescaler: The prescaler for the serial interface
  Returns:
   a bytearray, ready to send on the serial port
  """
  header = [MAGIC, bar_uid, CMD_SERIAL_BAUDRATE]
  data = [prescaler]
  crc_compute = crc8.crc8()
  crc_compute.update(bytearray(data))
  crc = [crc_compute.digest()[0]]
  msg = header + data + crc
  return bytearray(msg)


def PrepareBootloaderMsg(bar_uid):
  """ Prepare a message from a list of RGB colors
  Args:
   serial: Serial port object. Should be already initialized
   bar_uid: UID of the bar to which we want to send the message
  Returns:
   a bytearray, ready to send on the serial port
  """
  header = [MAGIC, bar_uid, CMD_BOOTLOADER]
  data = []
  crc_compute = crc8.crc8()
  crc_compute.update(bytearray(header + data))
  crc = [crc_compute.digest()[0]]
  msg = header + data + crc
  return bytearray(msg)