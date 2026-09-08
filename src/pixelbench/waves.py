"""Wave shaping shared by the water, the surf line and the beach.

The functions here are small, but they are the ones that decide whether the
picture reads as sea or as an animated texture. See `docs/wave-physics.md` for
the references behind each one.
"""

import numpy as np


def swash(u):
    """Time profile of the swash, for u = cycle phase in [0, 1).

    Uprush and backwash are NOT symmetric: the water runs up in a fast surge
    (~20% of the cycle) and drains back slowly through the rest. Using a
    symmetric cosine here is what made the foam look like a pulsing line.
    """
    return np.where(u < 0.20, u * 5.0,
                    np.clip(1.0 - (u - 0.20) / 0.80, 0.0, 1.0) ** 1.35)


def shore_offset(x):
    """Delay with which the wave reaches each point along the shore.

    A beach does not take the whole wave at once: the sandbar is irregular and
    the break walks along the shore. Without this the foam rises and falls as a
    single line, which does not read as water hitting a sandbar.
    """
    return np.sin(x * 0.085) * 1.15 + np.sin(x * 0.031 + 2.0) * 1.75
