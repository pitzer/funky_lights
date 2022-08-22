from .rainbow_pattern import RainbowPattern
import numpy as np
from collections import namedtuple

import patterns.palettes as palettes
from patterns.color_roll_pattern import ColorRollPattern
from patterns.crossfade_pattern import CrossfadePattern
from patterns.fire_pattern import FirePatternUV
from patterns.sparkle_pattern import SparklePattern
from patterns.sweep_pattern import SweepPattern
from patterns.theater_chase_pattern import TheaterChasePattern
from patterns.rainbow_pattern import RainbowPattern
from patterns.rainbow_waves_pattern import RainbowWavesPattern
from patterns.bouncing_blocks_pattern import BouncingBlocksPattern
from patterns.video_pattern import VideoPattern, Rect

PatternConfig = namedtuple(
    'PatternConfig', ['rotation', 'manual', 'special_effects', 'eyes'])

DEFAULT_CONFIG = PatternConfig(
    # This is the default pattern rotation. These patterns are rotated unless manually changed.
    rotation = {   
        '0x0': (FirePatternUV, dict(palette=palettes.FIRE, width=2, height=100)),
        '1x0': (VideoPattern, dict(file='media/shifter_escape.mp4')),
        '2x0': (VideoPattern, dict(file='media/radial_beams.mp4', crop=Rect(0, 0, 850, 720))),
        '3x0': (VideoPattern, dict(file='media/butter_churn.mp4', crop=Rect(60, 60, 60, 60))),
        '4x0': (VideoPattern, dict(file='media/psychill1.mp4', fps=10)),
        '5x0': (VideoPattern, dict(file='media/psychill1.mp4', crop=Rect(60, 130, 60, 60))),
        '6x0': (VideoPattern, dict(file='media/psychill2.mp4', crop=Rect(60, 130, 60, 60))),
        '7x0': (RainbowWavesPattern, dict()),
    },

    # Manual patterns are not part of the pattern rotation. They will only play when selected 
    # through a controller.
    manual = {
        '0x1': (CrossfadePattern, dict()),
        '1x1': (TheaterChasePattern, dict(speed=1.5, step_size=3)),
        '2x1': (SweepPattern, dict(decay_param=0.5, sweep_speed=0.3)),
        '3x1': (ColorRollPattern, dict()),
        '4x1': (BouncingBlocksPattern, dict()),
    },

    # Effect patterns are overlayed on top of any pattern that is current playing.
    special_effects = {
        '0x2': (SparklePattern, dict(sparkle_probability=0.001, decay_param=0.95)),
    },

    # Eye patterns
    eyes = {
        '0x3': (VideoPattern, dict(file='media/eyes.mp4', include_segments=[50, 51])),
    }
) 

