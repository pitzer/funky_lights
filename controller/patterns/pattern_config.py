from .rainbow_pattern import RainbowPattern
import numpy as np

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

DEFAULT_CONFIG = dict(
    standard_patterns=[
    # Standard patterns
    ('0x0', FirePatternUV, dict(palette=palettes.FIRE, width=2, height=100)),
    ('1x0', CrossfadePattern, dict()),
    ('2x0', TheaterChasePattern, dict(speed=1.5, step_size=3)),
    ('3x0', SweepPattern, dict(decay_param=0.5, sweep_speed=0.3)),
    ('4x0', ColorRollPattern, dict())
    # Video patterns
    ('0x1', VideoPattern, dict(file='media/shifter_escape.mp4')),
    ('1x1', VideoPattern, dict(file='media/radial_beams.mp4', crop=Rect(0, 0, 850, 720))),
    ('2x1', VideoPattern, dict(file='media/butter_churn.mp4', crop=Rect(60, 60, 60, 60))),
    ('3x1', VideoPattern, dict(file='media/psychill1.mp4', fps=10)),
    ('4x1', VideoPattern, dict(file='media/psychill1.mp4', crop=Rect(60, 130, 60, 60))),
    ('5x1', VideoPattern, dict(file='media/psychill2.mp4', crop=Rect(60, 130, 60, 60))),
    ]

    effect_patterns=[
    # Effect patterns
    ('0x2', SparklePattern, dict(sparkle_probability=0.001, decay_param=0.95)),
    ('1x2', RainbowWavesPattern, dict()),
    ('1x3', BouncingBlocksPattern, dict())
    ]

    # Eyes
    eye_patterns=[
    ('0x5', VideoPattern, dict(file='media/eyes.mp4', include_segments=[50, 51])),
    ]
) 
