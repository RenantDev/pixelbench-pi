"""Every preset must render without blowing up, on any hardware."""

import numpy as np
import pygame
import pytest

from pixelbench.cli import build_parser, main
from pixelbench.config import PRESETS
from pixelbench.scene import Scene
from pixelbench.sprites import Flock, make_sprites


@pytest.mark.parametrize("preset", list(PRESETS))
def test_every_preset_renders(preset):
    pygame.init()
    try:
        cfg = PRESETS[preset]
        rng = np.random.default_rng(20260831)
        scene = Scene(cfg["w"], cfg["h"], rng)
        frames = make_sprites()
        flock = Flock(cfg["sprites"], cfg["w"], cfg["h"], rng)
        buf = pygame.Surface((cfg["w"], cfg["h"]))
        for i in range(12):
            t = i * 0.37
            scene.draw(t, buf)
            flock.blits(t, 0.016, frames)
        arr = pygame.surfarray.array3d(buf)
        assert arr.shape == (cfg["w"], cfg["h"], 3)
        assert arr.any(), "the frame came out entirely black"
    finally:
        pygame.quit()


def test_internal_resolutions_divide_1080p_exactly():
    """This is why the presets are these numbers: on a 1080p panel the integer
    upscale fills the screen with no letterboxing and no resampling."""
    for cfg in PRESETS.values():
        assert 1920 % cfg["w"] == 0
        assert 1080 % cfg["h"] == 0
        assert 1920 // cfg["w"] == 1080 // cfg["h"]


def test_flock_resizes_both_ways():
    rng = np.random.default_rng(1)
    flock = Flock(10, 240, 135, rng)
    flock.resize(40)
    assert flock.n == 40 and len(flock.x) == 40
    flock.resize(5)
    assert flock.n == 5 and len(flock.x) == 5
    flock.resize(0)
    assert flock.blits(0.0, 0.016, []) == ()


def test_cli_runs_headless_and_reports(tmp_path, capsys):
    out = tmp_path / "result.json"
    rc = main(["-c", "light", "-t", "2", "--headless", "--no-sound",
               "--no-hud", "--json", str(out)])
    assert rc == 0
    assert "average FPS" in capsys.readouterr().out
    assert out.exists()


def test_bad_resolution_is_rejected():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--resolution"])
