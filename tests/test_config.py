"""Tests for configuration loading."""

import pytest
import tempfile
from pathlib import Path


class TestConfig:
    """Tests for Config class."""

    def test_default_config_when_no_file(self):
        """Should return defaults when no config file exists."""
        from genetic_gp.core.config import Config, load_config

        config = load_config(Path("/nonexistent/path"))

        assert config.output.verbosity == "normal"
        assert config.output.renderer == "sixel"
        assert config.latex.pretty is True

    def test_load_from_yaml(self):
        """Should load settings from YAML file."""
        from genetic_gp.core.config import load_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".gp_config.yaml"
            config_path.write_text("""
output:
  verbosity: verbose
  renderer: unicode
latex:
  pretty: false
  font_size: 18
""")
            config = load_config(Path(tmpdir))

            assert config.output.verbosity == "verbose"
            assert config.output.renderer == "unicode"
            assert config.latex.pretty is False
            assert config.latex.font_size == 18

    def test_verbosity_levels(self):
        """Verbosity enum should have correct ordering."""
        from genetic_gp.core.config import Verbosity

        assert Verbosity.MINIMAL < Verbosity.NORMAL < Verbosity.VERBOSE
