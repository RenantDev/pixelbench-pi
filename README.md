# pixelbench

[![CI](https://github.com/RenantDev/pixelbench-pi/actions/workflows/ci.yml/badge.svg)](https://github.com/RenantDev/pixelbench-pi/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/RenantDev/pixelbench-pi/blob/main/LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://github.com/RenantDev/pixelbench-pi/blob/main/pyproject.toml)

**A pixel art FPS benchmark for the Raspberry Pi**, with thermal and throttling
telemetry built into the result.

It renders an animated synthwave sunset — a sea built from real wave physics, an
island with a castaway working through his routine, birds, and a soundtrack
synthesised in numpy — then reports FPS, frame time, 1% low, die temperature and
`vcgencmd get_throttled`, all in one block.

[Português](https://github.com/RenantDev/pixelbench-pi/blob/main/README.pt-BR.md)

<p align="center">
  <img src="https://raw.githubusercontent.com/RenantDev/pixelbench-pi/main/docs/media/demo.gif" alt="The benchmark scene: a synthwave sunset over a sea with an island, waves breaking on its shore, and a castaway signalling for help" width="480">
</p>

```
=== pixelbench - pixel art FPS benchmark =========================
 preset...........: medium  (480x270 internal, 90 sprites)
 output...........: 1920x1080 x4 (fullscreen)
 scaler...........: sdl2 (accelerated) @ x11  vsync OFF
 soundtrack.......: synthesised ambient, volume 0.55
 duration.........: 33.4 s, 3262 frames
------------------------------------------------------------------
 average FPS......:     97.5
 FPS min / max....:     43.5 / 129.7
 1% low (p99 ms)..:     79.4  (12.59 ms)
 mean frametime...:    10.25 ms  (median 10.16 ms)
 stability........: stdev 0.64 ms
------------------------------------------------------------------
 temperature......: 51.2 C -> 53.5 C  (peak 54.0 C)
 throttled........: 0x0 -> 0x0
==================================================================
```

## Why this exists, and why it is Pi-specific

A spinning triangle at 4000 FPS tells you very little about a single-board
computer. This benchmark was written for the Raspberry Pi and makes four choices
because of it.

**It reports whether the board was throttling.** A frame rate taken while the
SoC was capped describes the cooling, not the machine. `vcgencmd get_throttled`
is sampled on its own thread throughout the run and latched, so a one-second
throttle event still shows up in the final block. Without that line, a benchmark
number from a Pi is not a result.

**Its resolutions are exact divisors of 1920x1080.** 240x135, 480x270, 640x360
and 960x540 upscale by exactly x8, x4, x3 and x2 to a 1080p panel. The
scaling is integer and nearest-neighbour, so nothing is resampled, nothing is
letterboxed, and the load you measure is the load you asked for.

**It separates the upscale from the scene.** On a Pi 5, scaling to 1080p *on the
CPU* costs about 10 ms per frame and becomes the bottleneck — every preset sits
pinned at ~45 FPS regardless of its real cost. Handing the upscale to the SDL
renderer roughly doubles the frame rate and lets it track the scene again.
`--cpu` runs the software path on purpose, so you can measure the difference on
your own board.

**The load is a real scene.** Sea, parallax layers, sprite blits, palette
lookups and numpy array work — the mix a small 2D game actually produces, not a
synthetic loop. And it is deterministic (fixed seed, quantised water phase), so
two runs measure the same picture.

Everything Pi-specific degrades gracefully: on hardware without `vcgencmd` the
telemetry reads `n/a` and the benchmark still runs.

> The clip above is rendered straight from the renderer by
> [`tools/record_demo.py`](https://github.com/RenantDev/pixelbench-pi/blob/main/tools/record_demo.py) — not a screen capture. The scene is
> deterministic, so the same command reproduces the same file byte for byte.

## Install

One line, no clone and no git:

```bash
pip install https://github.com/RenantDev/pixelbench-pi/releases/latest/download/pixelbench-pi.tar.gz
```

That URL always resolves to the newest release, so it stays valid across
versions. Needs Python 3.9+, SDL2, and a `pygame` that has `pygame._sdl2` (any
wheel from PyPI has it).

### On Raspberry Pi OS and Debian

Recent releases refuse to let pip write into the system Python (PEP 668), so the
line above needs a virtual environment. Use `--system-site-packages` and it
reuses the apt builds of `pygame` and `numpy`, which turns the install into a
few seconds instead of a few minutes:

```bash
sudo apt install -y python3-pygame python3-numpy
python3 -m venv --system-site-packages ~/.venvs/pixelbench
~/.venvs/pixelbench/bin/pip install https://github.com/RenantDev/pixelbench-pi/releases/latest/download/pixelbench-pi.tar.gz
~/.venvs/pixelbench/bin/pixelbench
```

Add `alias pixelbench=~/.venvs/pixelbench/bin/pixelbench` to your `~/.bashrc` to
get the bare command back.

### Other ways

```bash
pip install git+https://github.com/RenantDev/pixelbench-pi   # track main, needs git
git clone https://github.com/RenantDev/pixelbench-pi && cd pixelbench-pi && pip install -e .
```

Release assets are listed with their SHA-256 sums in `SHA256SUMS.txt` on the
[releases page](https://github.com/RenantDev/pixelbench-pi/releases).

## Use

```bash
pixelbench                     # medium preset, fullscreen, runs until ESC
pixelbench -c heavy            # heavier preset
pixelbench -c extreme -t 60    # stress test, stops on its own after 60 s
pixelbench --cpu               # software scaling, to compare against the GPU path
pixelbench --headless          # no window: CPU render cost only
pixelbench --json result.json  # also write a machine-readable summary
```

| Flag | Default | What it does |
|---|---|---|
| `-c, --load` | `medium` | preset: `light`, `medium`, `heavy`, `extreme` |
| `-t, --time` | `0` | duration in seconds (`0` = run until ESC) |
| `-n, --sprites` | preset | number of birds, overriding the preset |
| `-r, --resolution` | preset | internal resolution, e.g. `640x360` |
| `-w, --windowed` | off | run in a window instead of fullscreen |
| `-j, --window` | `1280x720` | window size when using `-w` |
| `--cpu` | off | scale in software instead of the SDL renderer |
| `--vsync` | off | pin the frame rate to the monitor refresh |
| `--headless` | off | no window; measures CPU render cost only |
| `--no-sound` | off | run silently |
| `--volume` | `0.55` | soundtrack volume |
| `--no-hud` | off | start with the on-screen HUD hidden |
| `--json FILE` | — | write the summary as JSON |

Keys while running: `ESC`/`Q` quit, `SPACE` pause, `F` window/fullscreen,
`M` mute the soundtrack, `H` hide the HUD, `+`/`-` change the sprite count.

| Preset | Internal | Upscale to 1080p | Sprites |
|---|---|---|---|
| `light` | 240x135 | x8 | 24 |
| `medium` | 480x270 | x4 | 90 |
| `heavy` | 640x360 | x3 | 220 |
| `extreme` | 960x540 | x2 | 500 |

## Reference results

Raspberry Pi 5 (8 GB), Debian 13, X11, fullscreen 1920x1080, vsync off, no
overclock, active cooling. `throttled=0x0` throughout.

| Run | Average FPS |
|---|---|
| `light` | ~108 |
| `medium` | ~92 |
| `heavy` | ~78 |
| `extreme` | ~35 |
| `medium --cpu` | ~48 |
| `medium --vsync` | 60.0 (monitor limit — expected, not a failure) |

The soundtrack does not cost frames: 99.9 FPS with sound against 99.6 without,
on the same preset. If you see a drop, do not blame the audio.

## Reading the result

**The average FPS is the least useful number in the block.** Look at these
instead:

- **1% low** — the frame rate of the worst 1% of frames. An average of 90 FPS
  made of a steady 95 with occasional 20 ms stalls feels far worse than a flat
  85, and only this line shows the difference.
- **Median frame time vs. mean** — if the median is well below the mean, a few
  slow frames are inflating the average. In a clean run the two are within a
  few hundredths of a millisecond.
- **`throttled`** — anything other than `0x0` invalidates the run. Check cooling
  and power supply before trusting the number.
- **Temperature** — a rise of a few degrees over a run is normal; approaching
  80 °C means the fan curve is about to become the thing you are measuring.

Over a long session the average drifts down: every window focus change or
notification produces a slow frame that lands in the sample. Compare 1% low and
median frame time before concluding anything got worse.

## How it works

The interesting parts are documented on their own:

- [Wave physics](https://github.com/RenantDev/pixelbench-pi/blob/main/docs/wave-physics.md) — deep-water dispersion, the trochoidal
  profile, refraction and shoaling over the island's bank, the breaker index,
  and one approach that did not work.
- [Pixel art rules](https://github.com/RenantDev/pixelbench-pi/blob/main/docs/pixel-art-rules.md) — why the water is flat colour with
  stepped highlights, where dithering helps and where it produces a dotted line.
- [Audio synthesis](https://github.com/RenantDev/pixelbench-pi/blob/main/docs/audio-synthesis.md) — the soundtrack, and the
  infrasound bug that taught the lesson in it.
- [Benchmark methodology](https://github.com/RenantDev/pixelbench-pi/blob/main/docs/benchmarking.md) — what is measured, what is
  discarded, and how to reproduce a comparable run.

## Contributing

See [CONTRIBUTING.md](https://github.com/RenantDev/pixelbench-pi/blob/main/CONTRIBUTING.md). The scene is pinned by golden hashes:
if you change how it looks, the tests will tell you, and updating those hashes
is a deliberate act, never a way to make a test pass.

## License

MIT — see [LICENSE](https://github.com/RenantDev/pixelbench-pi/blob/main/LICENSE).
