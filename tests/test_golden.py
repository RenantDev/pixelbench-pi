"""The scene is deterministic, so it can be pinned down to the pixel.

These hashes come from the reference implementation. A change here means the
rendered image changed - which is fine if you meant it, and a bug if you did
not. Never edit a hash just to make the test pass.
"""

import hashlib
import json
import pathlib

import numpy as np
import pygame
import pytest

from pixelbench.audio import make_music
from pixelbench.config import PRESETS
from pixelbench.scene import Scene

REFERENCE = json.loads((pathlib.Path(__file__).parent / "golden/reference.json").read_text())
SEED = 20260831


def _digest(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


@pytest.fixture(scope="module")
def _pygame():
    pygame.init()
    yield
    pygame.quit()


@pytest.mark.parametrize("preset", ["light", "medium"])
def test_frames_are_bit_identical(preset, _pygame):
    cfg = PRESETS[preset]
    scene = Scene(cfg["w"], cfg["h"], np.random.default_rng(SEED))
    buf = pygame.Surface((cfg["w"], cfg["h"]))
    for t in REFERENCE["instants"]:
        scene.draw(t, buf)
        got = _digest(pygame.surfarray.array3d(buf).astype(np.uint8))
        assert got == REFERENCE["frames"][f"{preset}@{t}"], f"frame changed at t={t}"


def test_soundtrack_matches_the_reference():
    """The audio is compared numerically rather than by hash.

    It goes through np.fft, which does not round identically across
    architectures and numpy builds - a bit-exact hash would pass on the machine
    that generated it and fail everywhere else. The RMS envelope over 64 windows
    still catches a changed chord, a changed level or a changed arrangement,
    which is what the test is actually for.
    """
    track = make_music()
    assert list(track.shape) == REFERENCE["audio_shape"]

    mono = track.astype(np.float64).mean(axis=1) / 32767.0
    assert mono.std() > 0, "the soundtrack came out silent"
    assert np.sqrt((mono ** 2).mean()) == pytest.approx(REFERENCE["audio_rms"], rel=1e-3)
    assert np.abs(mono).max() == pytest.approx(REFERENCE["audio_peak"], rel=1e-3)

    envelope = [float(np.sqrt((b ** 2).mean())) for b in np.array_split(mono, 64)]
    np.testing.assert_allclose(envelope, REFERENCE["audio_envelope_rms_64"],
                               rtol=1e-3, atol=1e-5)
