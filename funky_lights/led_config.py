import numpy as np

class LedConfig():
    def __init__(self):
        self.total_num_leds = 0
        self.total_length = 0
        self.total_num_segments = 0
        self.led_segments = []

    def to_dict(self):
        return {
            'total_num_leds': self.total_num_leds,
            'total_length': self.total_length,
            'total_num_segments': self.total_num_segments,
            'led_segments': [s.to_dict() for s in self.led_segments]
        }


class Segment():
    def __init__(self, uid, name, points, num_leds, length):
        self.uid = uid
        self.name = name
        self.points = points
        self.num_leds = num_leds
        self.length = length

    def merge(self, other):
        self.points = np.concatenate((self.points, other.points), axis=0)
        self.num_leds += other.num_leds
        self.length += other.length

    def to_dict(self):
        return {
            'uid': self.uid,
            'name': self.name,
            'num_leds': self.num_leds,
            'length': self.length,
            'led_positions': self.points.tolist()
        }
