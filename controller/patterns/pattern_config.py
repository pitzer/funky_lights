from .rainbow_pattern import RainbowPattern
import numpy as np
from collections import namedtuple

import patterns.palettes as palettes
from patterns.color_roll_pattern import ColorRollPattern
from patterns.crossfade_pattern import CrossfadePattern
from patterns.fire_pattern import FirePatternUV
from patterns.flash_pattern import FlashPattern
from patterns.sparkle_pattern import SparklePattern
from patterns.sweep_pattern import SweepPattern
from patterns.theater_chase_pattern import TheaterChasePattern
from patterns.rainbow_pattern import RainbowPattern
from patterns.starburst_pattern import StarburstPattern
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
        #first row   
        # '0x0': (FirePatternUV, dict(palette=palettes.FIRE, width=2, height=100)),
        '0x0': (FirePatternUV, dict(palette=palettes.FIRE, width=2, height=100)),
        '1x0': (VideoPattern, dict(file='media/space_warp.mp4')),
        '2x0': (VideoPattern, dict(file='media/abstract_gradient_full.mp4')),
        '3x0': (VideoPattern, dict(file='media/matrix.mp4', crop=Rect(0, 100, 100, 1080))),
        '4x0': (VideoPattern, dict(file='media/blue_light_rays.mp4')),
        '5x0': (RainbowWavesPattern, dict(fps=5.0)),
        '6x0': (ColorRollPattern, dict()),
        '7x0': (VideoPattern, dict(file='media/flash.mp4', fps=5.0)),
        #second row
        '0x1': (VideoPattern, dict(file='media/abstract_green.mp4')),
        '1x1': (VideoPattern, dict(file='media/hearts.mp4')),
        '2x1': (VideoPattern, dict(file='media/rising_beams.mp4')),
        '3x1': (VideoPattern, dict(file='media/blue_horizon.mp4')),
        '4x1': (VideoPattern, dict(file='media/space_warp.mp4')),
        '5x1': (VideoPattern, dict(file='media/sparkling_ring.mp4')),
        '6x1': (VideoPattern, dict(file='media/neon_tunnel.mp4')),
        '7x1': (VideoPattern, dict(file='media/triangle_kaleidoscope.mp4')),
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
        'fire': (FirePatternUV, dict(palette=palettes.FIRE, width=2, height=100)),
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
