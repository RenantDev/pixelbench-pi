"""Every colour in the scene, in one place.

Pixel art lives on a limited palette. The two ramps below (sky and sea) are the
only gradients in the whole renderer; everything else is a flat colour picked to
sit somewhere on those ramps, so the picture reads as one image instead of a
collage.
"""

import numpy as np

# Limited palette - sunset sky fading into night.
SKY_PALETTE = np.array([
    (18, 16, 40), (28, 22, 58), (44, 28, 74), (66, 34, 86),
    (92, 42, 92), (124, 52, 92), (158, 66, 88), (190, 84, 82),
    (216, 106, 76), (234, 134, 74), (246, 166, 84), (250, 198, 108),
], dtype=np.uint8)

# Sea ramp: navy at the bottom (where you look down into the water) climbing to
# WARM tones at the top. The crests mirror the sunset sky, so the water has to
# pull the orange of the sun into it - an all-blue sea would fight the scene.
SEA_PALETTE = np.array([
    (12, 20, 42), (16, 28, 56), (21, 38, 70), (28, 50, 86),
    (36, 63, 101), (48, 78, 114), (64, 94, 124), (88, 110, 132),
    (118, 126, 138), (152, 142, 141), (186, 160, 150), (214, 184, 164),
    (238, 212, 186),
], dtype=np.uint8)
FOAM_COLOR = np.array((246, 230, 210), dtype=np.uint8)

FAR_HILL_COLOR = np.array((52, 40, 78), dtype=np.uint8)
NEAR_HILL_COLOR = np.array((26, 20, 44), dtype=np.uint8)
CLOUD_COLOR = np.array((236, 156, 122), dtype=np.uint8)
CLOUD_SHADOW_COLOR = np.array((176, 96, 96), dtype=np.uint8)
SUN_COLOR = np.array((255, 236, 150), dtype=np.uint8)
SUN_EDGE_COLOR = np.array((252, 190, 92), dtype=np.uint8)

# Letter -> colour key used by the ASCII sprite art (see `art()` in sprites.py).
ART_COLORS = {
    "k": (38, 28, 34),      # outline / hair
    "p": (214, 158, 112),   # skin
    "c": (196, 88, 74),     # torn shirt
    "b": (74, 62, 92),      # trousers
    "f": (252, 216, 120),   # fire - core
    "g": (240, 140, 56),    # fire - middle
    "v": (192, 66, 42),     # fire - edge
    "m": (104, 72, 46),     # wood
}

SAND_LIGHT = (232, 202, 146)
SAND = (204, 170, 112)
SAND_DARK = (166, 132, 84)
SAND_WET = (132, 106, 76)
BEACH_FOAM = (226, 238, 236)
ROCK_LIGHT = (212, 196, 176)     # the rock corner catching the sunset
ROCK = (148, 130, 120)           # body
ROCK_DARK = (106, 90, 84)        # shaded side
ROCK_SHADOW = (150, 118, 78)     # shadow cast on the sand
TRUNK = (96, 66, 42)
TRUNK_LIGHT = (132, 94, 58)
LEAF = (58, 122, 66)
LEAF_DARK = (36, 84, 50)
COCONUT = (72, 48, 32)
