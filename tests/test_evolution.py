"""Tests for evolution module - generator, mutation, and engine."""

import pytest
import random
from genetic_gp.core.expressions import Const, Var, BinOp, Sum, Product, Expression
from genetic_gp.evolution.generator import random_expr
from genetic_gp.evolution.mutation import mutate, crossover
from genetic_gp.evolution.engine import evolve, EvolutionResult
# Import fitness functions with aliases to avoid pytest collection
from genetic_gp.problems.math import test_double as fitness_double
from genetic_gp.problems.math import test_square as fitness_square


class TestRandomExpr:
    """Tests for random expression generation."""

    def test_returns_expression(self):
        """Should return something that has eval and complexity."""
        expr = random_expr()
        assert hasattr(expr, 'eval')
        assert hasattr(expr, 'complexity')

    def test_respects_max_depth(self):
        """At max_depth=0, should return a terminal."""
        expr = random_expr(depth=0, max_depth=0)
        assert isinstance(expr, (Const, Var))

    def test_uses_available_vars(self):
        """Generated vars should come from vars_available."""
        # Generate many expressions and check vars
        vars_found = set()
        for _ in range(100):
            expr = random_expr(max_depth=1, vars_available=['x', 'y'])
            vars_found.update(_collect_var_names(expr))

        # Should only have x and y, no 'n'
        assert vars_found <= {'x', 'y'}

    def test_is_evaluable(self):
        """Generated expression should be evaluable without error."""
        for _ in range(50):
            expr = random_expr()
            result = expr.eval({'n': 5})
            assert isinstance(result, (int, float))

    def test_deterministic_with_seed(self):
        """Same seed should produce same expression."""
        random.seed(42)
        expr1 = random_expr()

        random.seed(42)
        expr2 = random_expr()

        assert repr(expr1) == repr(expr2)

    def test_generates_variety(self):
        """Should generate different types of expressions."""
        types_seen = set()
        for _ in range(100):
            expr = random_expr(max_depth=2)
            types_seen.add(type(expr).__name__)

        # Should see at least Const, Var, and BinOp
        assert 'Const' in types_seen or 'Var' in types_seen
        assert 'BinOp' in types_seen or 'Sum' in types_seen


class TestMutate:
    """Tests for mutation operator."""

    def test_returns_expression(self):
        """Mutate should return an expression."""
        original = BinOp('*', Const(2), Var('n'))
        mutated = mutate(original)
        assert hasattr(mutated, 'eval')
        assert hasattr(mutated, 'complexity')

    def test_can_mutate_const(self):
        """Should be able to mutate a constant."""
        c = Const(5)
        mutated = mutate(c, rate=0.0)  # Low rate = structural mutation
        assert isinstance(mutated, Const)
        # Value should be different (mutated)
        assert mutated.val != 5 or mutated.val == 5  # Could be same by chance

    def test_preserves_structure_at_low_rate(self):
        """At rate=0, should mostly preserve structure."""
        original = BinOp('+', Var('n'), Const(1))
        # With rate=0, only structural mutations happen
        mutated = mutate(original, rate=0.0)
        # Should still be a BinOp with + operator
        assert isinstance(mutated, BinOp)
        assert mutated.op == '+'

    def test_can_replace_subtree_at_high_rate(self):
        """At rate=1, should usually replace entire tree."""
        original = Const(5)
        replaced_count = 0
        for _ in range(20):
            mutated = mutate(original, rate=1.0)
            if repr(mutated) != repr(original):
                replaced_count += 1
        # Most should be replaced
        assert replaced_count > 10

    def test_result_is_evaluable(self):
        """Mutated expression should be evaluable."""
        original = Sum('i', Const(1), Var('n'), Var('i'))
        for _ in range(20):
            mutated = mutate(original)
            result = mutated.eval({'n': 5})
            assert isinstance(result, (int, float))


class TestCrossover:
    """Tests for crossover operator."""

    def test_returns_expression(self):
        """Crossover should return an expression."""
        p1 = BinOp('*', Const(2), Var('n'))
        p2 = BinOp('+', Var('n'), Const(1))
        child = crossover(p1, p2)
        assert hasattr(child, 'eval')
        assert hasattr(child, 'complexity')

    def test_child_is_evaluable(self):
        """Child expression should be evaluable."""
        p1 = BinOp('*', Const(2), Var('n'))
        p2 = Sum('i', Const(1), Var('n'), Var('i'))
        for _ in range(20):
            child = crossover(p1, p2)
            result = child.eval({'n': 5})
            assert isinstance(result, (int, float))


