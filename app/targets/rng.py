"""The single source of nondeterminism in Buggy.

Exactly one seeded defect (AUT-006) is nondeterministic. It reads from the
generator below rather than from `random` directly, so the runner owns the seed
and every run stays reproducible while individual repeats genuinely differ.

That distinction is the point: the flake-rate column on /benchmark is measured
from observed outcome instability across repeats, not asserted from a constant.
"""

from __future__ import annotations

import random

# ponytail: one module-level generator instead of threading `rng` through every
# target signature. Only the runner reseeds it, and only between repeats.
RNG = random.Random(0)


def reseed(seed: int) -> None:
    """Reset the generator. Called by the runner before each repeat of a build."""
    RNG.seed(seed)


def flaky(probability: float) -> bool:
    """True with the given probability, drawn from the run-controlled generator."""
    return RNG.random() < probability
