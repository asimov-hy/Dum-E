"""Landmark dataclasses independent of any perception backend."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Landmark2D:
    """Normalized image-space landmark. x, y are in [0, 1]; z is relative depth."""

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Landmark3D:
    """World-space landmark in meters, origin near the hand geometric center."""

    x: float
    y: float
    z: float
