"""Tests for shared theme module."""

from __future__ import annotations

from opensim_models.shared.theme import style_axis, theme


class TestThemeFallback:
    """Verify that the theme module provides a usable fallback."""

    def test_theme_is_none_when_plot_theme_unavailable(self):
        # plot_theme is not installed in this environment, so theme should be None
        assert theme is None

    def test_style_axis_callable(self):
        assert callable(style_axis)

    def test_style_axis_noop_on_none(self):
        """Fallback style_axis should accept an axis-like object without error."""
        # Pass a dummy object; the fallback is a no-op
        style_axis(None)
