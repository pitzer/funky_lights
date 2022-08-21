import crc8
from . import crc16
from enum import Enum


MAGIC = 0x55

BROADCAST_UID = 0

CMD_LEDS = 1
CMD_SERIAL_BAUDRATE = 2
CMD_BOOTLOADER = 3

class ColorFormat(Enum):
    GRB = 0
    GBR = 1
    RGB = 2
    BGR = 3
    RBG = 4


def RgbToBits(rgbs, color_format=ColorFormat.GRB):
    """ Convert RGB value given as a 3-tuple to a list of two bytes that can
         be sent to the LEDs.
    Args:
     rgbs: list of rgb tuples
    Returns:
     a list of bytes
    """
    out = []
    if color_format == ColorFormat.RGB:
        # We pack data as 16 bits: RRRRRGGGGGGBBBBB
        for rgb in rgbs:
            r, g, b = rgb
            out += [((g << 3) & 0xE0) | ((b >> 3) & 0x1F),
                    (r & 0xF8) | ((g >> 5) & 0x07)]
    elif color_format == ColorFormat.BGR:
        # We pack data as 16 bits: BBBBBGGGGGGRRRRR
        for rgb in rgbs:
            r, g, b = rgb
            out += [((g << 3) & 0xE0) | ((r >> 3) & 0x1F),
                    (b & 0xF8) | ((g >> 5) & 0x07)]
    elif color_format == ColorFormat.GRB:
        # We pack data as 16 bits: GGGGGRRRRRRBBBBB
        for rgb in rgbs:
            r, g, b = rgb
            out += [((r << 3) & 0xE0) | ((b >> 3) & 0x1F),
                    (g & 0xF8) | ((r >> 5) & 0x07)]
    elif color_format == ColorFormat.GBR:
        # We pack data as 16 bits: GGGGGBBBBBBRRRRR
        for rgb in rgbs:
            r, g, b = rgb
            out += [((b << 3) & 0xE0) | ((r >> 3) & 0x1F),
                    (g & 0xF8) | ((b >> 5) & 0x07)]
    elif color_format == ColorFormat.RBG:
        # We pack data as 16 bits: RRRRRBBBBBBGGGGG
        for rgb in rgbs:
            r, g, b = rgb
            out += [((b << 3) & 0xE0) | ((g >> 3) & 0x1F),
                    (r & 0xF8) | ((b >> 5) & 0x07)]
    return out


def PrepareLedMsg(bar_uid, rgbs, color_format=ColorFormat.GRB):
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
    data = RgbToBits(rgbs, color_format)
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


def PrepareStartLedControllerMsg(bar_uid):
    """ Prepare a message to tell the bootloader to start the LED controller.
    Args:
     bar_uid: UID of the bar to which we want to send the message
    Returns:
     a bytearray, ready to send on the serial port
    """

    msg = [
        0x01, # UID
        0x06,  # Change running MODE
        0x00, 0x00, # address start
        0x00, 0x00, # number of bytes
        0xff, 0xff  # crc
    ]
    msg[0] = bar_uid
    crc = crc16.crc16(msg[0:6])
    msg[6] = (crc & 0x00ff)
    msg[7] = (crc & 0xff00) >> 8
    return bytearray(msg)