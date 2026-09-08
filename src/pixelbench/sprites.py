"""ASCII sprite art and the flock of birds.

The birds are the adjustable part of the load: `-n/--sprites` and the +/- keys
change how many are on screen, which scales blit count without touching the
cost of the scene behind them.
"""

import numpy as np
import pygame

# 7x5 bird sprite, 3 wing-beat frames. '.' = transparent.
BIRD = [
    [
        "..#....",
        ".###..#",
        "#..####",
        ".......",
        ".......",
    ],
    [
        ".......",
        "..#...#",
        ".#######",
        ".......",
        ".......",
    ],
    [
        ".......",
        ".......",
        "#..####",
        ".###..#",
        "..#....",
    ],
]

# Five tints, from near-black to washed-out: the birds further away are lighter,
# which is the cheapest depth cue there is.
BIRD_TINTS = [(24, 18, 38), (72, 40, 62), (124, 58, 68), (176, 88, 78), (214, 130, 92)]


def art(lines, colors, scale=1):
    """Turn ASCII art into a Surface. '.' stays transparent."""
    width = max(len(line) for line in lines)
    s = pygame.Surface((width, len(lines)), pygame.SRCALPHA)
    for y, line in enumerate(lines):
        for x, ch in enumerate(line):
            if ch != ".":
                s.set_at((x, y), colors[ch])
    if scale > 1:
        s = pygame.transform.scale(s, (width * scale, len(lines) * scale))
    return s


def make_sprites(rng):
    """Turn the bird ASCII art into coloured Surfaces, one set per tint."""
    flocks = []
    for color in BIRD_TINTS:
        frames = []
        for glyph in BIRD:
            width = max(len(line) for line in glyph)
            s = pygame.Surface((width, len(glyph)), pygame.SRCALPHA)
            for y, line in enumerate(glyph):
                for x, c in enumerate(line):
                    if c == "#":
                        s.set_at((x, y), color)
            # convert_alpha() only works with a video surface (the CPU path).
            frames.append(s.convert_alpha() if pygame.display.get_surface() else s)
        flocks.append(frames)
    return flocks


class Flock:
    """Birds on sinusoidal routes; vectorised to survive hundreds of sprites.

    Every bird's position is one numpy expression over the whole flock, so
    going from 24 to 500 sprites costs blits, not Python.
    """

    def __init__(self, n, w, h, rng):
        self.w, self.h = w, h
        self.rng = rng
        self.n = 0
        self.x = np.zeros(0)
        self.y0 = np.zeros(0)
        self.speed = np.zeros(0)
        self.amp = np.zeros(0)
        self.phase = np.zeros(0)
        self.kind = np.zeros(0, dtype=np.int32)
        self.beat = np.zeros(0)
        self.resize(n)

    def resize(self, n):
        n = max(0, n)
        if n == self.n:
            return
        if n < self.n:
            cut = slice(0, n)
            for a in ("x", "y0", "speed", "amp", "phase", "kind", "beat"):
                setattr(self, a, getattr(self, a)[cut])
        else:
            k = n - self.n
            r = self.rng
            self.x = np.concatenate([self.x, r.random(k) * self.w])
            self.y0 = np.concatenate([self.y0, r.random(k) * (self.h * 0.55) + self.h * 0.05])
            self.speed = np.concatenate([self.speed, r.random(k) * 34 + 12])
            self.amp = np.concatenate([self.amp, r.random(k) * 7 + 2])
            self.phase = np.concatenate([self.phase, r.random(k) * 6.283])
            self.kind = np.concatenate([self.kind, r.integers(0, 5, k)])
            self.beat = np.concatenate([self.beat, r.random(k) * 6 + 7])
        self.n = n

    def blits(self, t, dt, flocks):
        if self.n == 0:
            return ()
        self.x = (self.x + self.speed * dt) % (self.w + 8)
        y = self.y0 + np.sin(t * 1.7 + self.phase) * self.amp
        frame = (t * self.beat).astype(np.int32) % 3
        xs = self.x.astype(np.int32) - 8
        ys = y.astype(np.int32)
        return [(flocks[self.kind[i]][frame[i]], (int(xs[i]), int(ys[i])))
                for i in range(self.n)]
