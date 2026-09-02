from __future__ import annotations

import asyncio
import json
import shutil

import remaster_series1_n3 as n3

EPISODE = 17
NARRATOR_VOICE = "pt-BR-AntonioNeural"
REPORT = n3.OUT / "quality-n3.json"


def force_ptbr_cast(turns: list[dict], pool: list[dict]) -> dict[str, str]:
    del pool
    speakers = {turn["speaker"] for turn in turns}
    if speakers != {"INSTRUTOR"}:
        raise RuntimeError(f"Locutores inesperados no A1-017: {sorted(speakers)}")
    return {"INSTRUTOR": NARRATOR_VOICE}


async def main() -> None:
    n3.TMP.mkdir(parents=True, exist_ok=True)
    if not await n3.probe_voice(NARRATOR_VOICE):
        raise RuntimeError(f"Voz pt-BR requerida indisponivel: {NARRATOR_VOICE}")

    pool = [{"voice": NARRATOR_VOICE, "gender": "M"}]
    original_cast = n3.build_episode_cast
    n3.build_episode_cast = force_ptbr_cast
    try:
        result = await n3.build_episode(EPISODE, pool, asyncio.Semaphore(1))
    finally:
        n3.build_episode_cast = original_cast
        shutil.rmtree(n3.TMP / f"a1-{EPISODE:03d}", ignore_errors=True)

    output = n3.OUT / result["output"]
    if not output.exists() or output.stat().st_size <= 1000:
        raise RuntimeError(f"Master A1-017 invalido: {output}")

    cast = result.get("speaker_cast", {})
    if cast != {"INSTRUTOR": NARRATOR_VOICE}:
        raise RuntimeError(f"Casting final inesperado: {cast}")
    if any("Multilingual" in voice for voice in cast.values()):
        raise RuntimeError(f"Casting multilingue proibido no A1-017: {cast}")

    result["hotfix_language_guard"] = True
    result["hotfix_reason"] = "abertura com prosodia semelhante a ingles"
    result["opening_voice_replaced"] = "pt-BR-FranciscaNeural -> pt-BR-AntonioNeural"

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    episodes = report.get("episodes", [])
    replaced = False
    for idx, episode in enumerate(episodes):
        if episode.get("episode") == EPISODE:
            episodes[idx] = result
            replaced = True
            break
    if not replaced:
        raise RuntimeError("A1-017 nao encontrado em quality-n3.json")

    report["episodes"] = episodes
    report["latest_hotfix"] = {
        "episode": EPISODE,
        "reason": "abertura com prosodia semelhante a ingles",
        "strategy": "narracao pt-BR AntonioNeural, sem voz Multilingual",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
