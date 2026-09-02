from __future__ import annotations

import asyncio
import json
import shutil

import remaster_series1_n3 as n3

EPISODE = 13
NARRATOR_VOICE = "pt-BR-FranciscaNeural"
ABORDADOR_VOICE = "pt-BR-AntonioNeural"
TENTANTE_CANDIDATES = [
    "pt-BR-FabioNeural",
    "pt-BR-DonatoNeural",
    "pt-BR-HumbertoNeural",
    "pt-BR-JulioNeural",
    "pt-BR-NicolauNeural",
    "pt-BR-ValerioNeural",
]
REPORT = n3.OUT / "quality-n3.json"


async def select_native_tentante_voice() -> string:
    for voice in TENTANTE_CANDIDATES:
        if await n3.probe_voice(voice):
            return voice
    raise RuntimeError("Nenhuma segunda voz masculina pt-BR nativa ficou disponivel para A1-013")


def make_force_cast(tentante_voice: str):
    def force_ptbr_cast(turns: list[dict], pool: list[dict]) -> dict[str, str]:
        del pool
        speakers = {turn["speaker"] for turn in turns}
        cast = {
            "INSTRUTOR": NARRATOR_VOICE,
            "ABORDADOR_M": ABORDADOR_VOICE,
            "TENTANTE_M": tentante_voice,
        }
        unsupported = speakers - set(cast)
        missing = set(cast) - speakers
        if unsupported or missing:
            raise RuntimeError(
                f"Locutores inesperados no A1-013 | unsupported={sorted(unsupported)} missing={sorted(missing)}"
            )
        if any("Multilingual" in voice for voice in cast.values()):
            raise RuntimeError(f"Casting multilingue proibido no A1-013: {cast}")
        if not all(voice.startswith("pt-BR-") for voice in cast.values()):
            raise RuntimeError(f"Casting fora de pt-BR no A1-013: {cast}")
        if cast["ABORDADOR_M"] == cast["TENTANTE_M"]:
            raise RuntimeError(f"Personagens masculinos sem diferenciacao de voz: {cast}")
        return cast

    return force_ptbr_cast


async def main() -> None:
    n3.TMP.mkdir(parents=True, exist_ok=True)

    for voice in (NARRATOR_VOICE, ABORDADOR_VOICE):
        if not await n3.probe_voice(voice):
            raise RuntimeError(f"Voz pt-BR requerida indisponivel: {voice}")
    tentante_voice = await select_native_tentante_voice()

    pool = [
        {"voice": NARRATOR_VOICE, "gender": "F"},
        {"voice": ABORDADOR_VOICE, "gender": "M"},
        {"voice": tentante_voice, "gender": "M"},
    ]

    original_cast = n3.build_episode_cast
    n3.build_episode_cast = make_force_cast(tentante_voice)
    try:
        result = await n3.build_episode(EPISODE, pool, asyncio.Semaphore(1))
    finally:
        n3.build_episode_cast = original_cast
        shutil.rmtree(n3.TMP / f"a1-{EPISODE:03d}", ignore_errors=True)

    output = n3.OUT / result["output"]
    if not output.exists() or output.stat().st_size <= 1000:
        raise RuntimeError(f"Master A1-013 invalido: {output}")

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    episodes = report.get("episodes", [])
    replaced = False
    for idx, episode in enumerate(episodes):
        if episode.get("episode") == EPISODE:
            episodes[idx] = result
            replaced = True
            break
    if not replaced:
        raise RuntimeError("A1-013 nao encontrado em quality-n3.json")

    report["episodes"] = episodes
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cast = result.get("speaker_cast", {})
    if cast.get("INSTRUTOR") != NARRATOR_VOICE:
        raise RuntimeError(f"Narrador final inesperado: {cast}")
    if cast.get("ABORDADOR_M") != ABORDADOR_VOICE:
        raise RuntimeError(f"Abordador final inesperado: {cast}")
    if cast.get("TENTANTE_M") != tentante_voice:
        raise RuntimeError(f"Tentante final inesperado: {cast}")
    if any("Multilingual" in voice for voice in cast.values()):
        raise RuntimeError(f"Voz multilingual persistiu no A1-013: {cast}")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
