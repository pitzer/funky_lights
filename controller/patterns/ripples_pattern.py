from patterns.pattern import PatternUV
from collections import namedtuple
import numpy as np

RippleSeed = namedtuple('RippleSeed', ['position', 'time'])

class RipplesPattern(PatternUV):
    def __init__(self, width = 100, height = 100):
        super().__init__()
        self.params.color = np.array([255, 255, 255], dtype=np.uint8)
        self.params.period_s = 2.0
        self.params.speed = 1.0
        self.time = 0
        self.ripple_seeds = [
            RippleSeed(position=np.array([128, 128]), time=0),
            RippleSeed(position=np.array([128, 128]), time=5.0),
        ]
        
    def initialize(self):
        self.generateUVCoordinates(255.0, 255.0)
    
    def reset(self):
        super().reset()
        self.initialize()

    async def animate(self, delta):
        self.time += delta
        # Remove old seeds
        self.ripple_seeds = list(filter(lambda s: self.time - s.time < 20.0, self.ripple_seeds))
        # Create new ones randomly
        if np.random.rand() < delta / self.params.period_s:
            new_seed = RippleSeed(position=np.random.rand(2) * 255.0, time=self.time)
            self.ripple_seeds.append(new_seed)
        # Compute ripple effect
        for segment in self.segments:
            intensities = np.zeros(segment.num_leds)
            for seed in self.ripple_seeds:
                if self.time < seed.time:
                    continue
                distances = np.linalg.norm((segment.uv - seed.position), axis=1)
                phase = ((self.time - seed.time) / self.params.speed - distances / 50.0) * 2 * np.pi
                seed_intensities = np.sin(phase) ** 2 / phase
                seed_intensities[phase <= 0] = 0
                intensities += seed_intensities
        
            segment.colors = np.clip(intensities[:, np.newaxis] * self.params.color, 0, 255).astype(np.uint8)
