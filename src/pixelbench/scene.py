"""The scene: sky, sun, clouds, hills, and the sea.

The sea is the expensive and the interesting part. Read `docs/wave-physics.md`
and `docs/pixel-art-rules.md` before changing it; the short version is:

* The water is NOT a plasma of sines in screen coordinates - that produced a
  flat interference pattern. Each row below the horizon has its own wavelength
  (wide near the camera, narrow far away) and the phase is the running sum of
  those wavelengths down the rows, so crests come out parallel to the horizon
  and bunch up with distance on their own.
* Brightness comes from the SLOPE of the wave (its derivative - the face that
  catches the light), never from its height.
* Everything that does not depend on time is pre-computed in __init__. The
  per-frame cost is four cosines and a palette lookup.

A path that did NOT work: true perspective (z proportional to 1/y). It is
physically correct, but it throws all the variation onto the horizon and leaves
the water near the camera practically flat. If you rework the sea, do not go
back down that road.
"""

import numpy as np
import pygame

from .config import BAYER4, WATER_STEPS, WAVE_OMEGA
from .island import Island
from .palette import (
    CLOUD_COLOR,
    CLOUD_SHADOW_COLOR,
    FAR_HILL_COLOR,
    FOAM_COLOR,
    NEAR_HILL_COLOR,
    SEA_PALETTE,
    SKY_PALETTE,
    SUN_COLOR,
    SUN_EDGE_COLOR,
)
from .waves import shore_offset, swash


