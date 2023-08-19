
#!/bin/bash

ffmpeg -i full/pulsing_dust.mov -vcodec h264 -an -ss 00:00:10 -t 00:00:30  pulsing_dust.mp4
ffmpeg -i full/radial_beams.mov -vcodec h264 -an -ss 00:00:10 -t 00:00:30 radial_beams.mp4
ffmpeg -i full/shifter_escape.mov -vcodec h264 -an -ss 00:00:01 -t 00:00:45 shifter_escape.mp4

