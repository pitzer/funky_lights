

def crc16(data):
    crc = 0xffff
    for b in data:
        # XOR byte into least
        # significant byte of crc
        crc ^= b

        # loop over each bit
        for i in range(8, 0, -1):
            # if the LSB is set
            if (crc & 0x0001) != 0:
                crc >>= 1;  # shift right and XOR 0xa001
                crc  ^= 0xa001
            else:           # else LSB is not set
                crc >>= 1;  # just shift right

    return crc