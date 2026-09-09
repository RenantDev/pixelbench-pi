#!/usr/bin/env python3
"""Render the README demo GIF straight from the renderer.

This is not a screen capture: it drives the Scene directly with the dummy SDL
driver, so there is no desktop, no window chrome and nothing from the machine it
runs on in the image. The scene is deterministic, so anyone can regenerate a
byte-identical set of frames.

    python tools/record_demo.py            # writes docs/media/demo.gif
    python tools/record_demo.py --help

Needs ffmpeg on PATH and Pillow installed.

On the 21-second default: the four wave trains have incommensurable
frequencies, so the sea never repeats exactly. 21 s is the length under two
minutes that brings all four closest to their starting phase at once, which is
the least visible loop seam available. The cloud and hill parallax layers only
repeat after ~40 minutes, so they always jump - that part is not fixable from
here.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from pixelbench.config import PRESETS  # noqa: E402
from pixelbench.scene import Scene  # noqa: E402
from pixelbench.sprites import Flock, make_sprites  # noqa: E402

SEED = 20260831


def render_frames(preset, start, duration, fps, outdir):
    from PIL import Image

    pygame.init()
    cfg = PRESETS[preset]
    w, h = cfg["w"], cfg["h"]
    rng = np.random.default_rng(SEED)
    scene = Scene(w, h, rng)
    birds = make_sprites()
    flock = Flock(cfg["sprites"], w, h, rng)
    buf = pygame.Surface((w, h))

    dt = 1.0 / fps
    # Step the flock up to the start instant so the birds are already spread out.
    for i in range(int(start / dt)):
        flock.blits(i * dt, dt, birds)

    n = int(round(duration * fps))
    for i in range(n):
        t = start + i * dt
        scene.draw(t, buf)
        b = flock.blits(t, dt, birds)
        if b:
            buf.blits(b, doreturn=False)
        arr = pygame.surfarray.array3d(buf).transpose(1, 0, 2).astype(np.uint8)
        Image.fromarray(arr).save(os.path.join(outdir, f"f{i:05d}.png"))
    pygame.quit()
    return n, w, h


def encode(framedir, fps, out):
    pattern = os.path.join(framedir, "f%05d.png")
    palette = os.path.join(framedir, "palette.png")
    # One palette for the whole clip, and no dithering: the scene already draws
    # its own ordered dither, and letting the encoder add more turns the flat
    # colour bands into noise.
    subprocess.run(
        ["ffmpeg", "-v", "error", "-framerate", str(fps), "-i", pattern,
         "-vf", "palettegen=max_colors=256:stats_mode=full", "-y", palette],
        check=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-framerate", str(fps), "-i", pattern,
         "-i", palette, "-lavfi",
         "paletteuse=dither=none:diff_mode=rectangle", "-loop", "0", "-y", out],
        check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-c", "--load", choices=list(PRESETS), default="medium")
    p.add_argument("--start", type=float, default=0.0,
                   help="first instant of the scene to record, in seconds")
    p.add_argument("--duration", type=float, default=21.0)
    p.add_argument("--fps", type=float, default=20.0)
    p.add_argument("-o", "--output", default="docs/media/demo.gif")
    args = p.parse_args()

    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found on PATH")

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        n, w, h = render_frames(args.load, args.start, args.duration, args.fps, tmp)
        encode(tmp, args.fps, args.output)
    size = os.path.getsize(args.output) / 1024
    print(f"{args.output}: {n} frames, {w}x{h}, {args.fps:g} fps, {size:.0f} KiB")


if __name__ == "__main__":
    main()
