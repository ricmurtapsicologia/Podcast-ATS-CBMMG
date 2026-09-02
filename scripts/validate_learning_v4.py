from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
index = (ROOT / "index.html").read_text(encoding="utf-8")
app = (ROOT / "app.js").read_text(encoding="utf-8")
psp = (ROOT / "psp.js").read_text(encoding="utf-8")
manifest = (ROOT / "content-manifest.js").read_text(encoding="utf-8")
learning = (ROOT / "learning-v4.css").read_text(encoding="utf-8")
assets_css = (ROOT / "assets-v4.css").read_text(encoding="utf-8")
a11y = (ROOT / "a11y-v4.js").read_text(encoding="utf-8")
cards = json.loads((ROOT / "psp-cards.json").read_text(encoding="utf-8"))

release_match = re.search(r'<meta name="gav-release" content="([^"]+)"', index)
assert release_match, "meta gav-release ausente"
release = release_match.group(1)
assert release == "gav-learning-v4-20260902", release
for path in ("styles.css", "psp.css", "learning-v4.css", "assets-v4.css", "content-manifest.js", "psp.js", "app.js", "a11y-v4.js"):
    assert f'{path}?v={release}' in index, f"asset fora da release única: {path}"

assert manifest.count('assets/audio/serie-1/a1-') == 21
assert manifest.count('assets/audio/serie-2/a2-') == 14
assert 'kind:"psp", status:"available"' in manifest
assert 'assets/img/series-1.jpg' in manifest
assert 'assets/img/series-2.jpg' in manifest
assert 'assets/img/series-3.jpg' in manifest
assert 'assets/img/hero.jpg' in assets_css

assert "const SERIES=" not in app
assert "const AUDIOS=" not in app
assert "enhancePage" not in psp
assert "gav:v4:item:" in app
assert "LEGACY_PROGRESS" in app
assert "completed" in app
assert app.count("<audio") == 1, "Série de áudio deve renderizar um único player"
assert psp.count("<audio") == 1, "PSP deve renderizar um único player"

assert len(cards) == 10
assert "N2" not in index
assert "N3" not in index
assert "Em construção" not in index
assert 'aria-live="polite"' in index and 'id="appStatus"' in index
assert '<section class="container" id="episodes" aria-live=' not in index
assert "prefers-reduced-motion:reduce" in learning
assert "episode-search" in learning
assert "filter-chip" in learning
assert "has-progress" in learning
assert 'role", "progressbar"' in a11y
assert 'aria-valuenow' in a11y

for asset in ("hero.jpg", "series-1.jpg", "series-2.jpg", "series-3.jpg"):
    path = ROOT / "assets" / "img" / asset
    assert path.exists() and path.stat().st_size > 1000, f"asset local ausente: {path}"

print("PASS: gate estrutural GAV v4 — manifesto, release, estado, player único, PSP, acessibilidade e assets locais.")