class Scene:
    """Builds the frame in numpy at the internal resolution (real pixel art)."""

    # (frequency, lateral tilt, amplitude) per wave train. The frequencies are
    # incommensurable on purpose: the crests never repeat the same drawing,
    # which is what removes the look of a pattern.
    # The SPEED is not a free choice: in deep water omega = sqrt(g*k), that is,
    # a longer wave travels faster. Hence speed = sqrt(frequency) - and that is
    # what makes the superposition of the trains look like sea instead of
    # summed noise.
    WAVE_TRAINS = (
        (1.00, 0.05, 1.00),   # long swell
        (1.73, -0.09, 0.58),  # second train, slight angle
        (2.91, 0.17, 0.32),   # short chop
        (5.31, -0.28, 0.17),  # fine ripple (also does the glitter)
    )
    STEEPNESS = 0.34          # Q of the trochoidal profile (sharp crest, flat trough)

    def __init__(self, w, h, rng):
        self.w, self.h = w, h
        self.rng = rng
        self.horizon = int(h * 0.62)
        hs = self.horizon            # sky height
        hm = h - hs                  # sea height

        # Sky: gradient quantised onto the palette (visible banding, retro style).
        t = np.linspace(0.0, 1.0, hs) ** 1.35
        idx = np.clip((t * (len(SKY_PALETTE) - 1)).astype(np.int32), 0, len(SKY_PALETTE) - 1)
        self.sky = np.broadcast_to(SKY_PALETTE[idx][None, :, :], (w, hs, 3)).copy()

        # Sun: disc with a rim, just above the horizon.
        cx, cy, r = int(w * 0.62), int(hs * 0.63), max(6, int(h * 0.10))
        gx = np.arange(w)[:, None] - cx
        gy = np.arange(hs)[None, :] - cy
        d2 = gx * gx + gy * gy
        disc = d2 <= r * r
        # Horizontal slots cut out of the sun (the synthwave trademark).
        slots = ((np.arange(hs)[None, :] // max(2, r // 6)) % 3 == 2) & (gy > -r // 3)
        self.sky[disc & ~slots] = SUN_COLOR
        self.sky[(d2 <= r * r) & (d2 > (r - 2) * (r - 2))] = SUN_EDGE_COLOR
        self.sun_x, self.sun_r = cx, r

        # Stars in the upper sky.
        n = max(20, (w * hs) // 900)
        sx = rng.integers(0, w, n)
        sy = (rng.random(n) ** 2.2 * (hs * 0.7)).astype(np.int32)
        keep = ~disc[sx, sy]
        self.stars = (sx[keep], sy[keep])
        self.star_phase = rng.random(keep.sum()) * 6.283

        # Clouds: a wide mask (2w) that scrolls in a loop.
        self.clouds = self._clouds(w * 2, hs)

        # Hills: two silhouette layers, each 2w wide.
        self.far_hills = self._ridge(w * 2, hs, peaks=5, amplitude=0.30, base=0.97, seed=1)
        self.near_hills = self._ridge(w * 2, hs, peaks=9, amplitude=0.16, base=1.06, seed=2)

        # ----- Sea -----
        # Each row of water has its own wavelength: wide near the camera,
        # narrow near the horizon. The phase is the running sum of those
        # wavelengths row by row - that is what keeps the crests parallel to
        # the horizon and makes them bunch up with distance, which is how the
        # sea actually looks. Everything time-independent is pre-computed here.
        self.sea_h = hm
        yy = (np.arange(hm, dtype=np.float32) + 1.0)[None, :]
        depth = yy / hm                                      # 0 = horizon
        lam = np.float32(1.7) + np.float32(hm * 0.44) * depth ** 1.8   # px/cycle
        krow = (2.0 * np.pi / lam).astype(np.float32)        # (1, hm)
        phase = np.cumsum(krow, axis=1).astype(np.float32)   # (1, hm)
        xc = (np.arange(w, dtype=np.float32) - w * 0.5)[:, None]

        # Near the horizon the wave gets smaller than a pixel: without damping
        # it turns into moire. The same ramp doubles as distance haze.
        near = np.clip(depth / 0.22, 0.0, 1.0).astype(np.float32)
        self.gain = near ** 1.4
        self.near = (depth > 0.42)                           # where foam fits

        # Sun glitter column on the water: where the reflections sparkle.
        glint = (np.exp(-((np.arange(w, dtype=np.float32)[:, None] - cx) ** 2)
                        / (2.0 * (r * 1.45) ** 2)) * self.gain).astype(np.float32)

        # Base colour by depth. The water is flat in FEW tones, with dithering
        # only on the transitions between bands; the highlights come later as
        # discrete streaks. Mapping a continuous brightness onto 13 tones turns
        # into noise - pixel art water is a smooth band with light streaks over it.
        self.dither = np.tile(BAYER4, (w // 4 + 1, hm // 4 + 1))[:w, :hm].copy()
        nm = len(SEA_PALETTE)
        floor = np.float32(10.6) - np.float32(5.9) * near ** np.float32(0.85)
        # No dithering on the far rows: up there the band changes fast and the
        # checkerboard turns into a dotted line on the horizon.
        self.base_idx = np.clip(floor + self.dither * near, 0, nm - 1).astype(np.int16)
        # Threshold for the light streaks; it drops in the sun's column, where
        # the water sparkles.
        self.lim1 = (np.float32(0.22) - glint * np.float32(0.34)).astype(np.float32)
        self.lim2 = (np.float32(0.72) - glint * np.float32(0.62)).astype(np.float32)

        self.frame = np.empty((w, h, 3), dtype=np.uint8)
        self.island = Island(w, h, self.horizon, hm)

        # Surf: distance in PIXELS to the island's water line. The (d-1)/|grad d|
        # term corrects the ellipse's anisotropy - without it the foam band comes
        # out thin at the front and enormously wide at the sides.
        il = self.island
        X = (np.arange(w, dtype=np.float32) - (il.x0 + il.cx))[:, None]
        Y = (np.arange(hm, dtype=np.float32) + hs - il.base)[None, :]
        a2, b2 = np.float32(il.rx ** 2), np.float32(max(1.0, il.ry_f) ** 2)
        d = np.sqrt(X * X / a2 + Y * Y / b2)
        grad = np.sqrt((X / a2) ** 2 + (Y / b2) ** 2) / np.maximum(d, 1e-6)
        dist = (d - 1.0) / np.maximum(grad, 1e-6)          # px outside the island
        # The foam is NOT a blob with random holes: it is a continuous sheet
        # hugging the shore whose WIDTH varies from point to point and over
        # time. It is the varying width that reads as water covering more
        # sandbar here and less there - punching holes in a blob only produces
        # texture, not a wave.
        self.surf_reach = np.float32(max(3.0, hm * 0.085))   # reach at the peak
        band = (dist > -2.0) & (dist < float(self.surf_reach) * 2.8)
        nz = np.nonzero(band)
        if len(nz[0]):
            self.surf_x = slice(int(nz[0].min()), int(nz[0].max()) + 1)
            self.surf_y = slice(int(nz[1].min()), int(nz[1].max()) + 1)
        else:                                    # island outside the visible water
            self.surf_x = self.surf_y = slice(0, 0)
        self.dist = np.ascontiguousarray(
            dist[self.surf_x, self.surf_y]).astype(np.float32)

        # ----- How the wave transforms as it reaches the island -----
        # The island is not just an obstacle: it is a BANK. The shallow water
        # around it changes the wave before it arrives, and that is what makes
        # the interaction look real instead of foam glued to an edge.
        #
        #   c = sqrt(g*h)  -> in shallow water the wave slows down; the part of
        #   the crest in the shallows falls behind and the crest BENDS, following
        #   the contours of the bottom (refraction, Snell's law: sin(f)/c = const).
        #   k = w/c grows -> the wavelength shortens along with it.
        #   H ~ h^(-1/4) (Green's law) -> the wave also GROWS as it shoals.
        d0 = max(8.0, il.rx * 0.95)                     # reach of the bank
        bank_depth = np.clip(dist / d0, 0.12, 1.0).astype(np.float32)
        # Extra phase accumulated along the wave's path (it travels from the
        # back of the scene toward the camera, so the integral runs over y).
        ref = np.cumsum((1.0 / np.sqrt(bank_depth) - 1.0) * krow, axis=1)
        # The bank is shallow and wide: integrated whole, the lag passes 90 rad
        # and scrambles the wave field. Normalising to a maximum lag of ~4.5 rad
        # (less than one wavelength) keeps the same refraction drawing over a
        # far calmer bottom.
        self.refraction = (ref * (4.5 / max(1e-6, float(ref.max())))).astype(np.float32)
        # Shoaling: grows on entering the shallows, capped because in practice
        # the wave breaks before growing without bound.
        self.shoaling = np.clip(bank_depth ** np.float32(-0.25),
                                1.0, 1.75).astype(np.float32)
        self.gain2d = (self.gain * self.shoaling).astype(np.float32)
        # Final phase of each train, refraction already folded in.
        # speed = sqrt(fi) is the deep-water dispersion relation.
        self.trains = [((phase * fi + xc * (krow * dxi)
                         + self.refraction * fi).astype(np.float32),
                        np.float32(amp), np.float32(np.sqrt(fi)))
                       for fi, dxi, amp in self.WAVE_TRAINS]
        # Wave phase at the height of the beach: syncs the water to the sand.
        self.island_phase = float(phase[0, min(hm - 1, max(0, int(il.base - hs)))])
        # Every stretch of shore has its own lag and its own break size (an
        # irregular sandbar), plus a per-column jitter that frays the edge.
        Xr = np.arange(w, dtype=np.float32)[self.surf_x][:, None]
        jit = np.random.default_rng(9).uniform(0.82, 1.18, (Xr.shape[0], 1))
        lat = (0.76 + 0.30 * np.sin(Xr * 0.13 + 0.7)
               * np.sin(Xr * 0.052 + 2.4)) * jit
        # Smooth between neighbouring columns: without this the sheet gets
        # jagged and even sheds bubbles detached from the island.
        kernel = np.ones(3) / 3.0
        lat = np.convolve(lat[:, 0], kernel, mode="same")[:, None]
        self.lat = lat.astype(np.float32)
        self.col_phase = (self.island_phase + shore_offset(Xr)).astype(np.float32)

    def _clouds(self, width, height, seed=7):
        rng = np.random.default_rng(seed)
        m = np.zeros((width, height), dtype=bool)
        for _ in range(max(6, width // 90)):
            cx = rng.integers(0, width)
            cy = rng.integers(int(height * 0.12), int(height * 0.55))
            for _ in range(rng.integers(3, 7)):
                ox = cx + rng.integers(-18, 19)
                oy = cy + rng.integers(-3, 4)
                rx = int(rng.integers(6, 20))
                ry = max(1, rx // 3)
                x0, x1 = max(0, ox - rx), min(width, ox + rx)
                y0, y1 = max(0, oy - ry), min(height, oy + ry)
                if x1 <= x0 or y1 <= y0:
                    continue
                gx = (np.arange(x0, x1)[:, None] - ox) / rx
                gy = (np.arange(y0, y1)[None, :] - oy) / ry
                m[x0:x1, y0:y1] |= (gx * gx + gy * gy) <= 1.0
        return m

    def _ridge(self, width, height, peaks, amplitude, base, seed):
        """Mountain profile as a sum of sines; returns a (width, height) mask."""
        rng = np.random.default_rng(seed)
        x = np.linspace(0, 2 * np.pi, width, endpoint=False)
        profile = np.zeros(width)
        for k in range(1, peaks + 1):
            profile += (rng.random() * 0.9 + 0.2) * np.sin(k * x + rng.random() * 6.283) / k
        profile = profile / (np.abs(profile).max() + 1e-6)
        top = (height * base - profile * height * amplitude).astype(np.int32)
        top = np.clip(top, 0, height)
        # A 2 px "staircase": a silhouette that looks like pixel art, not vector.
        top = (top // 2) * 2
        ys = np.arange(height)[None, :]
        return ys >= top[:, None]

    def draw(self, t, buf_surface):
        w, hs = self.w, self.horizon
        q = self.frame
        sky = q[:, :hs]
        sky[:] = self.sky

        # Twinkling stars.
        twinkle = (np.sin(t * 2.6 + self.star_phase) * 0.5 + 0.5)
        v = (140 + twinkle * 115).astype(np.uint8)
        sky[self.stars[0], self.stars[1]] = v[:, None]

        # Scrolling clouds (two speeds = parallax).
        for speed, color in ((3.2, CLOUD_SHADOW_COLOR), (5.0, CLOUD_COLOR)):
            off = int(t * speed) % w
            sky[self.clouds[off:off + w]] = color

        # Hills (the far layer moves more slowly).
        off = int(t * 1.8) % w
        sky[self.far_hills[off:off + w]] = FAR_HILL_COLOR
        off = int(t * 4.0) % w
        sky[self.near_hills[off:off + w]] = NEAR_HILL_COLOR

        # Sea: the brightness comes from the SLOPE of the wave (its derivative),
        # not from its height. It is the tilted face that catches the light from
        # the sky; using the height leaves the water looking like a rippled rug.
        # Pixel-art cadence: the water phase advances in steps, like an animated
        # tileset. Continuous motion gives away that it is maths, not art.
        ta = np.float32(np.floor(t * WATER_STEPS) / WATER_STEPS)

        slope = None
        ripple = None
        raw = None
        Q = np.float32(self.STEEPNESS)
        for base, amp, speed in self.trains:
            raw = np.cos(base - speed * np.float32(WAVE_OMEGA) * ta)
            # Trochoidal (Gerstner) profile: cos(f + Q*sin f) ~ c + Q*(c^2 - 1),
            # the real shape of a gravity wave (sharp crest, wide flat trough),
            # for free - without one extra sine per train. The -0.5 instead of
            # -1 removes the bias: the mean of cos^2 is 0.5, and with -1 the
            # whole sea went dark.
            c = (raw + Q * (raw * raw - np.float32(0.5))) * amp
            slope = c if slope is None else slope + c
            ripple = c        # the finest train is what does the glitter
        slope *= self.gain2d

        # Surf: width of the foam sheet at each column of the shore.
        rx, ry = self.surf_x, self.surf_y
        cr = raw[rx, ry]                  # raw ripple: frays the foam
        u = np.mod(self.col_phase - np.float32(WAVE_OMEGA) * ta,
                   np.float32(2 * np.pi)) * np.float32(1.0 / (2 * np.pi))
        # Breaker index: a wave breaks when H > 0.78*h. With shoaling H ~ h^(-1/4),
        # that gives a break depth ~ H0^0.8 - a bigger crest breaks further from
        # the beach, which is what you see at sea.
        width = self.surf_reach * swash(u) ** np.float32(0.8) * self.lat
        d = self.dist
        # The wave is not a white block: it is a CREST on the outer edge, where
        # it is breaking, with foam crumbling behind it. Filling it all white
        # turns into a bib stuck to the island.
        inside = d > np.float32(-1.5)
        crest = inside & (d < width) & (d > width - np.float32(3.0))
        drag = inside & (d <= width - np.float32(3.0)) & (cr > np.float32(-0.4))
        trough = (d >= width) & (d < width + self.surf_reach * np.float32(0.6))

        # Every light streak is a palette STEP, not an interpolation: the water
        # stays flat and the highlights become little dashes, the way water is
        # drawn in pixel art.
        n = len(SEA_PALETTE)
        idx = (self.base_idx + (slope > self.lim1) + (slope > self.lim2)
               - (slope < np.float32(-0.50)))
        # Dark trough right behind the sheet: the crest/trough contrast is what
        # makes the eye read "breaking wave" and not "light smudge".
        idx[rx, ry] -= trough
        np.clip(idx, 0, n - 1, out=idx)
        sea = SEA_PALETTE[idx]
        # Whitecaps: only on the crest of steep waves and only in near water.
        sea[(slope > 1.48) & self.near & (ripple > 0.03)] = FOAM_COLOR
        sub = sea[rx, ry]
        sub[drag] = SEA_PALETTE[-1]       # old foam, breaking apart
        sub[crest] = FOAM_COLOR           # the crest breaking right now
        q[:, hs:] = sea

        pygame.surfarray.blit_array(buf_surface, q)
        # Same water phase -> the lick on the sand lands with the foam.
        self.island.draw(buf_surface, t,
                         float(WAVE_OMEGA * ta) - self.island_phase)
