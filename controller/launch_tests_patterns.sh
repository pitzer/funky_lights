#!/bin/bash

serials=`ls /dev/serial/by-id/*`

for serial in $serials
do
	python ./test_pattern.py $serial&
done
