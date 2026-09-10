# Contributing

Thanks for taking a look. This is a small project; issues and pull requests are
both welcome.

## Setup

```bash
git clone https://github.com/RenantDev/pixelbench-pi
cd pixelbench-pi
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest
ruff check .
```

On a Raspberry Pi with distro packages, `python -m venv --system-site-packages
.venv` reuses the apt builds of `pygame` and `numpy` instead of compiling them.

The suite runs headless (`SDL_VIDEODRIVER=dummy`), so it needs no display.

## The golden hashes

`tests/test_golden.py` pins the rendered frames with SHA-256 hashes. The scene
is deterministic — fixed seed, quantised water phase — so any change to those
hashes means **the picture changed**.

The soundtrack is checked numerically instead of by hash: it goes through
`np.fft`, which does not round identically across architectures, so a bit-exact
hash would pass only on the machine that produced it. An RMS envelope over 64
windows still catches a changed chord, level or arrangement.

If a hash test fails and you did not intend a visual change, you have a bug.

If you *did* intend one, regenerate the hashes deliberately, say so in the pull
request, and include a before/after screenshot. **Never edit a hash to make a
test pass.**

## Performance changes

The point of this project is measurement, so a change that touches the render
loop needs numbers:

- run the same preset before and after, for at least 30 s, on the same machine;
- quote average FPS, 1% low and median frame time from both;
- confirm `throttled` was `0x0` in both, otherwise you measured your cooling.

`--json` makes the two runs easy to diff.

## Style

- `ruff check .` must pass. Line length 100.
- Do **not** run `ruff format`. The project lints but hand-formats: the colour
  palettes are laid out as ramps and the Bayer matrix as a 4x4 grid, and an
  autoformatter turns both into one-value-per-line columns that hide what they
  are. CI checks lint only, on purpose.
- Comments explain **why**, not what. The tricky parts of this codebase are
  tricky for physical reasons; if you change one, update the reasoning in
  `docs/` along with it.
- Where behaviour comes from a source (wave mechanics, pixel art convention),
  cite it. Several constants here look arbitrary and are not.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`,
`refactor:`, `docs:`, `test:`, `perf:`, `chore:`. Present tense, in English.

## Reporting a result

Benchmark numbers from other boards are genuinely useful. Open an issue with the
`--json` output and describe the environment: board, OS, display server,
resolution, cooling, and whether it is overclocked.

## Releasing

1. Bump `version` in `pyproject.toml` and `__version__` in
   `src/pixelbench/__init__.py`. They must match, and the publish workflow
   refuses to run if either disagrees with the tag.
2. Add the entry to `CHANGELOG.md`.
3. Tag `vX.Y.Z` and create the GitHub release. The workflow builds the wheel
   and sdist and attaches them.
4. Attach a copy of the sdist named `pixelbench-pi.tar.gz`, with no version in
   the name. That is what the README's one-line install points at through
   `/releases/latest/download/`, so the instruction never has to be edited.
5. Publishing to PyPI is gated on the repository variable `PYPI_PUBLISHING`
   being `enabled`, so a release does not fail against an index with no
   trusted publisher configured yet.
