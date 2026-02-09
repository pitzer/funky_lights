from patterns.pattern import Pattern

class ColorQuadrants(Pattern):
    def __init__(self):
        super().__init__()

    def initialize(self):
        for segment in self.segments:
            for i in range(segment.num_leds):
                pos = segment.led_positions[i]
                if pos[0] < 0.0:
                    segment.colors[i][0] = 0
                else:
                    segment.colors[i][0] = 255
                
                if pos[1] < 1.4:
                    segment.colors[i][1] = 0
                else:
                    segment.colors[i][1] = 255
                
                if pos[2] < 0.0:
                    segment.colors[i][2] = 0
                else:
                    segment.colors[i][2] = 255

    async def animate(self, delta):
        return