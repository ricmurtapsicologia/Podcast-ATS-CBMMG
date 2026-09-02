from __future__ import annotations

import asyncio
import json
import shutil

import remaster_series1_n3 as n3

EPISODE = 13
NARRATOR_VOICE = "pt-BR-FranciscaNeural"
MALE_BASE_VOICE = "pt-BR-AntonioNeural"
REPORT = n3.OUT / "quality-n3.json"

# O endpoint Edge TTS pode expor apenas uma voz masculina pt-BR estável.
# Para não fundir os dois personagens, o A1-013 usa a mesma voz-base masculina
# com personas prosódicas distintas e DSP adicional no personagem em crise.
TENTANTE_DSP = {
    "pitch_shift_semitones": -3.0,
    "high_pass_hz": 75,
    "low_pass_hz": 3900,
}


async def require_voice(voice: str) -> str:
    if not await n3.probe_voice(voice):
        raise RuntimeError(f"Voz pt-BR requerida indisponível: {voice}")
    return voice


def force_cast(turns: list[dict], pool: list[dict]) -> dict[str, str]:
    del pool
    speakers = {turn["speaker"] for turn in turns}
    expected = {"INSTRUTOR", "ABORDADOR_M", "TENTANTE_M"}
    if speakers != expected:
        raise RuntimeError(f"Locutores inesperados no A1-013: {sorted(speakers)}")
    return {
        "INSTRUTOR": NARRATOR_VOICE,
        "ABORDADOR_M": MALE_BASE_VOICE,
        "TENTANTE_M": MALE_BASE_VOICE,
    }


async def main() -> None:
    n3.TMP.mkdir(parents=True, exist_ok=True)
    await require_voice(NARRATOR_VOICE)
    await require_voice(MALE_BASE_VOICE)

    # Separação perceptual forte entre abordador e Carlos, preservando ambos
    # como personagens masculinos brasileiros.
    n3.SPEAKER_PERSONA["ABORDADOR_M"] = {
        "rate": 0,
        "pitch": 3,
        "label": "masculino-profissional-a1-013",
    }
    n3.SPEAKER_PERSONA["TENTANTE_M"] = {
        "rate": -4,
        "pitch": -6,
        "label": "masculino-crise-dsp-a1-013",
    }
    n3.CHARACTER_DSP["TENTANTE_M"] = dict(TENTANTE_DSP)

    pool = [
        {"voice": NARRATOR_VOICE, "gender": "F"},
        {"voice": MALE_BASE_VOICE, "gender": "M"},
    ]

    original_cast = n3.build_episode_cast
    n3.build_episode_cast = force_cast
    try:
        result = await n3.build_episode(EPISODE, pool, asyncio.Semaphore(1))
    finally:
        n3.build_episode_cast = original_cast
        shutil.rmtree(n3.TMP / f"a1-{EPISODE:03d}", ignore_errors=True)

    output = n3.OUT / result["output"]
    if not output.exists() or output.stat().st_size <= 1000:
        raise RuntimeError(f"Master A1-013 inválido: {output}")

    cast = result["speaker_cast"]
    identity = result["voice_identity"]
    dsp = result["speaker_dsp"]
    if cast["INSTRUTOR"] != NARRATOR_VOICE:
        raise RuntimeError(f"Narrador final inesperado: {cast}")
    if cast["ABORDADOR_M"] != MALE_BASE_VOICE or cast["TENTANTE_M"] != MALE_BASE_VOICE:
        raise RuntimeError(f"Casting masculino inesperado: {cast}")
    if identity["ABORDADOR_M"] == identity["TENTANTE_M"]:
        raise RuntimeError(f"Personagens sem identidades perceptuais distintas: {identity}")
    if float(dsp["TENTANTE_M"].get("pitch_shift_semitones", 0)) >= -2.5:
        raise RuntimeError(f"DSP insuficiente para diferenciar Carlos: {dsp}")

    result["hotfix_distinct_characters"] = True
    result["base_voice_shared_due_provider"] = True
    result["character_strategy"] = "persona prosódica + DSP do tentante"

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    episodes = report.get("episodes", [])
    replaced = False
    for idx, episode in enumerate(episodes):
        if episode.get("episode") == EPISODE:
            episodes[idx] = result
            replaced = True
            break
    if not replaced:
        raise RuntimeError("A1-013 não encontrado em quality-n3.json")

    report["episodes"] = episodes
    report["latest_hotfix"] = {
        "episode": EPISODE,
        "reason": "abordador e tentante soavam como a mesma pessoa",
        "strategy": "duas identidades masculinas distintas por prosódia e DSP",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
