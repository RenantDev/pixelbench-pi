import os

# Must be set before pygame is imported anywhere: the test suite has no display
# and no sound card (this is also how it runs in CI).
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
