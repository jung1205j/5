from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_leaflet_tiles_do_not_require_carto_key():
    source = (ROOT / 'animated_map.py').read_text(encoding='utf-8')
    assert 'https://tile.openstreetmap.org/{z}/{x}/{y}.png' in source
    assert 'basemaps.cartocdn.com' not in source
    assert 'OpenStreetMap' in source

def test_pydeck_fallback_uses_keyless_style():
    source = (ROOT.parent / 'app.py').read_text(encoding='utf-8')
    assert 'https://tiles.openfreemap.org/styles/dark' in source
    assert 'basemaps.cartocdn.com' not in source
