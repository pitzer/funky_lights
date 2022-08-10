from patterns.grid_pattern import GridPattern
import patterns.palettes as palettes
import numpy as np

class Ball():
    def __init__(self, x, y, size, color, x_inc, y_inc):
        self.x = x
        self.y = y
        self.size = size
        self.color= color
        self.x_inc = x_inc
        self.y_inc = y_inc

class BouncingBlocksPattern(GridPattern):
    def __init__(self):
        super().__init__()
        self.palette = palettes.COOL
        # Frequency of color change (in Hz)
        self.fps = 30
        self.num_balls = 20
        #starting positions
        self.x1 = 50
        self.y1 = 1
        self.x_inc = 1
        self.y_inc = 0.5
        self.size = 5
    
    def initialize(self):
        self.cumulative_delta = 1000  # set to an arbitrary high value
        self.current_color_index = 0
        self.grid.colorAll(self.palette[self.current_color_index])
        self.balls = []
        for ball in range(self.num_balls):
            xi = np.random.random()
            yi = np.random.random()
            cur_ball = Ball(
                np.random.randint(0,self.width),
                np.random.randint(0,self.height),
                self.size,
                self.palette[self.current_color_index+1],
                xi if xi > 0.5 else -xi,
                yi if yi < 0.5 else -yi
            )
            self.balls = np.append(self.balls, cur_ball)
            self.grid.colorCircle(cur_ball.x, cur_ball.y, cur_ball.size, cur_ball.color)
        
        super().initialize(self.grid)
    

    def animate(self, delta):
        self.cumulative_delta += delta
        if self.cumulative_delta < 1 / self.fps:
            return

        self.grid.colorAll(self.palette[self.current_color_index])

        for ball in self.balls:
            x2 = ball.x + ball.size
            y2 = ball.y + ball.size
            ball.x += ball.x_inc
            ball.y += ball.y_inc

            if ball.x >= self.width or ball.x <=0:
                ball.x_inc = ball.x_inc * -1
            if ball.y >= self.height or ball.y <=0:
                ball.y_inc = ball.y_inc * -1
            
            self.grid.colorArea(ball.x, x2, ball.y, y2, self.palette[self.current_color_index+1])

        super().animate()
        self.cumulative_delta = 0
        
