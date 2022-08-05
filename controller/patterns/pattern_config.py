from patterns.fire_pattern import FirePattern, FirePatternUV, PALETTE_FIRE
from patterns.rg_transition_pattern import RGTRansitionPattern
from patterns.video_pattern import VideoPattern, Rect


DEFAULT_CONFIG = [
    ('0x0', FirePatternUV, dict(palette=PALETTE_FIRE, width=2, height=100)),
    ('1x0', VideoPattern, dict(file='media/butter_churn.mp4', fps=20, crop=Rect(60, 60, 60, 60))),
    ('2x0', VideoPattern, dict(file='media/psychill1.mp4', fps=20, crop=Rect(60, 130, 60, 60))),
    ('3x0', VideoPattern, dict(file='media/psychill2.mp4', fps=20, crop=Rect(60, 130, 60, 60))),
    ('4x0', VideoPattern, dict(file='media/milkdrop.mp4', fps=20, crop=Rect(60, 130, 60, 60))),
    ('5x0', RGTRansitionPattern, dict()),
]



