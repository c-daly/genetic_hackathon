"""Tests for tools/library.py - Tool storage and operations."""

import pytest
from genetic_gp.core.expressions import Const, Var, BinOp, Sum
from genetic_gp.core.signatures import behavioral_signature
from genetic_gp.tools.library import Tool, ToolLibrary


class TestTool:
    """Tests for the Tool dataclass."""

    def test_create_simple_tool(self, double_expr):
        """Should create a simple tool without parameters."""
        sig = behavioral_signature(double_expr)
        tool = Tool(
            name='double',
            expr=double_expr,
            signature=sig,
        )
        assert tool.name == 'double'
        assert tool.params == []
        assert tool.metadata == {}

    def test_create_parameterized_tool(self):
        """Should create a tool with parameters."""
        # n^k where k is a parameter
        expr = BinOp('^', Var('n'), Var('k'))
        sig = behavioral_signature(expr)  # Default k=0
        tool = Tool(
            name='power',
            expr=expr,
            signature=sig,
            params=['k'],
            metadata={'source': 'test'},
        )
        assert tool.name == 'power'
        assert tool.params == ['k']
        assert tool.metadata['source'] == 'test'

    def test_eval_simple_tool(self, double_expr):
        """Simple tool should evaluate correctly."""
        sig = behavioral_signature(double_expr)
        tool = Tool(name='double', expr=double_expr, signature=sig)

        # eval_with_args for simple tool ignores args
        assert tool.eval_with_args(5, []) == 10
        assert tool.eval_with_args(3, []) == 6

    def test_eval_parameterized_tool(self):
        """Parameterized tool should substitute parameters."""
        # n * k
        expr = BinOp('*', Var('n'), Var('k'))
        sig = behavioral_signature(expr)
        tool = Tool(name='scale', expr=expr, signature=sig, params=['k'])

        # n=5, k=3 -> 5*3 = 15
        assert tool.eval_with_args(5, [3]) == 15
        # n=4, k=2 -> 4*2 = 8
        assert tool.eval_with_args(4, [2]) == 8

    def test_complexity(self, double_expr):
        """Tool complexity should match expression complexity."""
        sig = behavioral_signature(double_expr)
        tool = Tool(name='double', expr=double_expr, signature=sig)
        assert tool.complexity() == double_expr.complexity()


class TestToolLibrary:
    """Tests for ToolLibrary class."""

    def test_empty_library(self, empty_tool_library):
        """New library should be empty."""
        assert len(empty_tool_library) == 0
        assert empty_tool_library.list_tools() == []

    def test_add_tool(self, empty_tool_library, double_expr):
        """Should add a tool to the library."""
        sig = behavioral_signature(double_expr)
        tool = Tool(name='double', expr=double_expr, signature=sig)

        result = empty_tool_library.add(tool)

        assert result is True
        assert len(empty_tool_library) == 1

    def test_add_duplicate_rejected(self, empty_tool_library, double_expr):
        """Should reject duplicate tool names."""
        sig = behavioral_signature(double_expr)
        tool1 = Tool(name='double', expr=double_expr, signature=sig)
        tool2 = Tool(name='double', expr=double_expr, signature=sig)

        empty_tool_library.add(tool1)
        result = empty_tool_library.add(tool2)

        assert result is False
        assert len(empty_tool_library) == 1

    def test_get_by_name(self, tool_library_with_double):
        """Should retrieve tool by name."""
        tool = tool_library_with_double.get('double')
        assert tool is not None
        assert tool.name == 'double'

    def test_get_missing_returns_none(self, empty_tool_library):
        """Should return None for missing tool."""
        assert empty_tool_library.get('nonexistent') is None

    def test_find_by_signature(self, tool_library_with_double, double_expr):
        """Should find tool by matching signature."""
        sig = behavioral_signature(double_expr)
        tool = tool_library_with_double.find_by_signature(sig)
        assert tool is not None
        assert tool.name == 'double'

    def test_find_by_signature_no_match(self, tool_library_with_double, square_expr):
        """Should return None when no signature matches."""
        sig = behavioral_signature(square_expr)
        tool = tool_library_with_double.find_by_signature(sig)
        assert tool is None

    def test_find_by_signature_with_tolerance(self, empty_tool_library, double_expr):
        """Should match signatures within tolerance."""
        sig = behavioral_signature(double_expr)
        tool = Tool(name='double', expr=double_expr, signature=sig)
        empty_tool_library.add(tool)

        # Slightly different signature (within tolerance)
        slightly_off = tuple(v + 0.005 for v in sig)
        found = empty_tool_library.find_by_signature(slightly_off, tolerance=0.01)
        assert found is not None

    def test_list_tools(self, empty_tool_library, double_expr, square_expr):
        """Should list all tools."""
        sig1 = behavioral_signature(double_expr)
        sig2 = behavioral_signature(square_expr)

        empty_tool_library.add(Tool(name='double', expr=double_expr, signature=sig1))
        empty_tool_library.add(Tool(name='square', expr=square_expr, signature=sig2))

        tools = empty_tool_library.list_tools()
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert names == {'double', 'square'}

    def test_iteration(self, tool_library_with_double):
        """Should be iterable."""
        tools = list(tool_library_with_double)
        assert len(tools) == 1
        assert tools[0].name == 'double'


