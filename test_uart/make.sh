#!/bin/bash

MAX_MAINSIZE=7168

make -f Attiny85.mk

MAINSIZE=$(avr-size --format=avr --mcu=attiny85 build/test_uart.elf | grep Program | awk '{print $2}')
printf "MAIN: 0x0000 - 0x%04x \n\n" $MAINSIZE

## check if main overlap boot
if [ $(( $MAINSIZE )) -ge $(( $MAX_MAINSIZE )) ]
then
  printf "ERROR main end [0x%04x] overlap boot begin [0x%04x]\n\n" $MAINSIZE $MAX_MAINSIZE
  rm -rf build/*
fi
