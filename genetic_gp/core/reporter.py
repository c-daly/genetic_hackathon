"""Reporter module for genetic programming progress tracking."""

from __future__ import annotations
import sys
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from genetic_gp.core.config import Verbosity, get_config, Config
from genetic_gp.core.latex import to_latex
from genetic_gp.core.renderer import render_expression, supports_sixel


class Reporter:
    """
    Handles progress reporting for genetic programming runs.

    Uses Rich Console for formatted output and respects verbosity levels.
    """

    def __init__(
        self,
        verbosity: Optional[Verbosity] = None,
        renderer: Optional[str] = None,
        config: Optional[Config] = None
    ):
        """
        Initialize reporter with configuration.

        Args:
            verbosity: Override verbosity level
            renderer: Override renderer type ('auto', 'sixel', 'unicode', 'plain')
            config: Override config object
        """
        self.console = Console()

        if config is None:
            config = get_config()

        self.config = config
        self.verbosity = verbosity if verbosity is not None else config.output.verbosity_level
        self.renderer = renderer if renderer is not None else config.output.renderer

    def on_problem_started(self, problem_name: str, description: str = "") -> None:
        """
        Report when a problem starts.

        Args:
            problem_name: Name of the problem
            description: Optional problem description
        """
        if self.verbosity >= Verbosity.MINIMAL:
            panel = Panel(
                f"[bold]{problem_name}[/bold]\n{description}" if description else f"[bold]{problem_name}[/bold]",
                title="Problem Started",
                border_style="blue"
            )
            self.console.print(panel)

    def on_generation_update(self, generation: int, best_fitness: float) -> None:
        """
        Report generation progress.

        Args:
            generation: Current generation number
            best_fitness: Best fitness in this generation
        """
        if self.verbosity >= Verbosity.VERBOSE:
            self.console.print(f"Generation {generation}: best fitness = {best_fitness:.4f}")

    def on_new_best(self, expr: Any, fitness: float, generation: int) -> None:
        """
        Report when a new best solution is found.

        Args:
            expr: The expression representing the new best
            fitness: Fitness score
            generation: Generation where it was found
        """
        if self.verbosity < Verbosity.NORMAL:
            return

        # Render the expression
        rendered = self._render_expression(expr)

        # Create a table for the details
        table = Table(show_header=False, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        table.add_row("Generation", str(generation))
        table.add_row("Fitness", f"{fitness:.4f}")
        table.add_row("Complexity", str(expr.complexity()))

        self.console.print()
        self.console.print(Panel(
            table,
            title="New Best Solution",
            border_style="green"
        ))

        self._print_expression("Expression", expr, rendered)

    def on_solved(self, expr: Any, fitness: float, generation: int) -> None:
        """
        Report when problem is solved (always shown).

        Args:
            expr: The solution expression
            fitness: Fitness score (should be 1.0 or near)
            generation: Generation where solution was found
        """
        # Always show solved message regardless of verbosity
        rendered = self._render_expression(expr)

        # Create a table for the details
        table = Table(show_header=False, box=None)
        table.add_column("Key", style="cyan")
        table.add_column("Value")

        table.add_row("Generation", str(generation))
        table.add_row("Fitness", f"{fitness:.4f}")
        table.add_row("Complexity", str(expr.complexity()))

        self.console.print()
        self.console.print(Panel(
            table,
            title="SOLVED!",
            border_style="bold green"
        ))

        self._print_expression("Solution", expr, rendered)

    def on_simplified(self, original: Any, simplified: Any) -> None:
        """
        Report when an expression is simplified.

        Args:
            original: Original expression
            simplified: Simplified expression
        """
        if self.verbosity >= Verbosity.NORMAL:
            original_rendered = self._render_expression(original)
            simplified_rendered = self._render_expression(simplified)

            self.console.print()
            self.console.print(Panel(
                f"Original: {original_rendered or original}\n"
                f"Simplified: {simplified_rendered or simplified}",
                title="Expression Simplified",
                border_style="yellow"
            ))

    def on_tool_discovered(self, tool_name: str, signature: str) -> None:
        """
        Report when a new tool is discovered.

        Args:
            tool_name: Name of the discovered tool
            signature: Tool signature
        """
        if self.verbosity >= Verbosity.NORMAL:
            self.console.print()
            self.console.print(Panel(
                f"[bold]{tool_name}[/bold]\n{signature}",
                title="Tool Discovered",
                border_style="magenta"
            ))

    def _print_expression(self, label: str, expr: Any, rendered: Optional[str]) -> None:
        """
        Print expression, handling sixel output specially.

        Sixel sequences must be written directly to stdout to preserve
        escape characters that Rich Console would strip.

        Args:
            label: Label to show before expression (e.g., "Expression", "Solution")
            expr: Expression object
            rendered: Pre-rendered string (may contain sixel)
        """
        if rendered and rendered.startswith('\x1b'):
            # Sixel output - write directly to stdout to preserve escape sequences
            sys.stdout.write(f"{label}: ")
            sys.stdout.write(rendered)
            sys.stdout.write("\n")
            sys.stdout.flush()
        elif rendered:
            self.console.print(f"{label}: {rendered}")
        else:
            self.console.print(f"{label}: {expr}")

    def _render_expression(self, expr: Any) -> Optional[str]:
        """
        Render expression using configured renderer.

        Args:
            expr: Expression to render

        Returns:
            Rendered string or None if plain rendering
        """
        if self.renderer == 'plain':
            return None

        # For other renderers, convert to LaTeX first
        latex = to_latex(expr, pretty=self.config.latex.pretty)

        if self.renderer == 'unicode':
            # Just return the LaTeX as is (could be enhanced)
            return latex

        if self.renderer == 'sixel' or self.renderer == 'auto':
            # Use the full render pipeline
            return render_expression(
                expr,
                renderer=self.renderer,
                font_size=self.config.latex.font_size,
                dpi=self.config.latex.dpi,
                pretty=self.config.latex.pretty
            )

        return None


# Global reporter instance
_reporter: Optional[Reporter] = None


def get_reporter() -> Reporter:
    """Get global reporter instance."""
    global _reporter
    if _reporter is None:
        _reporter = Reporter()
    return _reporter


def reset_reporter() -> None:
    """Reset global reporter (for testing)."""
    global _reporter
    _reporter = None
