"""Guards on the soundtrack, all of them from a bug that actually shipped.

The first version distorted on monitor speakers. It was not clipping: 13.4% of
the energy sat below 20 Hz, inaudible infrasound that drives the cone to the end
of its travel and muddies everything above it. These tests are what stops that
from coming back unnoticed.
"""

import numpy as np

from pixelbench.audio import CEILING, RATE, TARGET_RMS, make_music


def _mono(track):
    return track.astype(np.float64).mean(axis=1) / 32767.0


def test_no_infrasound():
    """Sub-20 Hz energy must be negligible. This is the whole point."""
    x = _mono(make_music())
    power = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(len(x), 1.0 / RATE)
    share = power[freqs < 20.0].sum() / power.sum()
    assert share < 1e-4, f"{share:.2%} of the energy is below 20 Hz"


def test_level_is_set_by_rms_not_peak():
    x = _mono(make_music())
    rms = np.sqrt((x ** 2).mean())
    # The limiter pulls the level slightly below the target; it must not drift far.
    assert 0.6 * TARGET_RMS < rms < TARGET_RMS * 1.05


def test_stays_under_the_ceiling():
    x = np.abs(make_music().astype(np.float64) / 32767.0)
    assert x.max() <= CEILING + 1e-6


def test_loop_joins_without_a_click():
    """A loop that does not join produces a click once every 32 seconds."""
    track = make_music().astype(np.float64) / 32767.0
    seam = np.abs(track[0] - track[-1]).max()
    inner = np.abs(np.diff(track[:2000], axis=0)).max()
    assert seam <= inner * 4, "the loop seam jumps more than the signal itself"
