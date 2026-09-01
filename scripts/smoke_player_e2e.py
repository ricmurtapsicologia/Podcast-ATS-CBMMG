from __future__ import annotations

import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1365, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    response = page.goto(BASE, wait_until="networkidle")
    assert response and response.ok, response
    page.evaluate("localStorage.setItem('gav:onboard_done_v2','1'); localStorage.removeItem('gav:last_series_v2')")
    page.reload(wait_until="networkidle")

    def exercise(series_id: str, expected: int) -> None:
        button = page.locator(f'button[data-series-id="{series_id}"]')
        assert button.count() == 1
        button.click()
        cards = page.locator("#episodeList .episode-card")
        assert cards.count() == expected, (series_id, cards.count())
        indexes = sorted({0, expected // 2, expected - 1})
        for idx in indexes:
            audio = cards.nth(idx).locator("audio")
            audio.scroll_into_view_if_needed()
            audio.evaluate("el => new Promise((resolve, reject) => { if (el.readyState >= 1) return resolve(); const t=setTimeout(()=>reject(new Error('metadata timeout')),15000); el.addEventListener('loadedmetadata',()=>{clearTimeout(t);resolve();},{once:true}); el.load(); })")
            duration = audio.evaluate("el => el.duration")
            assert duration and duration > 0, (series_id, idx, duration)
            audio.evaluate("el => { el.currentTime = Math.min(1, Math.max(0, el.duration/4)); }")
            audio.evaluate("el => el.play()")
            page.wait_for_timeout(450)
            assert audio.evaluate("el => !el.paused")
            audio.evaluate("el => el.pause()")
            assert audio.evaluate("el => el.paused")
        page.locator("#backToSeries").click()

    exercise("1", 21)
    exercise("2", 14)
    assert not errors, errors

    mobile = browser.new_page(viewport={"width": 390, "height": 844})
    mobile.goto(BASE, wait_until="networkidle")
    mobile.evaluate("localStorage.setItem('gav:onboard_done_v2','1')")
    mobile.reload(wait_until="networkidle")
    mobile.locator('button[data-series-id="1"]').click()
    assert mobile.locator("#episodeList .episode-card").count() == 21
    assert mobile.locator("#libraryPanel").is_visible()
    browser.close()

print("PASS: E2E player desktop/mobile; séries 1/2; metadata; seek; play/pause; console limpa.")
