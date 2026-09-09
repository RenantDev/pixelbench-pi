# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/RenantDev/pixelbench-pi/releases/tag/v0.1.0
