from .rainbow_pattern import RainbowPattern
import numpy as np
from collections import namedtuple

import patterns.palettes as palettes
from patterns.color_roll_pattern import ColorRollPattern
from patterns.color_quadrants import ColorQuadrants
from patterns.crossfade_pattern import CrossfadePattern
from patterns.fire_pattern import FirePatternUV
from patterns.flash_pattern import FlashPattern
from patterns.sparkle_pattern import SparklePattern
from patterns.sweep_pattern import SweepPattern
from patterns.theater_chase_pattern import TheaterChasePattern
from patterns.rainbow_pattern import RainbowPattern
from patterns.starburst_pattern import StarburstPattern
from controller.patterns.bed_patterns import StaticColorPattern, BreathingColorPattern
from patterns.checkers_pattern import CheckersPattern
from patterns.rainbow_waves_pattern import RainbowWavesPattern
from patterns.bouncing_blocks_pattern import BouncingBlocksPattern
from patterns.video_pattern import VideoPattern, Rect

PatternConfig = namedtuple(
    'PatternConfig', ['rotation', 'manual', 'special_effects', 'eyes'])

SegmentMask = namedtuple(
    'SegmentMask', ['segment_uid', 'start', 'end'])

DEFAULT_CONFIG = PatternConfig(
    # This is the default pattern rotation. These patterns are rotated unless manually changed.
    rotation = {
        'twilight_breath': (BreathingColorPattern, dict(
            headboard_color = (48, 44, 96), 
            center_color = (72, 36, 94),
            front_color = (98, 56, 130),
            cage_color = (42, 18, 58),
            breath_period_s = 2,
            breath_amplitude_percent = 0.1
            )),
        'twilight_static': (StaticColorPattern, dict(
            headboard_color = (48, 44, 96), 
            center_color = (72, 36, 94),
            front_color = (98, 56, 130),
            cage_color = (42, 18, 58)
            )),
        'fire': (FirePatternUV, dict(palette=palettes.FIRE, width=10, height=100)),
        'space_warp': (VideoPattern, dict(file='media/space_warp.mp4')),
        'abstract_gradient': (VideoPattern, dict(file='media/abstract_gradient_full.mp4')),
        'matrix': (VideoPattern, dict(file='media/matrix.mp4', crop=Rect(0, 100, 100, 1080))),
        'blue_light_rays': (VideoPattern, dict(file='media/blue_light_rays.mp4')),
        'rainbow': (RainbowWavesPattern, dict(fps=5.0)),
        'color_roll': (ColorRollPattern, dict()),
        'flash': (VideoPattern, dict(file='media/flash.mp4', fps=5.0)),
    },

    # Manual patterns are not part of the pattern rotation. They will only play when selected 
    # through a controller.
    manual = {
        #third row
        '0x2': (CrossfadePattern, dict()),
        '1x2': (TheaterChasePattern, dict(speed=1.5, step_size=3)),
        '2x2': (SweepPattern, dict(decay_param=0.5, sweep_speed=0.3)),
        '3x2': (ColorRollPattern, dict()),
        '4x2': (BouncingBlocksPattern, dict()),
    },

    # Effect patterns are overlayed on top of any pattern that is current playing.
    special_effects = {
        #bottom row for easy identification
        '0x7': (FlashPattern, dict()),
        '1x7': (SparklePattern, dict(sparkle_probability=0.001, decay_param=0.95)),
        '2x7': (CheckersPattern, dict(decay_param=0.95)),
        '3x7': (StarburstPattern, dict(decay_param=0.95))
    },

    # Eye patterns
    eyes = {
        '0x3': (VideoPattern, dict(file='media/eyes.mp4', include_segments=[50, 51], segment_masks=[SegmentMask(50, 0, 97), SegmentMask(51, 0, 91)])),
    }
) 

BED_CONFIG = PatternConfig(
    rotation={
        'twilight_breath': (BreathingColorPattern, dict(
            headboard_color = (48, 44, 96), 
            center_color = (72, 36, 94),
            front_color = (98, 56, 130),
            cage_color = (42, 18, 58),
            breath_period_s = 10,
            breath_amplitude_percent = 0.2
            )),
        'fire': (FirePatternUV, dict(palette=palettes.FIRE, width=10, height=100)),
        'space_warp': (VideoPattern, dict(file='media/space_warp.mp4')),
        'abstract_gradient': (VideoPattern, dict(file='media/abstract_gradient_full.mp4')),
        'matrix': (VideoPattern, dict(file='media/matrix.mp4', crop=Rect(0, 100, 100, 1080))),
        'blue_light_rays': (VideoPattern, dict(file='media/blue_light_rays.mp4')),
        'rainbow': (RainbowWavesPattern, dict(fps=5.0)),
        'color_roll': (ColorRollPattern, dict()),
        'flash': (VideoPattern, dict(file='media/flash.mp4', fps=5.0)),
    },
    manual={},
    special_effects={},
    eyes={}
)
