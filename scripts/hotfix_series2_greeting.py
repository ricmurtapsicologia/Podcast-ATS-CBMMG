from __future__ import annotations

import asyncio
import json
import re
import shutil

import remaster_series2_n3 as n3

CANONICAL_GREETING = "Olá, caros abordadores."
GREETING_RE = re.compile(r"\bol[áa]\s*,?\s+pessoal\b[,.!?…]*", flags=re.I)
MALFORMED_CANONICAL_RE = re.compile(r"Olá, caros abordadores\.\s*[,.;:]+", flags=re.I)
TARGET_EPISODES = (0, 1, 2, 3, 10, 11, 12, 13)
VERSION = "n3-cast-20260901g"
REPORT_PATH = n3.ROOT / "reports" / "series2-greeting-hotfix.json"
QUALITY_PATH = n3.OUT / "quality-n3.json"


def patch_sources() -> list[str]:
    changed: list[str] = []
    for number in TARGET_EPISODES:
        path = n3.ROTEIROS / f"a2-{number:03d}.txt"
        original = path.read_text(encoding="utf-8")
        updated = GREETING_RE.sub(CANONICAL_GREETING, original)
        updated = MALFORMED_CANONICAL_RE.sub(CANONICAL_GREETING, updated)
        if CANONICAL_GREETING not in updated:
            raise RuntimeError(f"Saudação canônica ausente em {path.name}")
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed.append(path.as_posix())

    residual = []
    malformed = []
    for path in sorted(n3.ROTEIROS.glob("a2-*.txt")):
        text = path.read_text(encoding="utf-8")
        if GREETING_RE.search(text):
            residual.append(path.name)
        if MALFORMED_CANONICAL_RE.search(text) or "abordadores.," in text:
            malformed.append(path.name)
    if residual:
        raise RuntimeError(f"Ainda há saudação não canônica na Série 2: {residual}")
    if malformed:
        raise RuntimeError(f"Pontuação inválida após saudação canônica: {malformed}")
    return changed


def patch_target_app_urls() -> None:
    app = n3.APP.read_text(encoding="utf-8")
    for number in TARGET_EPISODES:
        pattern = re.compile(
            rf'(assets/audio/serie-2/a2-{number:03d}-n3\.mp3\?v=)[^"\s]+'
        )
        app, count = pattern.subn(rf"\g<1>{VERSION}", app, count=1)
        if count != 1:
            raise RuntimeError(f"URL do A2-{number:03d} não localizada em app.js")
    n3.APP.write_text(app, encoding="utf-8")


def update_quality(results: list[dict], pool: list[dict], cast: dict[str, str]) -> None:
    report = json.loads(QUALITY_PATH.read_text(encoding="utf-8"))
    by_episode = {int(item["episode"]): item for item in report.get("episodes", [])}
    for item in results:
        by_episode[int(item["episode"])] = item
    if sorted(by_episode) != list(range(14)):
        raise RuntimeError(f"Relatório N3 incompleto após hotfix: {sorted(by_episode)}")
    report["operational_voice_pool"] = pool
    report["character_cast"] = cast
    report["episodes"] = [by_episode[i] for i in range(14)]
    report["greeting_hotfix_version"] = VERSION
    report["greeting_hotfix_episodes"] = list(TARGET_EPISODES)
    QUALITY_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def main() -> None:
    changed_sources = patch_sources()
    n3.VERSION = VERSION
    sound_design = json.loads(n3.SOUND_DESIGN.read_text(encoding="utf-8"))
    n3.TMP.mkdir(parents=True, exist_ok=True)
    pool = await n3.resolve_operational_pool()
    cast = n3.resolve_cast(pool)
    sem = asyncio.Semaphore(n3.MAX_CONCURRENT_SYNTH)

    results: list[dict] = []
    for number in TARGET_EPISODES:
        print(f"[A2-{number:03d}] rerender saudação canônica")
        results.append(await n3.build_episode(number, cast, sound_design, sem))

    patch_target_app_urls()
    update_quality(results, pool, cast)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {
                "version": VERSION,
                "canonical_greeting": CANONICAL_GREETING,
                "episodes": list(TARGET_EPISODES),
                "changed_sources": changed_sources,
                "residual_ola_pessoal": False,
                "malformed_canonical_punctuation": False,
                "rerendered_outputs": [item["output"] for item in results],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    shutil.rmtree(n3.TMP, ignore_errors=True)
    print(json.dumps({"status": "PASS", "episodes": TARGET_EPISODES, "version": VERSION}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
