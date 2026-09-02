from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"
AXE = Path("node_modules/axe-core/axe.min.js")
assert AXE.exists(), "axe-core não instalado"


def audit(page, label: str) -> None:
    page.add_script_tag(path=str(AXE))
    result = page.evaluate(
        """async () => await axe.run(document, {
          runOnly: { type: 'tag', values: ['wcag2a','wcag2aa','wcag21aa','wcag22aa'] },
          resultTypes: ['violations']
        })"""
    )
    blocking = [v for v in result["violations"] if v.get("impact") in {"serious", "critical"}]
    if blocking:
        compact = [
            {
                "id": v["id"],
                "impact": v.get("impact"),
                "description": v.get("description"),
                "nodes": [n.get("target") for n in v.get("nodes", [])[:8]],
            }
            for v in blocking
        ]
        raise AssertionError(f"A11Y {label}: {json.dumps(compact, ensure_ascii=False, indent=2)}")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1365, "height": 900})
    page = context.new_page()
    page.goto(BASE, wait_until="networkidle")
    page.evaluate("localStorage.setItem('gav:v4:onboard-done','1')")
    page.reload(wait_until="networkidle")
    audit(page, "home")

    page.locator('button[data-series-id="1"]').click()
    page.wait_for_selector("#episodeIndex .episode-row")
    audit(page, "serie-1")

    page.locator("#backToSeries").click()
    page.locator('button[data-series-id="3"]').click()
    page.wait_for_selector("#pspGrid .psp-card")
    page.locator("#pspGrid .psp-card").nth(0).locator(".psp-card-toggle").click()
    audit(page, "serie-3")

    mobile = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce").new_page()
    mobile.goto(BASE, wait_until="networkidle")
    mobile.evaluate("localStorage.setItem('gav:v4:onboard-done','1')")
    mobile.reload(wait_until="networkidle")
    mobile.add_script_tag(path=str(AXE))
    result = mobile.evaluate("async () => await axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']},resultTypes:['violations']})")
    blocking = [v for v in result["violations"] if v.get("impact") in {"serious", "critical"}]
    assert not blocking, [(v["id"], v.get("impact")) for v in blocking]
    browser.close()

print("PASS: axe-core sem violações serious/critical nos estados principais desktop/mobile.")
