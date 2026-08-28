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
from patterns.segment_id_pattern import SegmentIdPattern
from patterns.static_color_pattern import StaticColorPattern, BreathingColorPattern


PatternConfig = namedtuple(
    'PatternConfig', ['rotation', 'manual', 'special_effects', 'eyes'])

SegmentMask = namedtuple(
    'SegmentMask', ['segment_uid', 'start', 'end'])

DEFAULT_CONFIG = PatternConfig(
    # This is the default pattern rotation. These patterns are rotated unless manually changed.
    rotation = {
        'slot_00': (BreathingColorPattern, dict(color=(147, 127, 245))),
        'slot_01': (VideoPattern, dict(file='media/blue_light_rays.mp4')),
        'slot_02': (VideoPattern, dict(file='media/space_warp.mp4')),
        'slot_03': (VideoPattern, dict(file='media/rising_beams.mp4')),
        'slot_04': (VideoPattern, dict(file='media/radial_beams.mp4', crop=Rect(0, 0, 850, 720))),
        'slot_05': (VideoPattern, dict(file='media/hearts.mp4')),
        'slot_06': (VideoPattern, dict(file='media/matrix.mp4', crop=Rect(0, 100, 100, 1080))),
        'slot_07': (VideoPattern, dict(file='media/blue_lines.mp4')),
        'slot_08': (FirePatternUV, dict(palette=palettes.FIRE, width=2, height=100)),
        'slot_09': (RainbowWavesPattern, dict()),
    },

    # Manual patterns are not part of the pattern rotation. They will only play when selected 
    # through a controller.
    manual = {
        'fire': (FirePatternUV, dict(palette=palettes.FIRE, width=2, height=100)),
        'shifter_escape': (VideoPattern, dict(file='media/shifter_escape.mp4')),
        'radial_beams': (VideoPattern, dict(file='media/radial_beams.mp4', crop=Rect(0, 0, 850, 720))),
        'butter_churn': (VideoPattern, dict(file='media/butter_churn.mp4', crop=Rect(60, 60, 60, 60))),
        'psychill1': (VideoPattern, dict(file='media/psychill1.mp4', fps=10)),
        'psychill1_crop': (VideoPattern, dict(file='media/psychill1.mp4', crop=Rect(60, 130, 60, 60))),
        'psychill2': (VideoPattern, dict(file='media/psychill2.mp4', crop=Rect(60, 130, 60, 60))),
        'rainbow_waves': (RainbowWavesPattern, dict()),
        'blue_lines': (VideoPattern, dict(file='media/blue_lines.mp4')),
        'hearts': (VideoPattern, dict(file='media/hearts.mp4')),
        'rising_beams': (VideoPattern, dict(file='media/rising_beams.mp4')),
        'blue_horizon': (VideoPattern, dict(file='media/blue_horizon.mp4')),
        'space_warp': (VideoPattern, dict(file='media/space_warp.mp4')),
        'sparkling_ring': (VideoPattern, dict(file='media/sparkling_ring.mp4')),
        'neon_tunnel': (VideoPattern, dict(file='media/neon_tunnel.mp4')),
        'triangle_kaleidoscope': (VideoPattern, dict(file='media/triangle_kaleidoscope.mp4')),
        'matrix': (VideoPattern, dict(file='media/matrix.mp4', crop=Rect(0, 100, 100, 1080))),
        'blue_light_rays': (VideoPattern, dict(file='media/blue_light_rays.mp4')),
        'rainbow': (RainbowWavesPattern, dict(fps=5.0)),
        'color_roll': (ColorRollPattern, dict()),        '0x2': (CrossfadePattern, dict()),
        'theater_chase': (TheaterChasePattern, dict(speed=1.5, step_size=3)),
        'sweep': (SweepPattern, dict(decay_param=0.5, sweep_speed=0.3)),
        'color_roll': (ColorRollPattern, dict()),
        'segment_id': (SegmentIdPattern, dict()),
        'bouncing_blocks': (BouncingBlocksPattern, dict()),
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

