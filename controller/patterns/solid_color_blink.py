from patterns.pattern import Pattern
import numpy as np

PALETTE_TROPICAL = np.array(
    [[242, 207, 51], [245, 112, 76], [32, 158, 179], [240, 167, 141]])


class SolidColorBlinkPattern(Pattern):
    def __init__(self):
        super().__init__()

        # The following members are options that can be overwritten when adding the pattern
        # to the pattern config.

        # Color palette to cycle through
        self.palette = PALETTE_TROPICAL

        # Frequency of color change (in Hz)
        self.fps = 0.5

    def initialize(self):
        """ This method gets called once when the pattern is first instantiated."""
        self.cumulative_delta = 1000  # set to an arbitrary high value
        self.current_color_index = 0
        pass

    def animate(self, delta):
        """ animate is called at every timestep the lights are updated. Here is where the colors 
            of the desired segments in self.segments should be updated.
        Args:
            delta: time in seconds since the last animation
        """

        # First check if it is time to cycle to the next color in the palette
        self.cumulative_delta += delta
        if self.cumulative_delta < 1 / self.fps:
            return

        # Cycle to the next color
        self.current_color_index = (
            self.current_color_index + 1) % self.palette.shape[0]
        # Update segments to use the new color
        for segment in self.segments:
            for color in segment.colors:
                np.copyto(color, self.palette[self.current_color_index])

        # Reset time
        self.cumulative_delta = 0
