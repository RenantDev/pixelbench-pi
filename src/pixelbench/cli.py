"""Command line, main loop and the on-screen HUD."""

import argparse
import os
import sys
import time

import numpy as np

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

from . import __version__  # noqa: E402
from .config import PRESETS  # noqa: E402
from .display import CpuOutput, GpuOutput, build_hud, fit_scale  # noqa: E402
from .metrics import format_report, summarize, write_json  # noqa: E402
from .scene import Scene  # noqa: E402
from .sprites import Flock, make_sprites  # noqa: E402
from .telemetry import Sensors  # noqa: E402

HELP_LINE = ("ESC quit | SPACE pause | F window | M music | "
             "H hide HUD | +/- sprites")
WARMUP_FRAMES = 30      # discarded at the start, while caches settle


def _size(text, what, parser):
    try:
        w, h = (int(v) for v in text.lower().split("x"))
    except ValueError:
        parser.error(f"{what} must be in WxH form, e.g. 640x360")
    return w, h


def build_parser():
    p = argparse.ArgumentParser(
        prog="pixelbench",
        description="Pixel art FPS benchmark for the Raspberry Pi.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("-c", "--load", choices=list(PRESETS), default="medium",
                   help="load preset")
    p.add_argument("-t", "--time", type=float, default=0.0,
                   help="duration in seconds (0 = run until ESC)")
    p.add_argument("-n", "--sprites", type=int, default=None,
                   help="number of sprites (overrides the preset)")
    p.add_argument("-r", "--resolution", default=None, metavar="WxH",
                   help="internal resolution, e.g. 640x360 (overrides the preset)")
    p.add_argument("-w", "--windowed", action="store_true",
                   help="run in a window (the default is fullscreen)")
    p.add_argument("-j", "--window", default="1280x720", metavar="WxH",
                   help="window size when using -w")
    p.add_argument("--cpu", action="store_true",
                   help="scale in software instead of the accelerated renderer")
    p.add_argument("--no-sound", action="store_true",
                   help="run silently (no ambient soundtrack)")
    p.add_argument("--volume", type=float, default=0.55, metavar="0..1",
                   help="soundtrack volume")
    p.add_argument("--vsync", action="store_true",
                   help="enable vsync (pins FPS to the monitor refresh rate)")
    p.add_argument("--headless", action="store_true",
                   help="no window (measures the CPU cost of rendering only)")
    p.add_argument("--no-hud", action="store_true", help="start with the HUD hidden")
    p.add_argument("--json", metavar="FILE", default=None,
                   help="also write the summary as JSON (measurements only)")
    p.add_argument("--version", action="version", version=f"pixelbench {__version__}")
    return p


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)

    preset = PRESETS[args.load]
    width, height = preset["w"], preset["h"]
    if args.resolution:
        width, height = _size(args.resolution, "--resolution", ap)
    n_sprites = preset["sprites"] if args.sprites is None else args.sprites
    window_size = _size(args.window, "--window", ap)

    headless = args.headless or not (os.environ.get("DISPLAY") or
                                     os.environ.get("WAYLAND_DISPLAY"))
    if headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        if not args.headless:
            print("warning: no DISPLAY - running headless (CPU cost only)",
                  file=sys.stderr)
    os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "0")  # nearest = crisp pixels

    pygame.init()
    from .audio import Music  # imported late: it pulls in the mixer
    music = None
    if not args.no_sound:
        music = Music(max(0.0, min(1.0, args.volume)))
        if not music.active:
            print(f"warning: no audio ({music.error}); continuing in silence",
                  file=sys.stderr)
    fullscreen = not args.windowed and not headless
    out = None
    if not args.cpu and not headless:
        try:
            out = GpuOutput(width, height, window_size, fullscreen, args.vsync)
        except Exception as e:  # no _sdl2, no accelerated driver, etc.
            print(f"warning: accelerated renderer unavailable ({e}); using CPU",
                  file=sys.stderr)
    if out is None:
        out = CpuOutput(width, height, window_size,
                        fullscreen and not headless, args.vsync)
    win_w, win_h = out.size
    driver = pygame.display.get_driver()

    buf = pygame.Surface((width, height))
    rng = np.random.default_rng(20260831)
    scene = Scene(width, height, rng)
    bird_frames = make_sprites(rng)
    flock = Flock(n_sprites, width, height, rng)

    def fonts_for(h):
        return (pygame.font.SysFont("dejavusansmono", max(18, h // 34), bold=True),
                pygame.font.SysFont("dejavusansmono", max(15, h // 48)))

    font_big, font_small = fonts_for(win_h)

    sensors = Sensors()
    temp_start, throttled_start = sensors.temp, sensors.throttled
    sensors.start()

    show_hud = not args.no_hud
    paused = False
    running = True
    clock = pygame.time.Clock()
    frame_ms = []        # ms per frame, after the warm-up
    frames = 0
    t_anim = 0.0
    volume = max(0.0, min(1.0, args.volume))
    if music is not None:
        music.play()
    t0 = time.perf_counter()
    last = t0
    hud_next = 0.0
    hud_dirty = True

    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif ev.key == pygame.K_SPACE:
                    paused = not paused
                elif ev.key == pygame.K_m and music is not None and music.active:
                    volume = 0.0 if volume > 0 else min(1.0, args.volume)
                    music.sound.set_volume(volume)
                    hud_dirty = True
                elif ev.key == pygame.K_h:
                    show_hud = not show_hud
                    hud_dirty = True
                elif ev.key == pygame.K_f and not headless:
                    out.toggle_fullscreen()
                    win_w, win_h = out.size
                    font_big, font_small = fonts_for(win_h)
                    hud_dirty = True
                elif ev.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    flock.resize(int(flock.n * 1.5) + 10)
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    flock.resize(int(flock.n / 1.5))

        now = time.perf_counter()
        dt = now - last
        last = now
        if not paused:
            t_anim += dt

        scene.draw(t_anim, buf)
        b = flock.blits(t_anim, 0.0 if paused else dt, bird_frames)
        if b:
            buf.blits(b, doreturn=False)

        # HUD: rebuilt only 4x per second, so it does not weigh on the frametime.
        if show_hud and (now >= hud_next or hud_dirty):
            hud_next = now + 0.25
            hud_dirty = False
            fps = clock.get_fps()
            factor, _ = fit_scale(win_w, win_h, width, height)
            sound = ""
            if music is not None and music.active:
                sound = " | sound ON" if volume > 0 else " | sound OFF"
            lines = [
                f"{fps:6.1f} FPS   {(1000.0 / fps if fps else 0):5.2f} ms",
                f"{width}x{height} x{factor} -> {win_w}x{win_h} | "
                f"{flock.n} sprites | {sensors.temp:.1f}C | {sensors.freq} MHz | "
                f"throttled {sensors.throttled}{sound}"
                f"{' | PAUSED' if paused else ''}",
            ]
            fs = [font_big, font_small]
            if now - t0 < 5.0:
                lines.append(HELP_LINE)
                fs.append(font_small)
            out.set_hud(build_hud(lines, fs))
        if not show_hud:
            out.set_hud(None)

        out.present(buf)
        clock.tick()

        frames += 1
        if frames > WARMUP_FRAMES:
            frame_ms.append(dt * 1000.0)
        if args.time > 0 and (now - t0) >= args.time:
            running = False

    total = time.perf_counter() - t0
    sensors.stop()
    temp_end, throttled_end = sensors.temp, sensors._throttled()
    fullscreen_now = out.fullscreen
    out.close()
    if music is not None:
        music.stop()
    pygame.quit()

    if len(frame_ms) < 5:
        print("run too short for reliable statistics", file=sys.stderr)
        return 1

    factor, _ = fit_scale(win_w, win_h, width, height)
    mode = "headless (dummy)" if headless else (
        f"{win_w}x{win_h} x{factor} ({'fullscreen' if fullscreen_now else 'window'})")
    soundtrack = ("off" if music is None or not music.active
                  else f"synthesised ambient, volume {volume:.2f}")
    report = summarize(
        frame_ms, preset=args.load, width=width, height=height, sprites=flock.n,
        mode=mode, scaler=out.name, driver=driver, vsync=args.vsync,
        soundtrack=soundtrack, duration=total, frames=frames,
        temp_start=temp_start, temp_end=temp_end, temp_max=sensors.temp_max,
        throttled_start=throttled_start, throttled_end=throttled_end,
        throttled_seen=sensors.throttled_seen)
    print(format_report(report))
    if args.json:
        write_json(report, args.json)
    return 0


def run():
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pygame.quit()
        print("\ninterrupted", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    run()
