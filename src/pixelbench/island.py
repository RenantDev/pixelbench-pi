"""The island, its beach, and the castaway going about his routine.

Two scale systems meet in this file and mixing them up is the bug that once
made the island twice its size with the characters floating above it:

* island geometry (width, dune radius, water line) is in SCREEN pixels;
* sprites (man, fire, palm) are in DESIGN pixels, multiplied by
  `self.scale = round(height / 180)`.

Anything that positions a sprite against the terrain has to convert.
"""

import numpy as np
import pygame

from .palette import (
    ART_COLORS,
    BEACH_FOAM,
    COCONUT,
    LEAF,
    LEAF_DARK,
    ROCK,
    ROCK_DARK,
    ROCK_LIGHT,
    ROCK_SHADOW,
    SAND,
    SAND_DARK,
    SAND_LIGHT,
    SAND_WET,
    TRUNK,
    TRUNK_LIGHT,
)
from .sprites import art
from .waves import shore_offset, swash

# Castaway: 7 x 10 pixels at design size.
FIGURE = {
    "idle": [
        "..kkk..", ".kpppk.", "..ppp..", "pcccccp", ".ccccc.",
        ".ccccc.", "..bbb..", "..b.b..", "..b.b..", "..k.k..",
    ],
    "walk1": [
        "..kkk..", ".kpppk.", "..ppp..", "pcccccp", ".ccccc.",
        ".ccccc.", "..bbb..", ".bb.bb.", ".b...b.", "k.....k",
    ],
    "walk2": [
        "..kkk..", ".kpppk.", "..ppp..", ".cccccp", "pccccc.",
        ".ccccc.", "..bbb..", "..bbb..", "..b.b..", "..k.k..",
    ],
    "wave1": [                        # both arms up
        "p.kkk.p", "ckpppkc", "c.ppp.c", ".ccccc.", ".ccccc.",
        ".ccccc.", "..bbb..", "..b.b..", "..b.b..", "..k.k..",
    ],
    "wave2": [                        # one arm up, one down
        "p.kkk..", "ckpppk.", "c.ppp..", ".cccccp", ".ccccc.",
        ".ccccc.", "..bbb..", "..b.b..", "..b.b..", "..k.k..",
    ],
    "crouch": [                       # crouched: tending fire, writing in sand
        ".......", ".......", "..kkk..", ".kpppk.", "..ppp..",
        ".cccccp", "pccccc.", "..bbb..", ".bb.bb.", ".k...k.",
    ],
    "fish": [                         # arms forward holding the rod
        "..kkk..", ".kpppk.", "..ppp..", ".ccccpp", ".ccccc.",
        ".ccccc.", "..bbb..", "..b.b..", "..b.b..", "..k.k..",
    ],
}

FIRE = [
    ["...v...", "..vgv..", ".vgfgv.", ".vgffv.", "vggffgv", "vvgggvv", "mmvvvmm"],
    ["..v.v..", "..vgv..", ".vgfv..", ".vgffv.", "vgfffgv", "vvggvvv", "mmvvvmm"],
    ["...v...", "..vgv..", "..vgfv.", ".vggfv.", "vggfggv", "vvgvgvv", "mmvvvmm"],
]


