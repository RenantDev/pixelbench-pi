"""Frame-time statistics and the final report.

The average FPS is the least interesting number here. What tells you whether a
board is actually pleasant to use is the 1% low and the median frame time: an
average of 90 FPS made of a smooth 95 with occasional 20 ms stalls feels far
worse than a flat 85. Both are reported, together with the thermal state that
qualifies them - a result taken while the board was throttling describes the
cooling, not the board.
"""

import json
import math

import numpy as np


def percentile(v, p):
    return float(np.percentile(v, p)) if len(v) else float("nan")


def summarize(frame_ms, *, preset, width, height, sprites, mode, scaler, driver,
              vsync, soundtrack, duration, frames, temp_start, temp_end,
              temp_max, throttled_start, throttled_end, throttled_seen):
    """Turn the raw frame times into the numbers the report is built from."""
    v = np.asarray(frame_ms, dtype=float)
    p99 = percentile(v, 99)
    return {
        "preset": preset,
        "width": width,
        "height": height,
        "sprites": sprites,
        "output": mode,
        "scaler": scaler,
        "driver": driver,
        "vsync": bool(vsync),
        "soundtrack": soundtrack,
        "duration_s": round(duration, 2),
        "frames": frames,
        "fps_mean": round(1000.0 / v.mean(), 2),
        "fps_min": round(1000.0 / v.max(), 2),
        "fps_max": round(1000.0 / v.min(), 2),
        "fps_1pct_low": round(1000.0 / p99, 2),
        "frametime_p99_ms": round(p99, 3),
        "frametime_mean_ms": round(float(v.mean()), 3),
        "frametime_median_ms": round(percentile(v, 50), 3),
        "frametime_stdev_ms": round(float(v.std()), 3),
        "temp_start_c": _round_or_none(temp_start),
        "temp_end_c": _round_or_none(temp_end),
        "temp_max_c": _round_or_none(temp_max),
        "throttled_start": throttled_start,
        "throttled_end": throttled_end,
        "throttled_during_run": throttled_seen not in ("0x0", "?"),
    }


def _round_or_none(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(x, 1)


def _temp(x):
    return "  n/a" if x is None else f"{x:.1f} C"


def format_report(r):
    """The human-readable block printed at the end of a run."""
    scale = f"{r['width']}x{r['height']} internal, {r['sprites']} sprites"
    lines = [
        "",
        "=== pixelbench - pixel art FPS benchmark =========================",
        f" preset...........: {r['preset']}  ({scale})",
        f" output...........: {r['output']}",
        f" scaler...........: {r['scaler']} @ {r['driver']}"
        f"{'  vsync ON' if r['vsync'] else '  vsync OFF'}",
        f" soundtrack.......: {r['soundtrack']}",
        f" duration.........: {r['duration_s']:.1f} s, {r['frames']} frames",
        "------------------------------------------------------------------",
        f" average FPS......: {r['fps_mean']:8.1f}",
        f" FPS min / max....: {r['fps_min']:8.1f} / {r['fps_max']:.1f}",
        f" 1% low (p99 ms)..: {r['fps_1pct_low']:8.1f}  ({r['frametime_p99_ms']:.2f} ms)",
        f" mean frametime...: {r['frametime_mean_ms']:8.2f} ms"
        f"  (median {r['frametime_median_ms']:.2f} ms)",
        f" stability........: stdev {r['frametime_stdev_ms']:.2f} ms",
        "------------------------------------------------------------------",
        f" temperature......: {_temp(r['temp_start_c'])} -> {_temp(r['temp_end_c'])}"
        f"  (peak {_temp(r['temp_max_c'])})",
        f" throttled........: {r['throttled_start']} -> {r['throttled_end']}"
        f"{'  <-- THROTTLING OCCURRED' if r['throttled_during_run'] else ''}",
        "==================================================================",
    ]
    return "\n".join(lines)


def write_json(report, path):
    """Write the machine-readable summary.

    Only measurements go in - no hostname, no user, no paths. A benchmark
    result should be safe to paste into an issue.
    """
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
