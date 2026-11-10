"""Design-only regressions: the light option and both prior options coexist."""
from pathlib import Path
from frontend.ui_theme import CLASSIC_CSS, NORUNJA_CSS, get_css


def test_cream_theme_uses_light_contrast_and_stable_hero():
    style = get_css("노른자 크림(추천)")
    assert "--nj-canvas:#F9F9F5" in style
    assert "--nj-ink:#26313A" in style
    assert ".nj-hero" in style
    assert ".nj-overview" in style
    assert ".nj-mini-grid" in style


def test_original_themes_are_still_available():
    assert CLASSIC_CSS in get_css("기존 다크·민트")
    assert NORUNJA_CSS in get_css("노른자 옐로")


def test_light_theme_makes_no_model_changes():
    root=Path(__file__).resolve().parents[2]
    body=(root/"app.py").read_text(encoding="utf-8")
    assert 'theme_choice == "노른자 크림(추천)"' in body
    assert 'display_result = show_result(region)' in body
    assert 'open_scenario(' in body
    assert 'build_map_html(' in body
