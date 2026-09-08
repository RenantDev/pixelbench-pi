"""Load presets and the constants that set the rhythm of the scene."""

import numpy as np

TITLE = "pixelbench - pixel art FPS benchmark"

# The internal resolutions are exact divisors of 1920x1080, so a fullscreen
# integer upscale (x8/x4/x3/x2) fills the monitor with no letterboxing and no
# resampling blur. That is the whole reason these particular numbers were
# chosen instead of round ones.
PRESETS = {
    "light":   {"w": 240, "h": 135, "sprites": 24},
    "medium":  {"w": 480, "h": 270, "sprites": 90},
    "heavy":   {"w": 640, "h": 360, "sprites": 220},
    "extreme": {"w": 960, "h": 540, "sprites": 500},
}

# Pace of the water. Real swell has a 6-12 s period; an earlier version used
# 2.4 s and looked frantic. The animation is also NOT continuous: pixel art
# water is a tileset of a few frames cycling slowly, so the phase advances in
# steps (WATER_STEPS per second) instead of sliding.
WAVE_OMEGA = 0.90      # rad/s of the main swell (~7 s per wave)
WATER_STEPS = 10.0     # animation steps per second

# Bayer 4x4: ordered dithering on the transitions between palette bands. This
# is what replaces a smooth gradient - pixel art has no half tones, it has a
# checkerboard.
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6],
                    [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float32) / 16.0 - 0.47) * 0.62
