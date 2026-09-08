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


def test_soundtrack_is_bit_identical():
    track = make_music()
    assert list(track.shape) == REFERENCE["audio_shape"]
    assert _digest(track) == REFERENCE["audio_sha256"]
