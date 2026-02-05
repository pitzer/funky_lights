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