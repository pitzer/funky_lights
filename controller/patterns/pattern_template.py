from patterns.pattern import Pattern
import patterns.palettes as palettes
import numpy as np


class SolidColorBlinkPattern(Pattern):
    def __init__(self):
        super().__init__()

        # The following members are options that can be overwritten when adding the pattern
        # to the pattern config.

        # Color palette to cycle through
        self.params.palette = palettes.TROPICAL

        # Frequency of color change (in Hz)
        self.params.fps = 0.5

    def initialize(self):
        """ This method gets called once when the pattern is first instantiated."""
        self.cumulative_delta = 1000  # set to an arbitrary high value
        self.current_color_index = 0
        pass

    async def animate(self, delta):
        """ animate is called at every timestep the lights are updated. Here is where the colors 
            of the desired segments in self.segments should be updated.
        Args:
            delta: time in seconds since the last animation
        """

        # First check if it is time to cycle to the next color in the palette
        self.cumulative_delta += delta
        if self.cumulative_delta < 1 / self.params.fps:
            return

        # Cycle to the next color
        self.current_color_index = (
            self.current_color_index + 1) % self.params.palette.shape[0]
  
        # Update segments to use the new color. 
        # 
        # Each "Segment" represents a single LED light strip on the art car. We are planning to have
        # on the order 80 segments in the final configuration. The segments are configure in the 
        # light controller using the config/led_config.json files. self.segments is populated from this
        # file when the Pattern is initialized.
        # 
        # The color array in each Segment has one RGB entry per LED on the light strip. The main purpose 
        # the animate method is updating the color array. The Segment also has a unique id. This can be 
        # used to only update certain segments during the animation. The CSV files in the config directory 
        # and the https://docs.google.com/spreadsheets/d/1Ga7npntoar6uwUSJpEfCIg9-kc4bZ1iFmo08Xg21sjo
        # and config/bus_config.all.json can be helpful to understand which segments belong to which part 
        # of the elephant, e.g. [1, 2, 3] are the three long strips going over the dome front to back.
        for segment in self.segments:
            for color in segment.colors:
                np.copyto(color, self.params.palette[self.current_color_index])

        # Reset time
        self.cumulative_delta = 0