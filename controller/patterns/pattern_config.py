from patterns.fire_pattern import FirePattern, FirePatternUV, PALETTE_FIRE
from patterns.rg_transition_pattern import RGTRansitionPattern
from patterns.solid_color_blink import SolidColorBlinkPattern, PALETTE_TROPICAL
from patterns.video_pattern import VideoPattern, Rect


DEFAULT_CONFIG = [
    (FirePatternUV, dict(palette=PALETTE_FIRE, width=2, height=100)),
    (SolidColorBlinkPattern, dict(palette=PALETTE_TROPICAL)),
    (VideoPattern, dict(file='media/butter_churn.mp4', fps=20, crop=Rect(60, 60, 60, 60))),
    (VideoPattern, dict(file='media/psychill1.mp4', fps=20, crop=Rect(60, 130, 60, 60))),
    (VideoPattern, dict(file='media/psychill2.mp4', fps=20, crop=Rect(60, 130, 60, 60))),
    (VideoPattern, dict(file='media/milkdrop.mp4', fps=20, crop=Rect(60, 130, 60, 60))),
    (RGTRansitionPattern, dict()),
]



