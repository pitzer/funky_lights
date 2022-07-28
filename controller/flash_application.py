import os
from sqlite3 import connect
import sys
import time

from funky_lights import connection, hexfile, messages, crc16

def main():
    application_file = '../attiny/attiny.ino.tiny8.hex'
    tty_device = connection.DEFAULT_TTY_DEVICE
    uid = messages.BROADCAST_UID

    if len(sys.argv) > 1:
        application_file = sys.argv[1]
    if len(sys.argv) > 2:
        tty_device = sys.argv[2]
    if len(sys.argv) > 3:
        uid = int(sys.argv[3])

    if not os.path.isfile(application_file):
        # that's required to get not-so-dumb result from 2to3 tool
        txt = "ERROR: File not found: %s" % application_file
        print(txt)
        sys.exit(1)

    # Switch to bootloader if not already in it
    serial_port = connection.SetupSerial(tty_device, baudrate=connection.LED_BAUDRATE)
    serial_port.write(messages.PrepareBootloaderMsg(uid))
    serial_port.close()
    time.sleep(1.0)

    # Bootloader communicates at 9600 baud
    serial_port = connection.SetupSerial(tty_device, baudrate=9600)
    file = hexfile.load(application_file)
    frames = []
    byte_offset = 0
    for addr, data in file:
        if byte_offset == 0:
            frame = [
                0x01, # UID
                0x10, # Write Multiple Registers 
                0x00, 0x00, # address start
                0x00, 0x10, # number of bytes
                0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
                0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
                0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
                0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
                0xff, 0xff  # crc
            ]
            frame[0] = uid
            frame[2] = (addr & 0xff00) >> 8
            frame[3] = (addr & 0xff)
            frames.append(frame)

        frame[byte_offset + 6] = data
        if byte_offset == 31:
            crc = crc16.crc16(frame[0:38])
            frame[38] = (crc & 0x00ff)
            frame[39] = (crc & 0xff00) >> 8
            byte_offset = 0
        else:
            byte_offset += 1
    
    # Process last partial frame
    crc = crc16.crc16(frame[0:38])
    frame[38] = (crc & 0x00ff)
    frame[39] = (crc & 0xff00) >> 8

    for frame in frames:
        print('TX:' + ''.join([' %02x' % b for b in frame[0:38]]) + ' CRC [' + ''.join([' %02x' % b for b in frame[38:]]) + ']')
        serial_port.write(bytearray(frame))
        # 200ms should be plenty of time for the MCU to write the frame to flash
        time.sleep(0.2)

if __name__ == '__main__':
    main()