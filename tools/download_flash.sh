avrdude -v -pattiny85 -cusbtiny -U flash:r:/tmp/flash.bin:r
python bin2hex.py /tmp/flash.bin flash.hex