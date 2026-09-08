# Wave physics

The sea in this benchmark is not decoration with a sine wave on it. Every choice
below came from a reference, and each one replaced something that looked wrong.

References:
[Trochoidal (Gerstner) wave](https://en.wikipedia.org/wiki/Trochoidal_wave) ·
[Rendering Water using Gerstner Waves](https://jaynakum.github.io/blog/5/GerstnerWaves.html) ·
[Coastal Dynamics — Refraction](https://geo.libretexts.org/Bookshelves/Oceanography/Coastal_Dynamics_(Bosboom_and_Stive)/05:_Coastal_hydrodynamics/5.02:_Wave_transformation/5.2.3:_Refraction) ·
[Breaker index](https://www.coastalwiki.org/wiki/Breaker_index) ·
[Swash zone dynamics](https://www.coastalwiki.org/wiki/Swash_zone_dynamics)

## 1. Deep-water dispersion: ω = √(g·k)

A longer wave travels faster. The speed of each train is therefore **not a free
parameter** — it is `speed = √(frequency)`. This is what makes the superposition
of the four trains look like sea instead of summed noise: with arbitrary speeds
the trains slide over one another wrongly and the eye catches it immediately.

The four trains use incommensurable frequencies (1.00, 1.73, 2.91, 5.31) on
purpose, so the crests never repeat the same drawing.

## 2. Trochoidal (Gerstner) profile

A real gravity wave has a sharp crest and a wide, shallow trough — not a
symmetric sine. Implemented as:

```
cos(φ) + Q·(cos²φ − 0.5)
```

which is the first-order expansion of `cos(φ + Q·sin φ)`. It comes for free: no
extra sine per train.

**The `−0.5` is essential, and `−1` is the trap.** The mean of cos² is 0.5, so
subtracting 1 biases every sample downward and the entire sea goes dark. There
is a test for this (`test_trochoidal_bias_is_removed`).

## 3. Refraction and shoaling at the island

The island is a **bank**, not an obstacle. That distinction is what makes the
interaction look real instead of foam glued to an edge.

In shallow water `c = √(g·h)`, so the part of the crest over the shallows falls
behind and the crest **bends** to follow the depth contours (Snell's law:
sin φ / c = constant), with the wavelength shortening along with it. The height
grows by Green's law, `H ∝ h^(−1/4)`.

Both are pre-computed as two static fields — the extra phase accumulated along
the wave's path (a `cumsum` down y) and an amplitude gain. **Zero per-frame cost.**

*One necessary adjustment:* integrated against the raw bathymetry the lag passes
90 rad and scrambles the wave field. It is normalised to ~4.5 rad — less than
one wavelength. Same refraction drawing, far calmer bottom.

## 4. Breaker index: it breaks when H > 0.78·h

Combined with shoaling, this gives a break depth ∝ H₀^0.8 — a bigger crest
breaks further from the beach, which is what you see at sea. That is where the
exponent 0.8 in the foam width comes from.

## 5. Swash and backwash are asymmetric

The water runs up in a fast surge (~20% of the cycle) and drains back slowly
through the rest. The symmetric cosine used at first was part of why the foam
looked like a line pulsing on and off.

## How the sea is actually drawn

The water is **not** a plasma of sines in screen coordinates — that produced a
flat interference pattern. Each row below the horizon has its own wavelength
(wide near the camera, narrow far away), and the phase is the running sum of
those wavelengths row by row. The crests then come out parallel to the horizon
and bunch up with distance on their own.

Four wave trains sum. Brightness comes from the **slope** (the derivative — the
face that catches the light), never from the height; using height leaves the
water looking like a rippled rug. Foam appears only on the steep crests of near
water, broken up by the finest ripple train so it does not become a continuous
band. Near the horizon the wave gets smaller than a pixel, so a damping ramp
prevents moiré and doubles as distance haze.

> **A path that did not work: true perspective (z ∝ 1/y).** It is physically
> correct, but it throws all the variation onto the horizon and leaves the water
> near the camera practically flat. If you rework the sea, do not go back down
> that road.

## Surf at the island

The island's footprint on the water is a flattened ellipse. The foam field uses
the distance in **pixels** to that ellipse — `(d−1)/|∇d|` — and not the raw
elliptical distance, which would come out thin at the front and enormously wide
at the sides.

What makes it read as a wave hitting a sandbar rather than an ornament:

- **Every point of the shore has its own delay** (`shore_offset`, shared between
  water and sand). Without it the foam lights up all at once and becomes a line
  going up and down.
- The foam is a **continuous sheet whose width varies per column**, not a blob
  with holes. Varying width reads as water covering more bank here and less
  there; punching holes in a blob only produces texture.
- The sheet has a **bright crest on the outer edge** (where it is breaking) and
  foam **crumbling behind it** (cut by the ripple). Filling it all white turns
  into a bib stuck to the island.
- A **dark trough right behind the crest** — the crest/trough contrast is what
  gives the wave its volume.
- The per-column width is **smoothed between neighbours** (3-wide moving
  average): without it the sheet gets jagged and even sheds bubbles detached
  from the island.
- On the sand, the lick rises in **tongues** (same delay function), leaving wet
  sand as it draws back. These are 40 pre-built frames of one wave cycle,
  indexed by phase — zero per-frame cost.

All of it is computed only in a rectangle around the island, never over the
whole sea.
