from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import remaster_series1_n3 as n3

EPISODE = 7
VERSION = "n3-cast-20260901f"
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
    cast: dict[str, str] = {}
    if "INSTRUTOR" in speakers:
        cast["INSTRUTOR"] = NARRATOR_VOICE
    if "DEMO_M" in speakers:
        cast["DEMO_M"] = DEMO_VOICE

    unsupported = speakers - set(cast)
    if unsupported:
        raise RuntimeError(f"Locutores inesperados no A1-007: {sorted(unsupported)}")
    if any("Multilingual" in voice for voice in cast.values()):
        raise RuntimeError(f"Casting multilingue proibido no A1-007: {cast}")
    return cast


async def main() -> None:
    source = n3.ROTEIROS / "a1-007.txt"
    source_text = source.read_text(encoding="utf-8").lower()
    if "paciente" in source_text:
        raise RuntimeError("Terminologia clínica indevida ainda presente no A1-007: paciente")
    if "tentantes com perfil depressivo" not in source_text:
        raise RuntimeError("Terminologia ATS esperada não encontrada no A1-007")

    n3.TMP.mkdir(parents=True, exist_ok=True)
    pool = await n3.resolve_operational_pool()

    original_cast = n3.build_episode_cast
    n3.build_episode_cast = force_ptbr_cast
    try:
        result = await n3.build_episode(EPISODE, pool, asyncio.Semaphore(1))
    finally:
        n3.build_episode_cast = original_cast
        shutil.rmtree(n3.TMP / f"a1-{EPISODE:03d}", ignore_errors=True)

    result["version"] = VERSION
    result["terminology_hotfix"] = {"from": "pacientes", "to": "tentantes"}

    output = n3.OUT / result["output"]
    if not output.exists() or output.stat().st_size <= 1000:
        raise RuntimeError(f"Master A1-007 invalido: {output}")

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    episodes = report.get("episodes", [])
    replaced = False
    for idx, episode in enumerate(episodes):
        if episode.get("episode") == EPISODE:
            episodes[idx] = result
            replaced = True
            break
    if not replaced:
        raise RuntimeError("A1-007 nao encontrado em quality-n3.json")

    report["episodes"] = episodes
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    voices = set(result.get("speaker_cast", {}).values())
    if voices != {NARRATOR_VOICE, DEMO_VOICE}:
        raise RuntimeError(f"Casting final inesperado: {result.get('speaker_cast')}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
