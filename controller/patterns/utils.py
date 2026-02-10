import numpy as np

def clamp(minimum, x, maximum):
    return max(minimum, min(x, maximum))

def expandKeys(dictionnary, allowed_keys):
    """ Given a dictionnary with string keys that are potentially condensed at 'key1+key2',
    return a new dictionnary where the keys are expanded to the allowed keys, and the values are copied."""
    new_dictionnary = {}
    for key in dictionnary.keys():
        if "+" in key:
            keys = key.split("+")
            for k in keys:
                k = k.strip()
                if k not in allowed_keys:
                    raise ValueError(f"Invalid key: {k}")
                new_dictionnary[k] = dictionnary[key]
        else:
            if key not in allowed_keys:
                raise ValueError(f"Invalid key: {key}")
            new_dictionnary[key] = dictionnary[key]
    return new_dictionnary

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

def scaleColors(color, intensities, amplitude_pct):
    """ Scale the colors by the given intensities and amplitude percentage, and clip to [0, 255]. """
    if amplitude_pct > 0:
        return np.clip(color * intensities[:, np.newaxis] * amplitude_pct, 0, 255).astype(np.uint8)
    else:
        return np.clip(color * (1.0 + intensities[:, np.newaxis] * amplitude_pct), 0, 255).astype(np.uint8)