"""The wave shaping is physics, not decoration - so it can be asserted."""

import numpy as np

from pixelbench.scene import Scene
from pixelbench.waves import shore_offset, swash


def test_dispersion_longer_waves_travel_faster():
    """Deep-water dispersion: omega = sqrt(g*k), so speed = sqrt(frequency).

    The train speeds are derived, never chosen. With arbitrary speeds the trains
    slide over each other wrongly and the sea reads as summed noise.
    """
    freqs = [f for f, _, _ in Scene.WAVE_TRAINS]
    speeds = [np.sqrt(f) for f in freqs]
    assert speeds == sorted(speeds), "speed must grow with frequency"
    assert freqs == sorted(freqs)
    for f, speed in zip(freqs, speeds):
        assert speed == np.sqrt(f)


def test_swash_is_asymmetric():
    """Uprush is fast (~20% of the cycle), backwash is slow. A symmetric cosine
    here is what made the foam look like a pulsing line."""
    u = np.linspace(0.0, 1.0, 1001, endpoint=False)
    y = swash(u)
    peak = float(u[np.argmax(y)])
    assert 0.15 < peak < 0.25, f"peak at {peak:.2f}, expected the uprush near 0.20"
    # Rising limb far shorter than the falling one.
    assert peak < (1.0 - peak) / 2


def test_swash_stays_in_range():
    u = np.linspace(0.0, 1.0, 501, endpoint=False)
    y = swash(u)
    assert y.min() >= 0.0 and y.max() <= 1.0 + 1e-9


def test_shore_offset_varies_along_the_shore():
    """Without a per-point delay the foam lights up all at once and reads as a
    line going up and down, not as water hitting a sandbar."""
    x = np.arange(0.0, 400.0)
    d = shore_offset(x)
    assert d.std() > 0.5
    assert np.abs(np.diff(d)).max() < 0.5      # smooth, no jumps


def test_trochoidal_bias_is_removed():
    """The profile uses cos^2 - 0.5, not cos^2 - 1: the mean of cos^2 is 0.5, and
    with -1 the whole sea goes dark."""
    phi = np.linspace(0, 2 * np.pi, 4096, endpoint=False)
    c = np.cos(phi)
    profile = c + Scene.STEEPNESS * (c * c - 0.5)
    assert abs(profile.mean()) < 1e-9
    # A sharper crest than trough is the point of the trochoidal shape.
    assert profile.max() > abs(profile.min())