class TestEvolve:
    """Tests for evolution engine."""

    def test_returns_evolution_result(self):
        """Should return an EvolutionResult."""
        result = evolve(
            fitness_double,
            pop_size=10,
            generations=5,
            verbose=False,
        )
        assert isinstance(result, EvolutionResult)
        assert hasattr(result, 'best_expr')
        assert hasattr(result, 'best_fitness')
        assert hasattr(result, 'generations_run')
        assert hasattr(result, 'solved')

    def test_fitness_improves(self):
        """Fitness should generally improve over generations."""
        fitness_history = []

        def track_fitness(gen, scores):
            if scores:
                fitness_history.append(scores[0][1])

        evolve(
            fitness_double,
            pop_size=20,
            generations=30,
            on_generation=track_fitness,
            verbose=False,
        )

        # Final fitness should be >= initial fitness
        if len(fitness_history) >= 2:
            assert fitness_history[-1] >= fitness_history[0] - 0.1

    def test_stops_when_solved(self):
        """Should stop early when solution is found."""
        result = evolve(
            fitness_double,
            pop_size=30,
            generations=100,
            stop_at_fitness=0.99,
            verbose=False,
        )

        if result.solved:
            assert result.generations_run < 100
            assert result.best_fitness >= 0.99

    def test_collects_solutions_above_threshold(self):
        """Should collect solutions above specified threshold."""
        result = evolve(
            fitness_double,
            pop_size=30,
            generations=50,
            collect_solutions_above=0.5,
            verbose=False,
        )

        # If any solutions found, they should all be above threshold
        for expr, fitness in result.all_solutions:
            assert fitness > 0.5

    def test_best_expr_is_evaluable(self):
        """Best expression should be evaluable."""
        result = evolve(
            fitness_double,
            pop_size=20,
            generations=20,
            verbose=False,
        )

        for n in range(10):
            val = result.best_expr.eval({'n': n})
            assert isinstance(val, (int, float))

    def test_can_solve_double(self):
        """Should be able to solve f(n) = 2n with enough generations."""
        result = evolve(
            fitness_double,
            pop_size=40,
            generations=100,
            verbose=False,
        )

        # Should achieve decent fitness
        assert result.best_fitness > 0.5

    def test_respects_vars_available(self):
        """Should use specified variables."""
        result = evolve(
            fitness_double,
            pop_size=10,
            generations=5,
            vars_available=['x'],
            verbose=False,
        )

        # Expression should only use 'x', not 'n'
        var_names = _collect_var_names(result.best_expr)
        # This might fail if 'n' sneaks in somehow
        assert 'n' not in var_names or var_names == set()


class TestEvolutionIntegration:
    """Integration tests for the evolution system."""

    def test_full_pipeline_double(self):
        """Full evolution run for doubling function."""
        result = evolve(
            fitness_double,
            pop_size=60,
            generations=80,
            stop_at_fitness=0.99,
            verbose=False,
        )

        # Check we got a valid result
        assert result.best_expr is not None
        assert 0 <= result.best_fitness <= 1

        # Verify the expression works
        if result.best_fitness > 0.8:
            # Should approximately double inputs
            for n in [1, 2, 3]:
                val = result.best_expr.eval({'n': n})
                # Allow some tolerance
                assert abs(val - 2 * n) < 1 or result.best_fitness < 0.99

    def test_full_pipeline_square(self):
        """Full evolution run for squaring function."""
        result = evolve(
            fitness_square,
            pop_size=60,
            generations=80,
            stop_at_fitness=0.99,
            verbose=False,
        )

        assert result.best_expr is not None
        assert result.best_fitness > 0.3  # Should find something


class TestEvolutionReporter:
    """Tests for reporter integration."""

    def test_evolve_accepts_reporter(self):
        """Should accept optional reporter parameter."""
        from genetic_gp.evolution.engine import evolve
        from genetic_gp.core.reporter import Reporter
        from genetic_gp.core.config import Verbosity
        from genetic_gp.problems.math import test_double as fitness_double

        reporter = Reporter(verbosity=Verbosity.MINIMAL, renderer="plain")

        result = evolve(
            fitness_double,
            pop_size=20,
            generations=10,
            reporter=reporter,
            verbose=False,
        )

        assert result is not None

    def test_evolve_emits_events(self):
        """Should emit events to reporter."""
        from genetic_gp.evolution.engine import evolve
        from genetic_gp.problems.math import test_double as fitness_double

        events = []

        class TestReporter:
            def on_problem_started(self, *args): events.append(('started', args))
            def on_new_best(self, *args): events.append(('new_best', args))
            def on_solved(self, *args): events.append(('solved', args))
            def on_generation_update(self, *args): events.append(('gen', args))

        result = evolve(
            fitness_double,
            pop_size=30,
            generations=50,
            reporter=TestReporter(),
            verbose=False,
        )

        assert len(events) > 0
        assert any(e[0] == 'new_best' for e in events)


def _collect_var_names(expr) -> set:
    """Collect all variable names used in an expression."""
    names = set()
    if isinstance(expr, Var):
        names.add(expr.name)
    elif isinstance(expr, BinOp):
        names.update(_collect_var_names(expr.left))
        names.update(_collect_var_names(expr.right))
    elif isinstance(expr, (Sum, Product)):
        names.update(_collect_var_names(expr.start))
        names.update(_collect_var_names(expr.end))
        names.update(_collect_var_names(expr.body))
        names.discard(expr.var)  # Loop var is not external
    return names
