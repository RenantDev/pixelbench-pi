# Pixel art rules applied to the water

These are conventions from people who draw water for a living, not inventions.

References:
[Slynyrd — Water in Motion](https://www.slynyrd.com/blog/2018/10/12/pixelblog-10-water-in-motion) ·
[Wolthera — Animating water tiles: edges](https://wolthera.info/2019/06/animating-water-tiles-part-1-edges/) ·
[Draw Central — How to Pixel Water](https://drawcentral.com/2013/09/how-to-pixel-water.html) ·
[Colour cycling](https://en.wikipedia.org/wiki/Color_cycling)

## 1. Few flat tones, and highlights as a step

Pixel art water is a smooth band with a streak of light over it, not a gradient.
Mapping a continuous brightness onto the 13 tones of the palette turns into
noise. Here the base colour comes from depth (pre-computed per row) and each
highlight adds **+1 or +2 palette indices** — a step, never an interpolation.

## 2. Ordered dithering only on the transitions

A Bayer 4x4 matrix dithers the boundaries between palette bands, and it is
**switched off on the far rows**: up there the band changes fast and the
checkerboard turns into a dotted line across the horizon.

## 3. Sharper crest than trough

A real wave is not a symmetric sine; the top is steeper than the bottom, and
pixel art exaggerates that on purpose — though only *slightly*, since overdoing
it flattens the whole sea.

This rule is applied, but not as a separate step. It falls out of the trochoidal
profile in `scene.py` — `cos φ + Q·(cos²φ − 0.5)`, with `Q = Scene.STEEPNESS`
(0.34) — which sharpens the crest and widens the trough as a consequence of the
wave mechanics rather than as a cosmetic tweak. See
[Wave physics §2](wave-physics.md#2-trochoidal-gerstner-profile).

An earlier version multiplied the slope by a hand-tuned factor to get the same
look. The trochoidal term replaced it: it is derived rather than guessed, and it
costs nothing extra per frame.

## 4. Tileset cadence

The water phase advances in **steps** (`WATER_STEPS`, 10 per second), not
continuously: pixel art water is a tileset of a few frames. Continuous motion
gives away that it is maths, not art. The benchmark still recomputes everything
every frame — only the phase is quantised.

## 5. Slow rhythm

Real swell has a period of 6–12 s. `WAVE_OMEGA = 0.90 rad/s` gives ~7 s per
wave. The first version used 2.6 rad/s (2.4 s) and looked frantic. The cloud and
hill parallax was slowed to match, so nothing fights it.

## 6. Coast foam: jagged, and in few frames

Per Wolthera: an irregular edge, never a smooth line.

## 7. The sea palette pulls warm at the top

The crests mirror the sunset sky. An all-blue sea would fight the scene.

## The island and the castaway

The **SOS is laid out in stones** (5x5 cells per letter, each cell a 2x2 px
stone with a stride of 3 on both axes). Two traps, each of which cost a full
iteration to find:

- The cast shadow filled the 1 px gap and **glued the stones back into a bar**,
  so it is now drawn only where there is no neighbouring stone.
- With the highlight on a **top row**, stacked stones turned into horizontal
  stripes and the letter disappeared. The highlight has to sit on a **corner**.

The castaway's routine is a **pre-computed cyclic timeline** (wave → fire → SOS
→ fish, with walks between stops): given an instant `t` you know where he is and
what he is doing, with no state kept. That keeps the animation deterministic and
makes pause work for free.

**Mind the two scale systems.** The island's geometry (width, dune radius) is in
**screen pixels**, while the sprites (man, fire, palm) are in **design pixels**
multiplied by `scale = round(height/180)`. Mixing them up once produced an
island at double size with the characters floating above it.
