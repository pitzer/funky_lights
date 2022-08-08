import numpy as np

class Segment:
    def __init__(self, uid, num_leds, led_positions):
        self.uid = uid
        self.num_leds = num_leds
        self.colors = np.array([[255, 0, 0] for i in range(num_leds)])
        self.led_positions = np.array(led_positions)


#Allows direct control of Segments
class Pattern:
    def __init__(self):
        self.segments = []

    def prepareSegments(self, led_config):
        for s in led_config['led_segments']:
            segment = Segment(s['uid'], s['num_leds'], s['led_positions'])
            self.segments.append(segment)

    def initialize(self):
        pass
        
    def animate(self, delta):
        pass