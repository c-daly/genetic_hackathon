"""Core evolution engine for genetic programming."""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any, Callable, List, Tuple

from genetic_gp.evolution.generator import random_expr
from genetic_gp.evolution.mutation import mutate
from genetic_gp.core.simplify import simplify


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
    reporter: Any | None = None,
    max_complexity: int = 10,
    simplify_generations: int = 30,
) -> EvolutionResult:
    """Run genetic programming evolution.

    Two-phase approach:
    1. Evolve to find a correct solution (accuracy >= stop_at_fitness)
    2. Continue aggressively simplifying until no improvement or max generations

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
        reporter: Optional reporter for progress tracking
        max_complexity: Target maximum complexity (keep simplifying until reached or stuck)
        simplify_generations: Max generations to spend simplifying after solving

    Returns:
        EvolutionResult with best expression and metadata
    """
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
    last_improvement_gen: int = 0

    for gen in range(generations):
        # Evaluate population
        scores: List[Tuple[Any, float]] = []  # (expr, accuracy)
        for expr in population:
            # Wrap expression evaluation in a callable for fitness function
            accuracy = fitness_fn(lambda n, e=expr: e.eval({'n': n}))
            scores.append((expr, accuracy))

            # Collect solutions above threshold
            if collect_solutions_above is not None and accuracy > collect_solutions_above:
                all_solutions.append((expr, accuracy))

        # Sort by accuracy (descending), then by complexity (ascending) as tiebreaker
        scores.sort(key=lambda x: (-x[1], x[0].complexity()))

        # Show sample of what we're trying (every 10 generations in verbose mode)
        if reporter and gen % 10 == 0 and hasattr(reporter, 'on_population_sample'):
            # Pick diverse sample: best, median, and worst
            sample_indices = [0, len(scores) // 2, -1]
            sample = [scores[i] for i in sample_indices if i < len(scores)]
            reporter.on_population_sample(gen, sample)

        # Track best by accuracy
        best_accuracy_this_gen = max(a for _, a in scores)
        if best_accuracy_this_gen > best_fitness:
            # Find simplest expression with best accuracy (already sorted by complexity as tiebreaker)
            best_exprs = [(e, a) for e, a in scores if a == best_accuracy_this_gen]
            best_fitness = best_accuracy_this_gen
            best_ever = best_exprs[0][0]  # First one is simplest due to sort

            # Emit new best event
            if reporter:
                reporter.on_new_best(best_ever, best_fitness, gen)

        # Report progress
        if verbose and (gen % report_interval == 0 or best_accuracy_this_gen >= stop_at_fitness):
            avg_accuracy = sum(a for _, a in scores) / len(scores)
            top_expr, top_acc = scores[0]
            print(f"Gen {gen:3d}: Best={top_acc:.3f} Avg={avg_accuracy:.3f} Complexity={top_expr.complexity()}")

        # Emit generation update event
        if reporter and (gen % report_interval == 0 or best_accuracy_this_gen >= stop_at_fitness):
            reporter.on_generation_update(gen, best_accuracy_this_gen)

        # Call generation hook
        if on_generation is not None:
            on_generation(gen, scores)

        # Check if solved - continue aggressively simplifying
        if best_accuracy_this_gen >= stop_at_fitness:
            # Find simplest expression with target accuracy in this generation
            solved_exprs = [(e, a) for e, a in scores if a >= stop_at_fitness]
            if solved_exprs:
                # Already sorted by complexity as tiebreaker
                simplest = solved_exprs[0][0]

                # Also try to simplify using tool library if available
                if tool_library and hasattr(tool_library, 'try_simplify'):
                    simplified, was_simplified = tool_library.try_simplify(simplest)
                    if was_simplified:
                        # Verify simplified version still works
                        simp_acc = fitness_fn(lambda n, e=simplified: e.eval({'n': n}))
                        if simp_acc >= stop_at_fitness:
                            simplest = simplified
                            if reporter and hasattr(reporter, 'on_thought'):
                                reporter.on_thought("Simplified using tool library", f"{simplified}")

                if best_ever is None or simplest.complexity() < best_ever.complexity():
                    old_complexity = best_ever.complexity() if best_ever else float('inf')
                    best_ever = simplest
                    last_improvement_gen = gen
                    if reporter and hasattr(reporter, 'on_thought'):
                        reporter.on_thought("Found simpler solution", f"{simplest} (complexity {old_complexity} -> {simplest.complexity()})")

            # Track when we first solved
            if first_solved_gen is None:
                first_solved_gen = gen
                last_improvement_gen = gen
                if verbose:
                    print(f"Solved! Complexity={best_ever.complexity()}. Aggressively simplifying...")
                # Emit solved event
                if reporter:
                    reporter.on_solved(best_ever, best_fitness, gen)
            else:
                # Check stopping conditions for simplification phase
                gens_since_solve = gen - first_solved_gen
                gens_since_improvement = gen - last_improvement_gen

                # Stop if: reached target complexity, OR spent max generations, OR stuck for 10 gens
                if best_ever.complexity() <= max_complexity:
                    if verbose:
                        print(f"Reached target complexity {best_ever.complexity()} at gen {gen}")
                    return EvolutionResult(
                        best_expr=simplify(best_ever),
                        best_fitness=best_fitness,
                        generations_run=gen + 1,
                        solved=True,
                        all_solutions=all_solutions,
                    )
                elif gens_since_solve >= simplify_generations:
                    if verbose:
                        print(f"Max simplify generations reached. Final complexity: {best_ever.complexity()}")
                    return EvolutionResult(
                        best_expr=simplify(best_ever),
                        best_fitness=best_fitness,
                        generations_run=gen + 1,
                        solved=True,
                        all_solutions=all_solutions,
                    )
                elif gens_since_improvement >= 10:
                    if verbose:
                        print(f"No improvement for 10 gens. Final complexity: {best_ever.complexity()}")
                    return EvolutionResult(
                        best_expr=simplify(best_ever),
                        best_fitness=best_fitness,
                        generations_run=gen + 1,
                        solved=True,
                        all_solutions=all_solutions,
                    )

        # Selection - keep top performers by accuracy (simpler ones win ties)
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
        best_expr=simplify(best_ever) if best_ever else None,
        best_fitness=best_fitness,
        generations_run=generations,
        solved=False,
        all_solutions=all_solutions,
    )


