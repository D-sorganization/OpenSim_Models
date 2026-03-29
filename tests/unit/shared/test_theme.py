"""Tests for shared theme module."""

from __future__ import annotations

import importlib
import sys
from unittest.mock import MagicMock

from opensim_models.shared import theme as theme_module


class TestThemeFallback:
    """Verify that the theme module provides a usable fallback."""

    def test_theme_is_none_when_plot_theme_unavailable(self, monkeypatch):
        # Ensure plot_theme is not in sys.modules
        monkeypatch.delitem(sys.modules, "plot_theme", raising=False)
        monkeypatch.delitem(sys.modules, "plot_theme.integration", raising=False)
        monkeypatch.delitem(sys.modules, "plot_theme.themes", raising=False)

        importlib.reload(theme_module)
        assert theme_module.theme is None

    def test_style_axis_callable(self):
        assert callable(theme_module.style_axis)

    def test_style_axis_noop_on_none(self):
        """Fallback style_axis should accept an axis-like object without error."""
        importlib.reload(theme_module)
        theme_module.style_axis(None)


class TestThemeIntegration:
    """Verify behavior when plot_theme is available."""

    def test_theme_loaded_when_available(self, monkeypatch):
        mock_integration = MagicMock()
        mock_themes = MagicMock()
        mock_themes.DEFAULT_THEME = "default"

        mock_theme_obj = MagicMock()
        mock_theme_obj.name = "mock_theme"
        mock_themes.get_theme.return_value = mock_theme_obj

        monkeypatch.setitem(sys.modules, "plot_theme", MagicMock())
        monkeypatch.setitem(sys.modules, "plot_theme.integration", mock_integration)
        monkeypatch.setitem(sys.modules, "plot_theme.themes", mock_themes)

        importlib.reload(theme_module)

        assert theme_module.theme is not None
        assert theme_module.theme.name == "mock_theme"

        ax = MagicMock()
        theme_module.style_axis(ax)
        mock_integration.style_axis.assert_called_once_with(ax)
