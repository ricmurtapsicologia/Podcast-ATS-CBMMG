from __future__ import annotations

import json
import sys
import time
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765/"


def auth_payload() -> str:
    now = int(time.time() * 1000)
    return json.dumps({
        "authenticated": True,
        "createdAt": now,
        "expiresAt": now + 8 * 60 * 60 * 1000,
        "version": 3,
    })


def authorize(page, url: str = BASE, onboard_done: bool = True) -> None:
    page.goto(url, wait_until="networkidle")
    page.wait_for_selector('#catsAuthGate[data-gav-branded="true"]')
    page.evaluate("payload => sessionStorage.setItem('gav_auth_v1', payload)", auth_payload())
    if onboard_done:
        page.evaluate("localStorage.setItem('gav:v4:onboard-done','1')")
    page.reload(wait_until="networkidle")
    page.wait_for_selector('#catsAuthGate[data-gav-branded="true"]', state="attached")
    assert page.locator("#catsAuthGate").is_hidden(), "gate deveria estar liberado com sessão GAV válida"


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    # 1) Gate próprio: bloqueado por padrão, branding da ampulheta, acesso automático e sem assets visuais externos.
    context = browser.new_context(viewport={"width": 1365, "height": 900})
    page = context.new_page()
    errors: list[str] = []
    external_visual_requests: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("request", lambda req: external_visual_requests.append(req.url) if ("pinimg.com" in req.url or "images.pexels.com" in req.url) else None)

    page.goto(BASE, wait_until="networkidle")
    page.wait_for_selector('#catsAuthGate[data-gav-branded="true"]')
    gate = page.locator("#catsAuthGate")
    assert gate.is_visible(), "acesso deve iniciar bloqueado"
    assert gate.get_attribute("data-gav-branded") == "true"
    assert "Girando a Ampulheta da Vida" in (gate.locator("#catsAuthTitle").text_content() or "")
    assert (gate.locator(".cats-auth-eyebrow").text_content() or "").strip() == "Acesso à biblioteca"
    assert gate.locator("#catsAuthSubmit").is_hidden(), "botão de entrada não deve aparecer"
    assert "validado automaticamente" in (gate.locator("#catsAuthHelp").text_content() or "")
    semantic_gate_text = gate.text_content() or ""
    assert "Atendimento a Tentativas de Suicídio" not in semantic_gate_text
    hero_bg = page.locator("#catsAuthGate .cats-auth-hero").evaluate("el => getComputedStyle(el).backgroundImage")
    assert "assets/img/hero.jpg" in hero_bg or "hero.jpg" in hero_bg, hero_bg
    assert not external_visual_requests, external_visual_requests

    # Uma matrícula de 7 dígitos dispara validação automaticamente, sem clique.
    page.locator("#catsAuthInput").fill("0000000")
    page.wait_for_function("() => document.querySelector('#catsAuthMessage')?.classList.contains('is-visible')", timeout=5000)
    assert "Credencial não localizada" in page.locator("#catsAuthMessage").inner_text()
    page.evaluate("localStorage.removeItem('gav_login_attempts_v1')")
    page.locator("#catsAuthInput").fill("")

    # 2) Isolamento: uma sessão física do Curso ATS não libera o podcast.
    ats_context = browser.new_context(viewport={"width": 1100, "height": 760})
    payload = auth_payload().replace("\\", "\\\\").replace("'", "\\'")
    ats_context.add_init_script(f"sessionStorage.setItem('curso_ats_auth_v3','{payload}')")
    ats_page = ats_context.new_page()
    ats_page.goto(BASE, wait_until="networkidle")
    ats_page.wait_for_selector('#catsAuthGate[data-gav-branded="true"]')
    assert ats_page.locator("#catsAuthGate").is_visible(), "sessão do Curso ATS não pode liberar o podcast"
    ats_context.close()

    # 3) Sessão própria libera apenas a experiência GAV.
    authorize(page)

    # Home/branding/CTA: três séries, assets locais e ação pedagógica primária.
    assert page.locator(".series-card").count() == 3
    assert page.locator("#heroPrimary").inner_text().strip() == "Explorar as séries"
    image_sources = page.locator(".series-card img").evaluate_all("els => els.map(el => el.getAttribute('src'))")
    assert image_sources == ["assets/img/series-1.jpg", "assets/img/series-2.jpg", "assets/img/series-3.jpg"], image_sources

    # Série 1: lista compacta, player único, busca, progresso por ID estável.
    page.locator('button[data-series-id="1"]').click()
    assert page.locator("#episodeIndex .episode-row").count() == 21
    assert page.locator("#episodeList audio").count() == 1
    assert page.locator("#activeEpisodeTitle").inner_text().startswith("A1 001")

    search = page.locator("#episodeSearch")
    search.fill("Poder de Ouvir")
    assert page.locator("#episodeIndex .episode-row").count() == 1
    assert "A1 005" in page.locator("#episodeIndex .episode-row").inner_text()
    search.fill("")
    assert page.locator("#episodeIndex .episode-row").count() == 21

    page.locator('button.episode-select[data-item-id="a1-005"]').click()
    audio = page.locator("#seriesAudio")
    audio.evaluate("el => new Promise((resolve, reject) => { if (el.readyState >= 1) return resolve(); const t=setTimeout(()=>reject(new Error('metadata timeout')),15000); el.addEventListener('loadedmetadata',()=>{clearTimeout(t);resolve();},{once:true}); el.load(); })")
    duration = audio.evaluate("el => el.duration")
    assert duration and duration > 0
    audio.evaluate("el => { el.currentTime = Math.min(2, Math.max(1, el.duration / 8)); }")
    audio.evaluate("el => el.play()")
    page.wait_for_timeout(450)
    audio.evaluate("el => el.pause()")
    state = json.loads(page.evaluate("localStorage.getItem('gav:v4:item:a1-005')"))
    assert state["position"] > 0, state
    assert state["completed"] is False
    assert "a1-005" in page.evaluate("localStorage.getItem('gav:v4:last-item')")

    audio.evaluate("el => el.dispatchEvent(new Event('ended'))")
    page.wait_for_timeout(80)
    state = json.loads(page.evaluate("localStorage.getItem('gav:v4:item:a1-005')"))
    assert state["completed"] is True, state
    page.locator('[data-filter="completed"]').click()
    assert page.locator("#episodeIndex .episode-row").count() >= 1
    assert "A1 005" in page.locator("#episodeIndex").inner_text()

    # Deep link preservado sob autenticação própria.
    deep = context.new_page()
    authorize(deep, BASE + "#serie-1/a1-007")
    assert deep.locator("#libraryPanel").is_visible()
    assert deep.locator("#episodeList audio").count() == 1
    assert deep.locator("#activeEpisodeTitle").inner_text().startswith("A1 007")
    assert deep.evaluate("localStorage.getItem('gav:v4:item:a1-005')") is not None

    # Série 3: 10 cards, player único e conteúdo preservado.
    deep.locator("#backToSeries").click()
    deep.locator('button[data-series-id="3"]').click()
    deep.wait_for_selector("#pspGrid .psp-card")
    assert deep.locator("#pspGrid .psp-card").count() == 10
    assert deep.locator("#episodeList audio").count() == 1
    visible_text = deep.locator("#episodeList").inner_text()
    for forbidden in ("N2", "N3", "Em construção"):
        assert forbidden not in visible_text, (forbidden, visible_text[:500])
    deep.locator("#pspGrid .psp-card").nth(0).locator(".psp-card-toggle").click()
    assert deep.locator("#pspGrid .psp-card").nth(0).locator(".psp-card-details").is_visible()
    deep.locator("#pspGrid .psp-card").nth(0).locator(".psp-listen").click()
    psp_audio = deep.locator("#pspSharedAudio")
    psp_audio.evaluate("el => new Promise((resolve, reject) => { if (el.readyState >= 1) return resolve(); const t=setTimeout(()=>reject(new Error('psp metadata timeout')),15000); el.addEventListener('loadedmetadata',()=>{clearTimeout(t);resolve();},{once:true}); el.load(); })")
    assert psp_audio.evaluate("el => el.duration") > 0

    psp_deep = context.new_page()
    authorize(psp_deep, BASE + "#serie-3/psp-03")
    psp_deep.wait_for_selector('[data-psp-id="psp-03"].is-open')
    assert psp_deep.locator('[data-psp-id="psp-03"] .psp-card-details').is_visible()
    assert psp_deep.locator("#episodeList audio").count() == 1

    # Onboarding continua funcional após autenticação.
    fresh_context = browser.new_context(viewport={"width": 1000, "height": 760})
    fresh = fresh_context.new_page()
    authorize(fresh, onboard_done=False)
    assert fresh.locator("#onboarding").get_attribute("aria-hidden") == "false"
    fresh.locator("#onboardStart").focus()
    fresh.keyboard.press("Shift+Tab")
    assert fresh.evaluate("document.activeElement.id") == "onboardSkip"
    fresh.keyboard.press("Tab")
    assert fresh.evaluate("document.activeElement.id") == "onboardStart"
    fresh.keyboard.press("Escape")
    assert fresh.locator("#onboarding").get_attribute("aria-hidden") == "true"
    assert fresh.evaluate("localStorage.getItem('gav:v4:onboard-done')") == "1"
    fresh_context.close()

    # Mobile + reduced motion.
    reduced_context = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    reduced = reduced_context.new_page()
    authorize(reduced)
    assert reduced.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == "auto"
    reduced.locator('button[data-series-id="1"]').click()
    assert reduced.locator("#episodeList audio").count() == 1
    assert reduced.locator("#episodeIndex .episode-row").count() == 21
    reduced_context.close()

    assert not errors, errors
    browser.close()

print("PASS: GAV — acesso automático sem botão, sessão isolada, branding, players, progresso, deep links, PSP, onboarding, mobile e reduced-motion.")
