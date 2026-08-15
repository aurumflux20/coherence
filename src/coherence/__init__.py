"""Coherence — agent reality stack that evolves with use."""

from coherence.core.spine import Coherence
from coherence.core.types import Artifact, Bundle, Record, Truth
from coherence.evolve import DominoChain, EvolutionMemory

__all__ = [
    "Coherence",
    "Bundle",
    "Record",
    "Artifact",
    "Truth",
    "DominoChain",
    "EvolutionMemory",
]
__version__ = "0.2.0"
