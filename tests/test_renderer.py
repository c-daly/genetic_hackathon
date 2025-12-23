"""Tests for expression rendering."""

import pytest
from genetic_gp.core.expressions import Const, Var, BinOp, Sum


class TestLatexRenderer:
    """Tests for LaTeX to image rendering."""

    def test_render_simple_expression(self):
        """Should render without error."""
        from genetic_gp.core.renderer import render_latex_to_png

        png_bytes = render_latex_to_png("2n", dpi=100)

        assert png_bytes is not None
        assert len(png_bytes) > 0
        # PNG magic bytes
        assert png_bytes[:8] == b'\x89PNG\r\n\x1a\n'

    def test_render_complex_expression(self):
        """Should render sum notation."""
        from genetic_gp.core.renderer import render_latex_to_png

        latex = r"\sum_{i=1}^{n} i"
        png_bytes = render_latex_to_png(latex, dpi=100)

        assert png_bytes is not None
        assert len(png_bytes) > 0


class TestSixelOutput:
    """Tests for sixel encoding."""

    def test_png_to_sixel(self):
        """Should convert PNG to sixel string."""
        from genetic_gp.core.renderer import render_latex_to_png, png_to_sixel

        png_bytes = render_latex_to_png("x", dpi=72)
        sixel = png_to_sixel(png_bytes)

        # Sixel starts with escape sequence
        assert sixel.startswith('\x1bP') or sixel.startswith('\033P')
        # Sixel ends with ST (string terminator)
        assert sixel.endswith('\x1b\\') or sixel.endswith('\033\\')


class TestRendererFallback:
    """Tests for fallback rendering."""

    def test_unicode_fallback(self):
        """Should produce Unicode output when sixel unavailable."""
        from genetic_gp.core.renderer import render_unicode

        expr = Sum("i", Const(1), Var("n"), Var("i"))
        result = render_unicode(expr)

        # Should contain sigma-like character
        assert "Σ" in result or "sum" in result.lower()
