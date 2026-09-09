# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-09-09

### Added

- Built wheel and sdist attached to the release, so installing needs neither
  git nor a clone: one `pip install` from a URL.
- `tools/record_demo.py`, which renders the README clip straight from the
  renderer. The scene is deterministic, so it reproduces the published file
  byte for byte.

### Changed

- The distribution is now named `pixelbench-pi`. The bare name `pixelbench`
  belongs to an unrelated CPU-vs-GPU benchmark on PyPI. The import package and
  the `pixelbench` command are unchanged.
- `Sensors` exposes its readers publicly as `read_temp()`, `read_freq()` and
  `read_throttled()`; the CLI was already calling the private form.
- `make_sprites()` no longer takes an `rng` argument, which it never used.

### Fixed

- `docs/pixel-art-rules.md` described the sharper-crest rule as a slope
  multiplier that does not exist in the code. It is applied through the
  trochoidal profile.
- The soundtrack is compared numerically rather than by hash: `np.fft` does not
  round identically across architectures, so the bit-exact test passed on
  aarch64 and failed on x86_64.
- A comment claiming a 3x2 px SOS stone sat two lines above `STONE_W, STONE_H =
  2, 2`; 3 is the stride.

## [0.1.0] - 2026-09-09

First public release.

### Added

- Pixel art FPS benchmark with four load presets (`light`, `medium`, `heavy`,
  `extreme`), whose internal resolutions are exact divisors of 1920x1080 so the
  fullscreen upscale is integer and unresampled.
- Raspberry Pi telemetry sampled on its own thread: die temperature, CPU clock
  and `vcgencmd get_throttled`, with throttling latched into the final report.
  Degrades to neutral values on other hardware.
- Two upscale paths behind one interface — the SDL renderer and a software
  fallback (`--cpu`) — so the cost of scaling can be measured separately from
  the cost of the scene.
- Sea rendering from wave mechanics: deep-water dispersion, a trochoidal
  profile, refraction and shoaling over the island's bank, and a breaker index
  driving the surf. Documented in `docs/wave-physics.md`.
- Ambient soundtrack synthesised in numpy, with no audio assets.
- `--json` export of the summary, carrying measurements only.
- Golden-hash tests pinning every rendered frame and the soundtrack bit for bit.

[0.1.1]: https://github.com/RenantDev/pixelbench-pi/releases/tag/v0.1.1
[0.1.0]: https://github.com/RenantDev/pixelbench-pi/releases/tag/v0.1.0
