from genetic_gp.core.expressions import BinOp, Const, Var
from genetic_gp.tools.algorithm import AlgorithmLibrary


def test_algorithm_library_promotes_template():
    library = AlgorithmLibrary(min_occurrences=2, min_fitness=0.0)

    expr1 = BinOp('*', Var('n'), Const(2))
    expr2 = BinOp('*', Var('n'), Const(3))

    assert library.consider(expr1, 1.0) is False
    assert library.consider(expr2, 1.0) is True

    algorithms = library.list_algorithms()
    assert len(algorithms) == 1
    assert algorithms[0].template.describe() == "(n*p0)"
    assert len(algorithms[0].examples) == 2