def _count_primitive_usage(expr: Any) -> dict:
    """Count how many times each derived primitive is used in an expression."""
    from genetic_gp.core.expressions import PrimitiveCall

    counts = {}

    def count_recursive(e):
        if isinstance(e, PrimitiveCall):
            name = e.primitive_name
            counts[name] = counts.get(name, 0) + 1
            if hasattr(e, 'arg'):
                count_recursive(e.arg)
        elif hasattr(e, 'left'):
            count_recursive(e.left)
            count_recursive(e.right)
        elif hasattr(e, 'body'):
            count_recursive(e.start)
            count_recursive(e.end)
            count_recursive(e.body)
        elif hasattr(e, 'expr'):
            count_recursive(e.expr)

    count_recursive(expr)
    return counts


# Backwards compatibility
_count_tool_usage = _count_primitive_usage


def evolve_and_save_primitive(
    fitness_fn: Callable[[Callable[[int], float]], float],
    primitive_library: Any,
    primitive_name: str,
    reporter: Any | None = None,
    verbose: bool = True,
    **kwargs,
) -> EvolutionResult:
    """Evolve a solution and try to save it as a derived primitive.

    Args:
        fitness_fn: Fitness function
        primitive_library: PrimitiveLibrary to save to
        primitive_name: Name for the primitive if saved
        reporter: Optional reporter for progress
        verbose: Print progress
        **kwargs: Additional args for evolve()

    Returns:
        EvolutionResult
    """
    # Show existing primitives
    if verbose and len(primitive_library) > 0:
        print(f"\nAvailable primitives: {[p.name for p in primitive_library.list_primitives()]}")

    # Evolve
    result = evolve(
        fitness_fn,
        tool_library=primitive_library,  # Pass to evolve (uses tool_library param name)
        reporter=reporter,
        verbose=verbose,
        **kwargs,
    )

    if not result.solved:
        if verbose:
            print(f"Did not solve - not saving primitive")
        return result

    # Check primitive usage in solution
    usage = _count_primitive_usage(result.best_expr)
    if usage and verbose:
        print(f"Solution uses primitives: {usage}")

    # Try to save as primitive
    if hasattr(primitive_library, 'add_with_generalization'):
        added, reason = primitive_library.add_with_generalization(
            primitive_name, result.best_expr, result.best_fitness
        )
    else:
        added = primitive_library.should_save(result.best_expr, result.best_fitness)
        reason = "Added" if added else "Not saved"
        if added:
            from genetic_gp.tools.library import DerivedPrimitive
            from genetic_gp.core.signatures import behavioral_signature
            sig = behavioral_signature(result.best_expr)
            primitive = DerivedPrimitive(name=primitive_name, expr=result.best_expr, signature=sig)
            primitive_library.add(primitive)

    if reporter and hasattr(reporter, 'on_primitive_consideration'):
        decision = 'accepted' if added else 'rejected'
        if 'Generalized' in reason:
            decision = 'generalized'
        reporter.on_primitive_consideration(result.best_expr, result.best_fitness, decision, reason)
    # Backwards compatibility
    elif reporter and hasattr(reporter, 'on_tool_consideration'):
        decision = 'accepted' if added else 'rejected'
        if 'Generalized' in reason:
            decision = 'generalized'
        reporter.on_tool_consideration(result.best_expr, result.best_fitness, decision, reason)

    if verbose:
        if added:
            print(f"Saved: {reason}")
        else:
            print(f"Not saved: {reason}")

    return result


# Backwards compatibility alias
def evolve_and_save_tool(
    fitness_fn: Callable[[Callable[[int], float]], float],
    tool_library: Any,
    tool_name: str,
    **kwargs,
) -> EvolutionResult:
    """Deprecated: Use evolve_and_save_primitive() instead."""
    return evolve_and_save_primitive(fitness_fn, tool_library, tool_name, **kwargs)


