"""
TWO-PHASE EVOLUTION WITH PRIMITIVE ACCUMULATION

Evolution in two phases:
1. Find any correct solution (accuracy >= 0.99)
2. Aggressively simplify until target complexity or stuck

Derived primitives are accumulated across problems - later problems can reuse earlier discoveries.

Usage:
    python -m genetic_gp.experiments.simplicity
"""

from typing import Callable

from genetic_gp.core.reporter import get_reporter
from genetic_gp.core.config import get_config, Verbosity
from genetic_gp.evolution.engine import evolve_and_save_primitive
from genetic_gp.tools.library import PrimitiveLibrary
from genetic_gp.problems.math import test_double, test_square, test_sum_to_n, test_cube


def run_primitive_accumulation_demo():
    """Demonstrate primitive accumulation across problems."""
    reporter = get_reporter()
    config = get_config()
    verbose = config.output.verbosity_level >= Verbosity.VERBOSE

    # Shared primitive library across all problems
    primitive_library = PrimitiveLibrary()

    print("=" * 70)
    print("PRIMITIVE ACCUMULATION DEMO")
    print("=" * 70)
    print()
    print("Strategy:")
    print("  1. Solve problem -> aggressively simplify -> save as derived primitive")
    print("  2. Later problems can reuse earlier primitives")
    print("  3. Watch for: primitive usage, generalization, simplification")
    print()

    problems = [
        ("double", "f(n) = 2n", test_double),
        ("square", "f(n) = n²", test_square),
        ("sum_to_n", "f(n) = 1+2+...+n", test_sum_to_n),
        ("cube", "f(n) = n³", test_cube),
    ]

    for primitive_name, problem_name, fitness_fn in problems:
        print("\n" + "=" * 70)
        print(f"PROBLEM: {problem_name}")
        print("=" * 70)

        result = evolve_and_save_primitive(
            fitness_fn,
            primitive_library=primitive_library,
            primitive_name=primitive_name,
            reporter=reporter if verbose else None,
            verbose=True,
            pop_size=60,
            generations=100,
            max_complexity=5,  # Target simple solutions
            simplify_generations=30,  # Spend up to 30 gens simplifying
        )

        if result.solved:
            print(f"\nFinal: {result.best_expr}")
            print(f"Complexity: {result.best_expr.complexity()}")
        else:
            print(f"\nDid not solve (best fitness: {result.best_fitness:.3f})")

    # Summary
    print("\n" + "=" * 70)
    print("PRIMITIVE LIBRARY SUMMARY")
    print("=" * 70)
    primitive_library.print_summary()

    # Save to file for persistence demo
    primitive_library.save("primitives.yaml")
    print("\nSaved to primitives.yaml")


def main():
    """Run the demo."""
    run_primitive_accumulation_demo()

    print("\n" + "=" * 70)
    print("KEY FEATURES")
    print("=" * 70)
    print()
    print("Aggressive simplification:")
    print("  ✓ Continue up to 30 generations after solving")
    print("  ✓ Target complexity of 5 or less")
    print("  ✓ Stop early if no improvement for 10 gens")
    print()
    print("Primitive accumulation:")
    print("  ✓ Save solutions as derived primitives")
    print("  ✓ Generalize patterns (n*2 -> n*k)")
    print("  ✓ Report primitive usage in solutions")
    print("  ✓ Later problems can build on earlier primitives")
    print("  ✓ Persist to YAML for reuse across sessions")
    print()


if __name__ == '__main__':
    main()
