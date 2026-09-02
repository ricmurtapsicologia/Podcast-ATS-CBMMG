from __future__ import annotations

import asyncio
import json
import shutil

import remaster_series1_n3 as n3

EPISODE = 19
NARRATOR_VOICE = "pt-BR-FranciscaNeural"
DEMO_VOICE = "pt-BR-AntonioNeural"
REPORT = n3.OUT / "quality-n3.json"


def force_ptbr_cast(turns: list[dict], pool: list[dict]) -> dict[str, str]:
    available = {item["voice"] for item in pool}
    required = {NARRATOR_VOICE, DEMO_VOICE}
    missing = required - available
    if missing:
        raise RuntimeError(f"Vozes pt-BR requeridas indisponiveis: {sorted(missing)}")

    speakers = {turn["speaker"] for turn in turns}
    expected = {"INSTRUTOR", "DEMO_M"}
    if speakers != expected:
        raise RuntimeError(f"Locutores inesperados no A1-019: {sorted(speakers)}")

    cast = {
        "INSTRUTOR": NARRATOR_VOICE,
        "DEMO_M": DEMO_VOICE,
    }
    if any("Multilingual" in voice for voice in cast.values()):
        raise RuntimeError(f"Casting multilingue proibido no A1-019: {cast}")
    if not all(voice.startswith("pt-BR-") for voice in cast.values()):
        raise RuntimeError(f"Casting fora de pt-BR no A1-019: {cast}")
    return cast


async def main() -> None:
    n3.TMP.mkdir(parents=True, exist_ok=True)
    pool = await n3.resolve_operational_pool()

    original_cast = n3.build_episode_cast
    n3.build_episode_cast = force_ptbr_cast
    try:
        result = await n3.build_episode(EPISODE, pool, asyncio.Semaphore(1))
    finally:
        n3.build_episode_cast = original_cast
        shutil.rmtree(n3.TMP / f"a1-{EPISODE:03d}", ignore_errors=True)

    output = n3.OUT / result["output"]
    if not output.exists() or output.stat().st_size <= 1000:
        raise RuntimeError(f"Master A1-019 invalido: {output}")

    cast = result.get("speaker_cast", {})
    if cast != {"INSTRUTOR": NARRATOR_VOICE, "DEMO_M": DEMO_VOICE}:
        raise RuntimeError(f"Casting final inesperado no A1-019: {cast}")
    if any("Multilingual" in voice for voice in cast.values()):
        raise RuntimeError(f"Voz multilingual persistiu no A1-019: {cast}")

    result["hotfix_language_guard"] = True
    result["hotfix_reason"] = "abertura com sonoridade de espanhol/ingles"

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    episodes = report.get("episodes", [])
    replaced = False
    for idx, episode in enumerate(episodes):
        if episode.get("episode") == EPISODE:
            episodes[idx] = result
            replaced = True
            break
    if not replaced:
        raise RuntimeError("A1-019 nao encontrado em quality-n3.json")

    report["episodes"] = episodes
    report["latest_hotfix"] = {
        "episode": EPISODE,
        "reason": "abertura com sonoridade de espanhol/ingles",
        "strategy": "casting exclusivamente pt-BR nativo, sem voz Multilingual",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
