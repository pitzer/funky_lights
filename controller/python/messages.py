import crc8

MAGIC = 0x55

BROADCAST_UID = 0

CMD_LEDS = 1
CMD_SERIAL_BAUDRATE = 2
CMD_BOOTLOADER = 3


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
