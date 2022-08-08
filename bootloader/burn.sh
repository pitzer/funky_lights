#!/bin/bash

if [ $# -ne 1 ]
then
    echo "Usage: `basename $0` UID"
    exit 1
fi

if [ $1 -gt 255 ] || [ $1 -le 0 ]
then
        echo "Please enter at least a valid UID [0...255]"
        exit 1
fi

avrdude_binary='/Applications/Arduino.app/Contents/Java/hardware/tools/avr/bin/avrdude'
avrdude_conf='/Applications/Arduino.app/Contents/Java/hardware/tools/avr/etc/avrdude.conf'
bootloader_hex_file='boot.hex'
low_fuse='0xf1'
high_fuse='0xd3'
extended_fuse='0xfe'

avrdude_cmd="$avrdude_binary -C$avrdude_conf -pattiny85 -cusbtiny -U efuse:w:${extended_fuse}:m -U hfuse:w:${high_fuse}:m -U lfuse:w:${low_fuse}:m -U flash:w:$bootloader_hex_file -Ueeprom:w:0x$(printf "%.2x" $1):m"
echo $avrdude_cmd
eval $avrdude_cmd