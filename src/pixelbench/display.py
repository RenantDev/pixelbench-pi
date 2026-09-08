"""Two ways to get the internal frame onto the screen, behind one interface.

This split is itself a measurement. The scene renders at 240x135 ... 960x540 and
has to reach a 1920x1080 panel; who does that upscale dominates the result.

On a Raspberry Pi 5, scaling to 1080p ON THE CPU costs about 10 ms per frame and
becomes the bottleneck - every preset used to sit pinned at ~45 FPS regardless of
its actual load. Handing the upscale to the SDL renderer roughly doubles the
frame rate and lets it vary with the real cost of the scene again. `--cpu`
selects the software path on purpose, so the two can be compared.

Both classes expose the same interface (`name`, `size`, `toggle_fullscreen`,
`set_hud`, `present`, `close`), so the benchmark never needs to know which one
it got.
"""

import pygame

from .config import TITLE


def fit_scale(win_w, win_h, w, h):
    """Integer scale factor (crisp pixels) and the centred destination rect.

    The factor is an integer on purpose: a fractional upscale resamples and
    smears the pixel art. The presets are exact divisors of 1920x1080 so that
    this comes out exact on a 1080p panel, with no letterboxing.
    """
    f = max(1, min(win_w // w, win_h // h))
    dw, dh = w * f, h * f
    return f, pygame.Rect((win_w - dw) // 2, (win_h - dh) // 2, dw, dh)


class GpuOutput:
    """Scales the scene on the SDL renderer (accelerated). HUD at native res."""

    name = "sdl2 (accelerated)"

    def __init__(self, w, h, window_size, fullscreen, vsync):
        from pygame._sdl2 import video
        self._video = video
        self.w, self.h = w, h
        self.window_size = window_size
        self.fullscreen = fullscreen
        self.vsync = vsync
        self.win = video.Window(TITLE, size=window_size,
                                fullscreen_desktop=fullscreen)
        self.ren = video.Renderer(self.win, vsync=vsync)
        self.tex = video.Texture(self.ren, (w, h), streaming=True)
        self.hud_tex = None
        self.hud_pos = (8, 8)
        pygame.mouse.set_visible(not fullscreen)

    @property
    def size(self):
        return self.win.size

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.win.set_fullscreen(desktop=True)
        else:
            self.win.set_windowed()
            self.win.size = self.window_size
        pygame.mouse.set_visible(not self.fullscreen)

    def set_hud(self, surface):
        self.hud_tex = (self._video.Texture.from_surface(self.ren, surface)
                        if surface is not None else None)

    def present(self, buf):
        win_w, win_h = self.win.size
        _, dst = fit_scale(win_w, win_h, self.w, self.h)
        self.tex.update(buf)
        self.ren.clear()
        self.tex.draw(dstrect=dst)
        if self.hud_tex is not None:
            self.hud_tex.draw(dstrect=self.hud_tex.get_rect(topleft=self.hud_pos))
        self.ren.present()

    def close(self):
        self.hud_tex = None


class CpuOutput:
    """Software path: transform.scale + blit onto the video surface."""

    name = "software (CPU)"

    def __init__(self, w, h, window_size, fullscreen, vsync):
        self.w, self.h = w, h
        self.window_size = window_size
        self.fullscreen = fullscreen
        self.vsync = vsync
        pygame.display.set_caption(TITLE)
        self.screen = self._open()
        self.hud = None

    def _open(self):
        flags = pygame.FULLSCREEN if self.fullscreen else 0
        size = (0, 0) if self.fullscreen else self.window_size
        screen = pygame.display.set_mode(size, flags, vsync=1 if self.vsync else 0)
        pygame.mouse.set_visible(not self.fullscreen)
        return screen

    @property
    def size(self):
        return self.screen.get_size()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.screen = self._open()

    def set_hud(self, surface):
        self.hud = surface

    def present(self, buf):
        win_w, win_h = self.screen.get_size()
        _, dst = fit_scale(win_w, win_h, self.w, self.h)
        if dst.size != (win_w, win_h):
            self.screen.fill((0, 0, 0))
        self.screen.blit(pygame.transform.scale(buf, dst.size), dst.topleft)
        if self.hud is not None:
            self.screen.blit(self.hud, (8, 8))
        pygame.display.flip()

    def close(self):
        self.hud = None


def build_hud(lines, fonts):
    """Draw the HUD lines (with a drop shadow) onto a transparent surface."""
    imgs = [f.render(t, True, (255, 255, 255)) for t, f in zip(lines, fonts)]
    shadows = [f.render(t, True, (0, 0, 0)) for t, f in zip(lines, fonts)]
    width = max(i.get_width() for i in imgs) + 4
    height = sum(i.get_height() + 2 for i in imgs) + 4
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    y = 0
    for img, shadow in zip(imgs, shadows):
        s.blit(shadow, (2, y + 2))
        s.blit(img, (0, y))
        y += img.get_height() + 2
    return s
