# Audio synthesis, and the infrasound bug

The soundtrack is a 32-second seamless loop generated in numpy at startup: a
four-chord pad in A minor, a bass, sparse bells on a pentatonic scale, and surf
noise that breathes in time with the water on screen. No audio files ship with
the project.

It costs about 3 seconds to synthesise before the window opens, and **it does not
affect the frame rate** — measured at 99.9 FPS with sound against 99.6 without.

## The bug worth reading about

The first version distorted badly on monitor speakers. The obvious diagnosis was
clipping, and the obvious fix was to turn it down. Both were wrong.

The measurements said: **zero samples above 0.90, peak at 0.496.** Nothing was
clipping. What was actually happening: **13.4% of the total energy sat below
20 Hz**, coming from the surf noise, which used a 1/f^1.4 spectrum. That is
inaudible infrasound — but it drives the speaker cone to the end of its travel,
and everything audible riding on top of that excursion comes out dirty.

You cannot hear the problem. You have to measure it.

## The fixes

All in `make_music()`:

1. A **50 Hz high-pass** implemented by FFT, so it does not break the loop.
2. **Lighter noise**: 1/f^1.4 → 1/f^1.0.
3. **Bass level** 0.30 → 0.20.
4. **Randomised phase per partial** — with every sine starting at zero they add
   coherently and build tall peaks (a large crest factor) with no gain in
   perceived loudness.
5. **Level set by RMS** (target 0.11) instead of by peak.
6. A **soft-knee limiter** as a safety net, not as the fix.

Measured at the HDMI sink afterwards: energy below 20 Hz **0.0%**, and slow cone
excursion 0.0712 → 0.0057 — twelve times smaller.

## If you change the soundtrack

Measure the sub-20 Hz content before concluding a problem is about volume.
`tests/test_audio.py` asserts it stays below 0.01% of total energy, along with
the RMS target, the peak ceiling, and that the loop seam does not click.

## Loop seams

Every sine is snapped to a whole number of cycles in the 32 s window, so the
loop joins on the same phase. Bell tails that run past the end of the buffer are
folded back into the start, so the turn never chops a note in half.
