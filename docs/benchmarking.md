# Benchmark methodology

## What is measured

The wall-clock delta between consecutive frames, in milliseconds, collected in a
list and reduced at the end. The **first 30 frames are discarded**: they include
texture upload, font loading and the first passes through cold caches, and they
would otherwise drag the average down for reasons that have nothing to do with
the hardware.

`clock.tick()` is called without an argument — there is no frame cap unless you
pass `--vsync`.

## What is reported

| Line | Meaning |
|---|---|
| average FPS | `1000 / mean(frame_ms)`. The least useful number in the block. |
| FPS min / max | derived from the slowest and fastest single frame |
| 1% low (p99 ms) | frame rate of the worst 1% of frames — how the run actually felt |
| mean / median frametime | a gap between them means a few slow frames are inflating the mean |
| stability | standard deviation of the frame time |
| temperature | start → end, and the peak seen during the run |
| throttled | `vcgencmd get_throttled` at start and end, plus a latch for any event in between |

## Telemetry

Sampled on a separate thread at 1 Hz. Reading sysfs and spawning `vcgencmd` from
inside the render loop would show up as frame-time spikes and poison the very
measurement they exist to qualify.

Sources: `/sys/class/thermal/thermal_zone0/temp`,
`/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq`, and
`vcgencmd get_throttled`. Each degrades to a neutral value where it is not
available, so the benchmark runs on non-Pi hardware and simply reports less.

**Throttling is latched.** A one-second event during a five-minute run still
shows in the final block. Any value other than `0x0` invalidates the result:
what you measured was the cooling.

## Reproducing a comparable run

- Fullscreen, vsync off, no other windows on top. Every focus change and
  notification produces a slow frame that lands in the sample.
- At least 30 seconds. Shorter runs are dominated by the warm-up and by whatever
  the desktop happened to be doing.
- State the environment: board model, OS, display server (X11 or Wayland),
  resolution, cooling, and whether the board is overclocked.
- Prefer `--json` for anything you intend to compare later. It writes
  measurements only — no hostname, no user, no paths — so it is safe to paste
  into an issue.

## The determinism guarantee

The scene is seeded with a fixed value and the water phase is quantised, so two
runs of the same preset render the same pictures. Frame content is therefore
never a variable between runs; only the machine is. `tests/test_golden.py`
enforces this with SHA-256 hashes of rendered frames.

## Known comparison points

On a Raspberry Pi 5, the software upscale path (`--cpu`) costs about 10 ms per
frame at 1080p and pins every preset near 45 FPS. If your accelerated numbers
look close to your `--cpu` numbers, the SDL renderer probably fell back to
software — the `scaler` line in the report says which path actually ran.
