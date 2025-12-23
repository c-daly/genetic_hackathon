"""Evolution components: generation, mutation, and the evolution engine."""

from genetic_gp.evolution.generator import random_expr
from genetic_gp.evolution.mutation import mutate
from genetic_gp.evolution.engine import evolve, EvolutionResult

__all__ = [
    "random_expr",
    "mutate",
    "evolve",
    "EvolutionResult",
]