class Island:
    """An island out at sea, with a castaway working through his routine.

    The routine is a pre-computed cyclic timeline: given an instant t you can
    tell where he is and what he is doing, with no state kept between frames.
    That keeps the animation deterministic and makes pause work for free.
    """

    # (activity, position on the island 0..1, duration in seconds)
    ACTIVITIES = (
        ("wave", 0.20, 6.5),      # waves at the horizon asking for help
        ("fire", 0.34, 7.0),      # pokes the signal fire
        ("sos", 0.63, 6.0),       # tidies up the SOS stones
        ("fish", 0.93, 9.0),      # fishes for lunch at the water's edge
    )
    FIRE_X = 0.30
    PALM_X = 0.15

    def __init__(self, w, h, horizon, sea_h):
        self.w, self.h = w, h
        self.scale = max(1, int(round(h / 180.0)))
        self.iw = max(46, int(w * 0.24))
        self.radius_y = max(4, int(sea_h * 0.17))
        # The island's footprint on the water is an ellipse flattened by the
        # perspective: that curve is what the surf foam follows.
        self.ry_f = max(2, int(self.radius_y * 0.45))
        self.rx = self.iw * 0.5
        self.cx = self.iw * 0.5
        self.x0 = (w - self.iw) // 2
        self.base = horizon + int(sea_h * 0.34)      # the island's water line

        e = self.scale
        self.figure = {k: art(v, ART_COLORS, e) for k, v in FIGURE.items()}
        self.fire = [art(f, ART_COLORS, e) for f in FIRE]
        self.hw, self.hh = self.figure["idle"].get_size()

        self.palm_height = 36       # design pixels; scale multiplies later
        self.palm = [self._palm(k) for k in range(3)]
        self.sand = self._sand()
        # Fixed beach roughness: breaks up the foam edge pixel by pixel.
        self.jitter = np.random.default_rng(5).uniform(-0.9, 1.0, self.iw)
        self.swash = [self._swash(i) for i in range(self.N_SWASH)]
        self.script, self.cycle = self._script()

    # ---- geometry ----
    def top(self, xl):
        """Height of the sand (absolute y) at local position xl."""
        d = min(1.0, max(-1.0, (xl - self.cx) / self.rx))
        return self.base - self.radius_y * (1.0 - d * d) ** 0.5

    # ---- pieces ----
    def _profile(self, x):
        """(dune top, water line) in local surface coordinates."""
        dxn = (x - self.cx) / self.rx
        if abs(dxn) > 1.0:
            return None
        k = (1.0 - dxn * dxn) ** 0.5
        return self.radius_y - self.radius_y * k, self.radius_y + self.ry_f * k

    def _sand(self):
        """Sand dune: a dome on top, elliptical front below."""
        height = self.radius_y + self.ry_f + 1
        s = pygame.Surface((self.iw, height), pygame.SRCALPHA)
        rng = np.random.default_rng(11)
        for x in range(self.iw):
            prof = self._profile(x)
            if prof is None:
                continue
            top, front = prof
            for y in range(max(0, int(round(top))), min(height, int(round(front)) + 1)):
                depth = y - top
                if depth < 1:
                    color = SAND_LIGHT
                elif depth < 3:
                    color = SAND
                elif y >= front - 2:
                    color = SAND_WET
                else:
                    color = SAND_DARK
                if depth >= 1 and y < front - 2 and rng.random() < 0.06:
                    color = SAND_DARK if color is SAND else SAND
                s.set_at((x, y), color)
        self._write_sos(s, height)
        return s

    N_SWASH = 40         # pre-built frames of one wave cycle

    def _swash(self, i):
        """The wave licking the sand at instant i/N of the cycle.

        Each column rises according to the phase the wave has at THAT point of
        the shore, so the water advances in tongues and leaves wet sand behind
        as it draws back.
        """
        theta = 2.0 * np.pi * i / self.N_SWASH
        height = self.radius_y + self.ry_f + 1
        s = pygame.Surface((self.iw, height), pygame.SRCALPHA)
        kmax = self.ry_f + 2.5
        for x in range(self.iw):
            prof = self._profile(x)
            if prof is None:
                continue
            top, front = prof
            u = ((theta - shore_offset(self.x0 + x)) / (2.0 * np.pi)) % 1.0
            rise = kmax * float(swash(u)) + self.jitter[x]
            y_foam = max(top + 0.5, front - rise)
            y_wet = max(top + 0.5, front - rise * 1.45)
            for yy in range(int(round(y_wet)), int(round(front)) + 1):
                if 0 <= yy < height:
                    s.set_at((x, yy), SAND_WET)
            if rise > 0.6:                       # foam crest
                for dy in (0, 1):
                    yy = int(round(y_foam)) + dy
                    if 0 <= yy < height and yy <= int(round(front)):
                        s.set_at((x, yy), BEACH_FOAM)
        return s

    # Each cell of a letter becomes a 2x2 px stone on a 3 px stride, so the
    # letters read as text lying on the ground, seen almost edge-on.
    SOS_LETTERS = {
        "S": ("#####", "#....", "#####", "....#", "#####"),
        "O": ("#####", "#...#", "#...#", "#...#", "#####"),
    }
    # A 2x2 stone with a stride of 3 on both axes: the 1 px gap is what keeps
    # one stone apart from the next. The highlight sits on a CORNER, not on a
    # whole line - with a light top row the stacked stones turned into
    # horizontal stripes and the letter disappeared.
    STONE_W, STONE_H = 2, 2
    STRIDE_X, STRIDE_Y = 3, 3

    def _pix(self, s, height, x, y, color):
        """Paint only where there is sand - so stones never float on water."""
        x, y = int(x), int(y)
        if 0 <= x < self.iw and 0 <= y < height and s.get_at((x, y)).a:
            s.set_at((x, y), color)

    def _write_sos(self, s, height):
        """SOS laid out in stones on the sand - the plea nobody reads."""
        rng = np.random.default_rng(23)
        pw, ph = self.STONE_W, self.STONE_H
        sx, sy = self.STRIDE_X, self.STRIDE_Y
        letter_w, gap = 5 * sx - (sx - pw), sx
        width = 3 * letter_w + 2 * gap
        x0 = int(self.cx - width / 2 + self.iw * 0.06)

        for li, ch in enumerate("SOS"):
            glyph = self.SOS_LETTERS[ch]
            bx = x0 + li * (letter_w + gap)
            # Each letter settles at the dune height over its own stretch.
            tops = [self._profile(x)[0] for x in range(bx, bx + letter_w)
                    if 0 <= x < self.iw and self._profile(x)]
            if not tops:
                continue
            y0 = int(max(tops)) + 2
            grid = {(c, r) for r, line in enumerate(glyph)
                    for c, m in enumerate(line) if m == "#"}
            cells = [(c, r, bx + c * sx, y0 + r * sy) for c, r in grid]
            # Shadow only where there is NO stone alongside: otherwise it fills
            # the 1 px gap and glues the stones back into a single bar.
            for c, r, px, py in cells:
                if (c + 1, r) not in grid:
                    self._pix(s, height, px + pw, py + 1, ROCK_SHADOW)
                if (c, r + 1) not in grid:
                    for dx in range(pw):
                        self._pix(s, height, px + dx + 1, py + ph, ROCK_SHADOW)
            for _, _, px, py in cells:
                tone = int(rng.integers(-16, 17))       # no two stones alike
                light = tuple(int(np.clip(v + tone, 0, 255)) for v in ROCK_LIGHT)
                body = tuple(int(np.clip(v + tone, 0, 255)) for v in ROCK)
                dark = tuple(int(np.clip(v + tone, 0, 255)) for v in ROCK_DARK)
                self._pix(s, height, px, py, light)            # lit corner
                self._pix(s, height, px + 1, py, body)
                self._pix(s, height, px, py + 1, body)
                self._pix(s, height, px + 1, py + 1, dark)     # shaded corner

    def _palm(self, frame):
        """Hand-drawn palm: curved trunk and fronds with leaflets."""
        ph = self.palm_height
        pw = int(ph * 0.92) | 1          # odd: gives an exact centre
        p = pygame.Surface((pw, ph), pygame.SRCALPHA)
        mid = pw // 2
        sway = (frame - 1) * 0.08               # fronds swaying in the wind
        trunk_h = int(ph * 0.66)

        def put(x, y, color):
            x, y = int(x), int(y)
            if 0 <= x < pw and 0 <= y < ph:
                p.set_at((x, y), color)

        # Trunk: 2 px, curving slightly and tapering upward.
        top_x = mid
        for i in range(trunk_h):
            f = i / max(1, trunk_h - 1)
            tx = mid - 1 + f * f * 2.5
            y = ph - 1 - i
            put(tx, y, TRUNK)
            put(tx + 1, y, TRUNK_LIGHT if i % 4 else TRUNK)
            top_x = tx + 0.5
        top_y = ph - trunk_h - 1

        # Crown: 9 fronds that RISE, spread, and only droop at the tip. Without
        # the rise they turn into a curtain and the tree looks like a willow.
        length = ph * 0.46
        for ang in (-1.35, -1.0, -0.62, -0.28, 0.0, 0.28, 0.62, 1.0, 1.35):
            a = ang + sway * (1.0 if ang >= 0 else -1.0)
            sa, ca = np.sin(a), np.cos(a)
            rise = length * (0.28 + 0.62 * max(0.0, ca))
            steps = int(length * 1.6)
            for j in range(steps):
                sf = j / max(1.0, steps - 1.0)
                x = top_x + sa * length * 1.25 * sf
                y = top_y - rise * sf + length * 1.02 * sf * sf
                put(x, y, LEAF)
                put(x, y + 1, LEAF_DARK)
                spread = (1.0 - sf * 0.8) * 3.0        # leaflets on both sides
                for side in (-1, 1):
                    for k in range(1, int(spread) + 1):
                        put(x - ca * side * k * 0.55,
                            y + sa * side * k * 0.55 + 1,
                            LEAF if k <= 2 else LEAF_DARK)
        for dx, dy in ((-2, 2), (1, 3), (-1, 4)):       # coconuts
            put(top_x + dx, top_y + dy, COCONUT)

        if self.scale > 1:
            p = pygame.transform.scale(p, (pw * self.scale, ph * self.scale))
        return p

    # ---- the castaway's routine ----
    def _script(self):
        speed = max(4.0, self.iw * 0.16)        # pixels per second
        seg = []
        t = 0.0
        for i, (name, pos, dur) in enumerate(self.ACTIVITIES):
            nxt = self.ACTIVITIES[(i + 1) % len(self.ACTIVITIES)]
            x = pos * self.iw
            seg.append((name, t, t + dur, x, x))
            t += dur
            xd = nxt[1] * self.iw
            dt = abs(xd - x) / speed
            seg.append(("walk", t, t + dt, x, xd))
            t += dt
        return seg, t

    def _where(self, t):
        """(local x, activity, progress 0..1) at instant t."""
        tt = t % self.cycle
        for name, t0, t1, x0, x1 in self.script:
            if tt < t1:
                f = (tt - t0) / max(1e-6, t1 - t0)
                return x0 + (x1 - x0) * f, name, f
        return self.script[-1][3], "idle", 0.0

    def _figure_frame(self, activity, t, f):
        if activity == "walk":
            return self.figure["walk1" if int(t * 6) % 2 else "walk2"]
        if activity == "wave":
            return self.figure["wave1" if int(t * 3.5) % 2 else "wave2"]
        if activity == "fish":
            return self.figure["fish"]
        if activity in ("fire", "sos"):
            # stands up now and then to scan the horizon
            return self.figure["idle" if (f * 4.0) % 1.0 > 0.78 else "crouch"]
        return self.figure["idle"]

    # ---- drawing ----
    def draw(self, buf, t, theta=0.0):
        e = self.scale
        buf.blit(self.sand, (self.x0, int(self.base - self.radius_y)))
        # The wave's lick, on the same beat and the same phase as the water.
        i = int(theta / (2.0 * np.pi) * self.N_SWASH) % self.N_SWASH
        buf.blit(self.swash[i], (self.x0, int(self.base - self.radius_y)))

        # Swaying palm
        palm = self.palm[int(t * 1.6) % 3]
        pw, ph = palm.get_size()
        px = int(self.iw * self.PALM_X)
        buf.blit(palm, (self.x0 + px - pw // 2, int(self.top(px)) - ph + 2))

        # Signal fire + rising smoke
        fg = self.fire[int(t * 9) % 3]
        fw, fh = fg.get_size()
        fx = int(self.iw * self.FIRE_X)
        fy = int(self.top(fx)) - fh + 1
        buf.blit(fg, (self.x0 + fx - fw // 2, fy))
        for i in range(5):
            sy = fy - 2 - i * 2 - int(t * 7) % 3
            sx = self.x0 + fx + int(2.5 * np.sin(t * 1.3 + i * 0.9))
            if 0 <= sx < self.w and 0 <= sy < self.h:
                buf.set_at((sx, sy), (120 - i * 8, 112 - i * 8, 120 - i * 6))

        # The castaway
        xl, activity, f = self._where(t)
        img = self._figure_frame(activity, t, f)
        hx = self.x0 + int(xl) - self.hw // 2
        hy = int(self.top(xl)) - self.hh + 1
        if activity == "fish":
            # Rod pointing off the island, line dropping into the sea and the
            # float bobbing with the wave.
            hand = (hx + self.hw - 1, hy + 3 * e)
            tip = (hand[0] + 8 * e, hand[1] - 7 * e)
            water = int(self.base + 2 * e + 1.5 * np.sin(t * 2.1))
            pygame.draw.line(buf, TRUNK, hand, tip, max(1, e))
            pygame.draw.line(buf, (176, 186, 196), tip, (tip[0] + e, water), 1)
            pygame.draw.rect(buf, (206, 84, 66),
                             (tip[0] + e - e // 2, water - e // 2, max(1, e), max(1, e)))
        buf.blit(img, (hx, hy))
