#!/bin/bash

/Applications/Arduino.app/Contents/Java/hardware/tools/avr/bin/avrdude -C/Applications/Arduino.app/Contents/Java/hardware/tools/avr/etc/avrdude.conf -v -v -v -v -pattiny85 -cusbtiny -U flash:w:boot.hex
