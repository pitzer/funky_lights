import numpy as np

def clamp(minimum, x, maximum):
    return max(minimum, min(x, maximum))

def rotateLedPositions(led_positions, angle):
    # Rotate the LED positions by the given angle (in degrees) around the Y-axis
    angle_rad = np.radians(angle)
    cos_angle = np.cos(angle_rad)
    sin_angle = np.sin(angle_rad)

    rotated_positions = []
    for pos in led_positions:
        x, y, z = pos
        new_x = x * cos_angle + z * sin_angle
        new_y = y
        new_z = -x * sin_angle + z * cos_angle
        rotated_positions.append((new_x, new_y, new_z))

    return rotated_positions

def rippleBrightnesses(num_leds, center_index, time, period, speed, decay_time, decay_leds):
    """ Return brightness values (between 0 and 1) simulating a ripple effect emanating from the center LED over time
    Arguments:
        num_leds: Total number of LEDs in the strip
        center_index: Index of the center LED where the ripple starts
        time: Time since the ripple started, in seconds
        period: Time it takes for one full ripple cycle (in seconds)
        speed: Speed at which the ripple propagates (in leds/second)
        decay_time: Time it takes for the ripple to decay by 50% (in seconds)
        decay_leds: Number of LEDs over which the ripple decays to 50%
    """
    brightnesses = np.zeros(num_leds)
    if time < decay_time / 2.0:
        time_decay = time * 2.0 / decay_time
    else:
        time_decay = 0.5 ** (time - decay_time / 2.0)

    distances = np.abs(np.arange(num_leds) - center_index)
    phase = (time / period - distances / speed) * 2 * np.pi
    spatial_decay = 0.5 ** (distances / decay_leds)

    brightnesses = time_decay * np.sin(phase) * spatial_decay

    return brightnesses