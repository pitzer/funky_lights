#!/bin/bash

# clean
mkdir -p build
rm -rf build/*
rm -rf *.hex
rm -rf *.eep

# 1280 byte
# boot reserve
ENTRYADDR=0x1C00

CFLAGS="-Wall -DAPPADDR=$ENTRYADDR -DF_CPU=8000000 -mrelax -mmcu=attiny85 -ffunction-sections -Os -funsigned-char -funsigned-bitfields -fpack-struct -fshort-enums -Wstrict-prototypes -std=gnu99 -MMD -MP -I./libs -I./devs"

echo
echo "GCC for AVR (8.0.1 is recommended, LTO code size fits/smaller)."
echo


##
## BOOT LOADER
##

avr-gcc -c $CFLAGS -flto -MF build/crt1.o.d     -Wa,-adhlns=build/crt1.c.lst     crt1.S          -o build/crt1.o
avr-gcc -c $CFLAGS -flto -MF build/crc16.o.d    -Wa,-adhlns=build/crc16.lst      libs/crc16.c    -o build/crc16.o
avr-gcc -c $CFLAGS -flto -MF build/softuart.o.d -Wa,-adhlns=build/softuart.c.lst libs/softuart.c -o build/softuart.o
avr-gcc -c $CFLAGS -flto -MF build/pgmflash.o.d -Wa,-adhlns=build/pgmflash.lst   libs/pgmflash.c -o build/pgmflash.o
avr-gcc -c $CFLAGS -flto -MF build/eeprom.o.d   -Wa,-adhlns=build/eeprom.c.lst   libs/eeprom.c   -o build/eeprom.o
# boot.c
avr-gcc -c $CFLAGS -flto -MF build/boot.o.d     -Wa,-adhlns=build/boot.lst       boot.c          -o build/boot.o

avr-gcc $CFLAGS -flto -ffreestanding -nostartfiles -o build/boot.elf build/crt1.o \
                build/boot.o build/softuart.o build/crc16.o \
                build/eeprom.o build/pgmflash.o \
        -Wl,--relax,--section-start=.text=$ENTRYADDR,--gc-sections,-Map=build/boot.map


echo "BOOT:"
avr-size --format=avr --mcu=attiny85 build/boot.elf
avr-objcopy -j .text -j .data -O ihex build/boot.elf boot.hex

BOOTSIZE=$(avr-size --format=avr --mcu=attiny85 build/boot.elf | grep Program | awk '{print $2}')
printf "BOOT: 0x%04x - 0x%04x \n\n" $ENTRYADDR $(( $ENTRYADDR+$BOOTSIZE ))

## check if main overlap boot
if [ $(( $MAINSIZE )) -ge $(( $ENTRYADDR )) ]
then
  printf "ERROR main end [0x%04x] overlap boot begin [0x%04x]\n\n" $MAINSIZE $ENTRYADDR
#   rm -rf build/*
#   rm -rf *.hex
#   rm -rf *.eep
fi