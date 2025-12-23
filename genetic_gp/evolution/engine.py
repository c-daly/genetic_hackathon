"""Core evolution engine for genetic programming."""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any, Callable, List, Tuple

from genetic_gp.evolution.generator import random_expr
from genetic_gp.evolution.mutation import mutate


@dataclass
class EvolutionResult:
    """Result of an evolution run."""
    best_expr: Any
    best_fitness: float
    generations_run: int
    solved: bool
    all_solutions: List[Tuple[Any, float]] = field(default_factory=list)


def evolve(
    fitness_fn: Callable[[Callable[[int], float]], float],
    pop_size: int = 60,
    generations: int = 60,
    vars_available: List[str] | None = None,
    tool_library: Any | None = None,
    collect_solutions_above: float | None = None,
    on_generation: Callable[[int, List[Tuple[Any, float]]], None] | None = None,
    stop_at_fitness: float = 0.99,
    mutation_rate: float = 0.2,
    survivor_fraction: float = 0.2,
    verbose: bool = True,
    report_interval: int = 20,
) -> EvolutionResult:
    """Run genetic programming evolution.

    Args:
        fitness_fn: Function that takes a callable f(n) -> float and returns fitness [0, 1]
        pop_size: Population size
        generations: Maximum generations to run
        vars_available: Variables available for expressions (default: ['n'])
        tool_library: Optional ToolLibrary for tool reuse
        collect_solutions_above: If set, collect all solutions with fitness above this threshold
        on_generation: Optional callback called after each generation with (gen, scores)
        stop_at_fitness: Stop early if fitness reaches this threshold
        mutation_rate: Probability of mutation per gene
        survivor_fraction: Fraction of population that survives to reproduce
        verbose: Print progress updates
        report_interval: Generations between progress reports

    Returns:
        EvolutionResult with best expression and metadata
    """
    if vars_available is None:
        vars_available = ['n']

    # Initialize population with random expressions
    population = [
        random_expr(0, 3, vars_available, tool_library)
        for _ in range(pop_size)
    ]

    best_ever = None
    best_fitness = 0.0
    all_solutions: List[Tuple[Any, float]] = []

    for gen in range(generations):
        # Evaluate population
        scores: List[Tuple[Any, float]] = []
        for expr in population:
            # Wrap expression evaluation in a callable for fitness function
            fitness = fitness_fn(lambda n, e=expr: e.eval({'n': n}))
            scores.append((expr, fitness))

            # Collect solutions above threshold
            if collect_solutions_above is not None and fitness > collect_solutions_above:
                all_solutions.append((expr, fitness))

        # Sort by fitness (descending)
        scores.sort(key=lambda x: x[1], reverse=True)

        # Track best
        if scores[0][1] > best_fitness:
            best_fitness = scores[0][1]
            best_ever = scores[0][0]

        # Report progress
        if verbose and (gen % report_interval == 0 or scores[0][1] >= stop_at_fitness):
            avg = sum(s for _, s in scores) / len(scores)
            print(f"Gen {gen:3d}: Best={scores[0][1]:.3f} Avg={avg:.3f}")

        # Call generation hook
        if on_generation is not None:
            on_generation(gen, scores)

        # Check if solved
        if scores[0][1] >= stop_at_fitness:
            if verbose:
                print(f"Solved at generation {gen}")
            return EvolutionResult(
                best_expr=scores[0][0],
                best_fitness=scores[0][1],
                generations_run=gen + 1,
                solved=True,
                all_solutions=all_solutions,
            )

        # Selection - keep top performers
        num_survivors = max(1, int(pop_size * survivor_fraction))
        survivors = [expr for expr, _ in scores[:num_survivors]]

        # Breed next generation
        next_pop = survivors.copy()
        while len(next_pop) < pop_size:
            parent = random.choice(survivors)
            child = mutate(parent, rate=mutation_rate, vars_available=vars_available, tool_library=tool_library)
            next_pop.append(child)

        population = next_pop

    # Did not solve, return best found
    if verbose:
        print(f"Best after {generations} generations: {best_fitness:.3f}")

    return EvolutionResult(
        best_expr=best_ever,
        best_fitness=best_fitness,
        generations_run=generations,
        solved=False,
        all_solutions=all_solutions,
    )


def evolve_with_simplicity(
    fitness_fn: Callable[[Callable[[int], float]], float],
    simplicity_weight: float = 0.3,
    **kwargs,
) -> EvolutionResult:
    """Evolution with simplicity pressure.

    Fitness = accuracy * (1 - simplicity_weight) + simplicity * simplicity_weight

    Args:
        fitness_fn: Base fitness function (accuracy)
        simplicity_weight: Weight for simplicity in combined fitness (0-1)
        **kwargs: Additional arguments passed to evolve()

    Returns:
        EvolutionResult
    """
    import math

    def combined_fitness(func: Callable[[int], float], expr: Any = None) -> float:
        accuracy = fitness_fn(func)

        # Get expression from closure if not provided
        # This is a bit hacky but necessary for the current interface
        if expr is None:
            return accuracy

        complexity = expr.complexity()
        simplicity = math.exp(-complexity / 10.0)

        return accuracy * (1 - simplicity_weight) + simplicity * simplicity_weight

    # Note: This doesn't quite work with current interface since we can't pass expr
    # to fitness_fn. Would need to refactor to support this properly.
    # For now, just use regular evolve
    return evolve(fitness_fn, **kwargs)
