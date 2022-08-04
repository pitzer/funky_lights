# Set this if the IDE is not in your $PATH or you want to use a specific version:
ARDUINO_DIR = /Applications/Arduino.app/Contents/Java

# Programmer type:
ISP_PROG = usbasp

# https://github.com/damellis/attiny (1.5+)
ALTERNATE_CORE = attiny-master
ALTERNATE_CORE_PATH = $(HOME)/Library/Arduino15/packages/attiny/hardware/avr/1.0.2
BOARD_TAG = ATtinyX5
BOARD_SUB = attiny85
F_CPU = 16000000L
# Reserve 1024 byte for the bootloader
HEX_MAXIMUM_SIZE = 7168

ARDUINO_LIBS = CRC EEPROM FAB_LED-master TXOnlySerial

# Overwrite path for build artifacts
OBJDIR = build

# Path to the Arduino Makefile
include Arduino.mk