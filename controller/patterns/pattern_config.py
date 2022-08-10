from patterns.fire_pattern import FirePattern, FirePatternUV
from patterns.crossfade_pattern import CrossfadePattern
import patterns.palettes as palettes
from patterns.rg_transition_pattern import RGTRansitionPattern
from patterns.bouncing_blocks import BouncingBlocksPattern
from patterns.rainbow_pattern import RainbowPattern
from patterns.video_pattern import VideoPattern, Rect


DEFAULT_CONFIG = [
    (FirePatternUV, dict(palette=palettes.FIRE, width=2, height=100)),
    (CrossfadePattern, dict()),
    (BouncingBlocksPattern, dict()),
    (RainbowPattern, dict()),
    (VideoPattern, dict(file='media/butter_churn.mp4', fps=20, crop=Rect(60, 60, 60, 60))),
    (VideoPattern, dict(file='media/psychill1.mp4', fps=20, crop=Rect(60, 130, 60, 60))),
    (VideoPattern, dict(file='media/psychill2.mp4', fps=20, crop=Rect(60, 130, 60, 60))),
    (VideoPattern, dict(file='media/milkdrop.mp4', fps=20, crop=Rect(60, 130, 60, 60))),
    (RGTRansitionPattern, dict()),
]

