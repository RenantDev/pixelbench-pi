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

`tests/test_golden.py` pins the rendered frames and the soundtrack with SHA-256
hashes. The scene is deterministic — fixed seed, quantised water phase — so any
change to those hashes means **the picture or the sound changed**.

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
