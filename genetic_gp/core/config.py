"""Configuration loading for genetic programming framework."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

import yaml


class Verbosity(IntEnum):
    """Verbosity levels for reporting."""
    MINIMAL = 1
    NORMAL = 2
    VERBOSE = 3

    @classmethod
    def from_str(cls, s: str) -> "Verbosity":
        return cls[s.upper()]


@dataclass
class OutputConfig:
    """Output configuration."""
    verbosity: str = "normal"
    renderer: str = "sixel"
    fallback: str = "unicode"

    @property
    def verbosity_level(self) -> Verbosity:
        return Verbosity.from_str(self.verbosity)


@dataclass
class LatexConfig:
    """LaTeX rendering configuration."""
    pretty: bool = True
    font_size: int = 14
    dpi: int = 150


@dataclass
class Config:
    """Main configuration container."""
    output: OutputConfig = field(default_factory=OutputConfig)
    latex: LatexConfig = field(default_factory=LatexConfig)
    report_interval: int = 10


def load_config(search_path: Path | None = None) -> Config:
    """Load configuration from .gp_config.yaml."""
    if search_path is None:
        search_path = Path.cwd()

    config_file = search_path / ".gp_config.yaml"

    if not config_file.exists():
        return Config()

    with open(config_file) as f:
        data = yaml.safe_load(f) or {}

    output_data = data.get("output", {})
    latex_data = data.get("latex", {})

    return Config(
        output=OutputConfig(**output_data),
        latex=LatexConfig(**latex_data),
        report_interval=data.get("report_interval", 10),
    )


_config: Config | None = None


def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reset_config() -> None:
    """Reset global config (for testing)."""
    global _config
    _config = None