class TestNoveltyDetection:
    """Tests for novelty detection in ToolLibrary."""

    def test_empty_library_is_novel(self, empty_tool_library, double_expr):
        """Everything is novel in an empty library."""
        assert empty_tool_library.is_novel(double_expr)

    def test_same_expression_not_novel(self, tool_library_with_double, double_expr):
        """Same expression should not be novel."""
        assert not tool_library_with_double.is_novel(double_expr)

    def test_different_expression_is_novel(self, tool_library_with_double, square_expr):
        """Different expression should be novel."""
        assert tool_library_with_double.is_novel(square_expr)

    def test_similar_expression_not_novel(self, tool_library_with_double):
        """Expression with similar signature should not be novel."""
        # n + n is equivalent to 2*n
        n_plus_n = BinOp('+', Var('n'), Var('n'))
        assert not tool_library_with_double.is_novel(n_plus_n)

    def test_novelty_threshold(self, tool_library_with_double):
        """Should respect novelty threshold."""
        # With very low threshold, most things are novel
        expr = BinOp('*', Const(2.1), Var('n'))  # Almost 2*n
        # With low threshold (0.1), similar expressions are NOT novel
        assert not tool_library_with_double.is_novel(expr, threshold=0.1)


class TestTrivialDetection:
    """Tests for trivial expression detection."""

    def test_const_is_trivial(self, empty_tool_library):
        """Constants are trivial."""
        assert empty_tool_library.is_trivial(Const(5))

    def test_var_is_trivial(self, empty_tool_library):
        """Variables are trivial."""
        assert empty_tool_library.is_trivial(Var('n'))

    def test_simple_binop_is_trivial(self, empty_tool_library):
        """Simple binary ops with only terminals are trivial.

        We don't want to save n*2, n*3, n*4 as separate tools.
        Instead, these should be generalized to patterns like n*k.
        """
        # n * 2
        expr = BinOp('*', Var('n'), Const(2))
        assert empty_tool_library.is_trivial(expr)

        # n + n
        expr = BinOp('+', Var('n'), Var('n'))
        assert empty_tool_library.is_trivial(expr)

    def test_nested_binop_not_trivial(self, empty_tool_library):
        """Nested binary ops are not trivial."""
        # (n + 1) * n
        inner = BinOp('+', Var('n'), Const(1))
        expr = BinOp('*', inner, Var('n'))
        assert not empty_tool_library.is_trivial(expr)

    def test_sum_not_trivial(self, empty_tool_library, sum_1_to_n):
        """Sum expressions are not trivial."""
        assert not empty_tool_library.is_trivial(sum_1_to_n)


class TestShouldSave:
    """Tests for should_save decision logic."""

    def test_low_fitness_not_saved(self, empty_tool_library, sum_1_to_n):
        """Low fitness expressions should not be saved."""
        assert not empty_tool_library.should_save(sum_1_to_n, fitness=0.5)

    def test_trivial_not_saved(self, empty_tool_library, double_expr):
        """Trivial expressions should not be saved even with high fitness."""
        # double_expr is n*2 which is trivial (simple binop with terminals)
        assert not empty_tool_library.should_save(double_expr, fitness=1.0)

    def test_non_novel_not_saved(self, tool_library_with_double, sum_1_to_n):
        """Non-novel expressions should not be saved."""
        # Add sum_1_to_n first
        sig = behavioral_signature(sum_1_to_n)
        tool_library_with_double.add(
            Tool(name='sum_to_n', expr=sum_1_to_n, signature=sig)
        )
        # Same expression should not be saved again
        assert not tool_library_with_double.should_save(sum_1_to_n, fitness=1.0)

    def test_good_expression_saved(self, empty_tool_library, sum_1_to_n):
        """Good, novel, non-trivial expression should be saved."""
        assert empty_tool_library.should_save(sum_1_to_n, fitness=1.0)


class TestToolCallIntegration:
    """Integration tests for ToolCall with ToolLibrary."""

    def test_tool_call_evaluation(self, tool_library_with_double):
        """ToolCall should evaluate using the library."""
        from genetic_gp.core.expressions import ToolCall

        # Call the double tool
        call = ToolCall('double', [], tool_library_with_double)

        # Should double the input
        result = call.eval({'n': 5})
        assert result == 10

    def test_tool_call_missing_tool(self, empty_tool_library):
        """ToolCall with missing tool should return 0."""
        from genetic_gp.core.expressions import ToolCall

        call = ToolCall('nonexistent', [], empty_tool_library)
        result = call.eval({'n': 5})
        assert result == 0

    def test_tool_call_complexity(self, tool_library_with_double):
        """ToolCall complexity should be base + args."""
        from genetic_gp.core.expressions import ToolCall

        # No args: complexity = 2
        call = ToolCall('double', [], tool_library_with_double)
        assert call.complexity() == 2

        # With arg: complexity = 2 + arg_complexity
        call_with_arg = ToolCall('double', [Const(5)], tool_library_with_double)
        assert call_with_arg.complexity() == 3  # 2 + 1
