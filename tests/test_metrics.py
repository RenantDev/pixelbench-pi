import math

import numpy as np

from pixelbench.metrics import format_report, percentile, summarize


def test_percentile_matches_numpy():
    v = np.array([1.0, 2.0, 3.0, 10.0, 4.0])
    for p in (0, 50, 90, 99, 100):
        assert percentile(v, p) == float(np.percentile(v, p))


def test_percentile_of_empty_is_nan():
    assert math.isnan(percentile([], 50))


def _report(frame_ms):
    return summarize(
        frame_ms, preset="medium", width=480, height=270, sprites=90,
        mode="1920x1080 x4 (fullscreen)", scaler="sdl2 (accelerated)", driver="x11",
        vsync=False, soundtrack="off", duration=10.0, frames=1000,
        temp_start=50.0, temp_end=55.0, temp_max=56.0,
        throttled_start="0x0", throttled_end="0x0", throttled_seen="0x0")


def test_summary_numbers():
    r = _report([10.0] * 100)
    assert r["fps_mean"] == 100.0
    assert r["frametime_median_ms"] == 10.0
    assert r["throttled_during_run"] is False


def test_one_percent_low_is_worse_than_the_average():
    """The 1% low is the number that describes how a run actually felt."""
    # A steady 10 ms with a 2% tail of 40 ms stalls: the average barely moves,
    # the 1% low collapses. That gap is exactly what the metric is for.
    r = _report([10.0] * 980 + [40.0] * 20)
    assert r["fps_mean"] > 90.0
    assert r["fps_1pct_low"] < 30.0


def test_throttling_is_latched_into_the_report():
    r = summarize(
        [10.0] * 50, preset="heavy", width=640, height=360, sprites=220,
        mode="headless (dummy)", scaler="software (CPU)", driver="dummy",
        vsync=False, soundtrack="off", duration=5.0, frames=500,
        temp_start=60.0, temp_end=84.0, temp_max=85.0,
        throttled_start="0x0", throttled_end="0x0", throttled_seen="0x60000")
    assert r["throttled_during_run"] is True
    assert "THROTTLING OCCURRED" in format_report(r)


def test_missing_telemetry_does_not_break_the_report():
    """On non-Pi hardware the sensors return NaN; the report must still render."""
    r = summarize(
        [10.0] * 50, preset="light", width=240, height=135, sprites=24,
        mode="headless (dummy)", scaler="software (CPU)", driver="dummy",
        vsync=False, soundtrack="off", duration=5.0, frames=500,
        temp_start=float("nan"), temp_end=float("nan"), temp_max=float("nan"),
        throttled_start="?", throttled_end="?", throttled_seen="?")
    assert r["temp_start_c"] is None
    assert "n/a" in format_report(r)
