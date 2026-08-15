"""Coherence — one law, many costumes.

Nothing is done unless there is evidence.
Nothing is finished unless there is a next.
Nothing is remembered unless it was done.
"""

from coherence.core.fact import LAW, Fact, FactError, FactKind
from coherence.core.spine import Coherence
from coherence.core.types import Artifact, Bundle, Record, Truth
from coherence.evolve import DominoChain, EvolutionMemory

__all__ = [
    "Coherence",
    "Fact",
    "FactError",
    "FactKind",
    "LAW",
    "Bundle",
    "Record",
    "Artifact",
    "Truth",
    "DominoChain",
    "EvolutionMemory",
]
__version__ = "0.3.0"
