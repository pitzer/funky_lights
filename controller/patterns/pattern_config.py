import numpy as np

from controller.patterns.sparkle_pattern import SparklePattern
from patterns.fire_pattern import FirePattern, FirePatternUV
from patterns.crossfade_pattern import CrossfadePattern
import patterns.palettes as palettes
from patterns.rg_transition_pattern import RGTRansitionPattern
from patterns.sparkle_pattern import SparklePattern
from patterns.sweep_pattern import SweepPattern
from patterns.theater_chase_pattern import TheaterChasePattern
from patterns.video_pattern import VideoPattern, Rect

DEFAULT_CONFIG = [
    (SparklePattern, dict(color=np.array([255, 255, 255]), sparkle_probability=0.001, decay_param=0.95)),
    (TheaterChasePattern, dict(color=np.array([255, 255, 255]), sparkle_probability=0.001, decay_param=0.95)),
    (SweepPattern, dict(color=np.array([255, 255, 255]), decay_param=0.5, sweep_speed=0.3)),
    (FirePatternUV, dict(palette=palettes.FIRE, width=2, height=100)),
    (CrossfadePattern, dict(palette=palettes.BLUES, fps=25)),
    (VideoPattern, dict(file='media/butter_churn.mp4', fps=20, crop=Rect(60, 60, 60, 60))),
    (VideoPattern, dict(file='media/psychill1.mp4', fps=20, crop=Rect(60, 130, 60, 60))),
    (VideoPattern, dict(file='media/psychill2.mp4', fps=20, crop=Rect(60, 130, 60, 60))),
    (VideoPattern, dict(file='media/milkdrop.mp4', fps=20, crop=Rect(60, 130, 60, 60))),
    (RGTRansitionPattern, dict()),
]

