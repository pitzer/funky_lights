import numpy as np

TROPICAL = np.array(
    [[242, 207, 51], [245, 112, 76], [32, 158, 179], [240, 167, 141]], dtype=np.uint8)

BLUES = np.array(
    [[127, 178, 240], [65, 146, 217], [2, 136, 209], [0, 75, 141]], dtype=np.uint8)

# Approximate "black body radiation" palette, akin to the FastLED 'HeatColor' function. 
# Recommend that you use values 0-240 rather than the usual 0-255, as the last 15 colors 
# will be 'wrapping around' from the hot end to the cold end, which looks wrong.
HEAT = np.array(
    [(0x00, 0x00, 0x00), (0xFF, 0x00, 0x00), (0xFF, 0xFF, 0x00), (0xFF, 0xFF, 0xCC)], dtype=np.uint8)

FIRE = np.array([(0x00, 0x00, 0x00), (0x22, 0x00, 0x00), (
    0x88, 0x00, 0x00), (0xFF, 0x00, 0x00), (0xFF, 0x66, 0x00), (0xFF, 0xCC, 0x00)], dtype=np.uint8)
    
COOL = np.array(
    [(0x00, 0x00, 0xFF), (0x00, 0x99, 0xDD), (0x44, 0x44, 0x88), (0x99, 0x00, 0xDD)], dtype=np.uint8)
