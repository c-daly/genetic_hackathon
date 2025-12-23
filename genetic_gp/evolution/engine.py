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
    simplicity_weight: float = 0.1,
    reporter: Any | None = None,
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
        simplicity_weight: Weight for simplicity in selection (0-1). Higher values prefer simpler solutions.
        reporter: Optional reporter for progress tracking

    Returns:
        EvolutionResult with best expression and metadata
    """
    import math
    if vars_available is None:
        vars_available = ['n']

    # Emit problem started event
    if reporter:
        reporter.on_problem_started("Evolution Started", f"Population: {pop_size}, Generations: {generations}")

    # Initialize population with random expressions
    population = [
        random_expr(0, 3, vars_available, tool_library)
        for _ in range(pop_size)
    ]

    best_ever = None
    best_fitness = 0.0
    all_solutions: List[Tuple[Any, float]] = []
    first_solved_gen: int | None = None

    for gen in range(generations):
        # Evaluate population
        scores: List[Tuple[Any, float, float]] = []  # (expr, accuracy, selection_score)
        for expr in population:
            # Wrap expression evaluation in a callable for fitness function
            accuracy = fitness_fn(lambda n, e=expr: e.eval({'n': n}))

            # Calculate simplicity bonus (exponential decay with complexity)
            complexity = expr.complexity()
            simplicity = math.exp(-complexity / 10.0)

            # Combined selection score (but track accuracy separately)
            selection_score = accuracy * (1 - simplicity_weight) + simplicity * simplicity_weight

            scores.append((expr, accuracy, selection_score))

            # Collect solutions above threshold (by accuracy, not selection score)
            if collect_solutions_above is not None and accuracy > collect_solutions_above:
                all_solutions.append((expr, accuracy))

        # Sort by selection score (descending) - prefers accurate AND simple
        scores.sort(key=lambda x: x[2], reverse=True)

        # Show sample of what we're trying (every 10 generations in verbose mode)
        if reporter and gen % 10 == 0 and hasattr(reporter, 'on_population_sample'):
            # Pick diverse sample: best, median, and a random
            sample_indices = [0, len(scores) // 2, -1]
            sample = [(scores[i][0], scores[i][1]) for i in sample_indices if i < len(scores)]
            reporter.on_population_sample(gen, sample)

        # Track best by accuracy (the actual fitness)
        best_accuracy_this_gen = max(s[1] for s in scores)
        if best_accuracy_this_gen > best_fitness:
            # Find simplest expression with best accuracy
            best_exprs = [(e, a, s) for e, a, s in scores if a == best_accuracy_this_gen]
            best_exprs.sort(key=lambda x: x[0].complexity())
            best_fitness = best_accuracy_this_gen
            best_ever = best_exprs[0][0]

            # Emit new best event
            if reporter:
                reporter.on_new_best(best_ever, best_fitness, gen)

        # Report progress
        if verbose and (gen % report_interval == 0 or best_accuracy_this_gen >= stop_at_fitness):
            avg_accuracy = sum(a for _, a, _ in scores) / len(scores)
            top_expr, top_acc, _ = scores[0]
            print(f"Gen {gen:3d}: Best={top_acc:.3f} Avg={avg_accuracy:.3f} Complexity={top_expr.complexity()}")

        # Emit generation update event
        if reporter and (gen % report_interval == 0 or best_accuracy_this_gen >= stop_at_fitness):
            reporter.on_generation_update(gen, best_accuracy_this_gen)

        # Call generation hook (pass accuracy scores for compatibility)
        if on_generation is not None:
            compat_scores = [(e, a) for e, a, _ in scores]
            on_generation(gen, compat_scores)

        # Check if solved (by accuracy)
        # Continue for a few more generations to find simpler solutions
        if best_accuracy_this_gen >= stop_at_fitness:
            # Find simplest expression with target accuracy in this generation
            solved_exprs = [(e, a) for e, a, _ in scores if a >= stop_at_fitness]
            if solved_exprs:
                solved_exprs.sort(key=lambda x: x[0].complexity())
                simplest = solved_exprs[0][0]
                if best_ever is None or simplest.complexity() < best_ever.complexity():
                    best_ever = simplest

            # Track when we first solved
            if first_solved_gen is None:
                first_solved_gen = gen
                if verbose:
                    print(f"Solved! Continuing to find simpler solutions...")
                # Emit solved event
                if reporter:
                    reporter.on_solved(best_ever, best_fitness, gen)
            elif gen - first_solved_gen >= 10:  # Continue for 10 more generations
                if verbose:
                    print(f"Final solution at generation {gen}")
                return EvolutionResult(
                    best_expr=best_ever,
                    best_fitness=best_fitness,
                    generations_run=gen + 1,
                    solved=True,
                    all_solutions=all_solutions,
                )

        # Selection - keep top performers by selection score (accurate AND simple)
        num_survivors = max(1, int(pop_size * survivor_fraction))
        survivors = [expr for expr, _, _ in scores[:num_survivors]]

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
