from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil

from pydub import AudioSegment

import remaster_series1_n3 as n3
from n3_casting import voice_gender

EPISODE = 8
HOTFIX_VERSION = "n3-cast-20260901e"
REPORT = n3.OUT / "quality-n3.json"
HOTFIX_REPORT = n3.ROOT / "reports" / "a1-008-hotfix-casting-ptbr.json"
ROTEIRO = n3.ROTEIROS / "a1-008.txt"
CORE = n3.ROOT / "scripts" / "n3_audio_core.py"
REMASTER = n3.ROOT / "scripts" / "remaster_series1_n3.py"
APP = n3.APP

NARRATOR = "pt-BR-FranciscaNeural"
MALE_BASE = "pt-BR-AntonioNeural"
TENTANTE_DSP = {
    "pitch_shift_semitones": -2.2,
    "high_pass_hz": 80,
    "low_pass_hz": 4200,
}


def patch_roteiro() -> None:
    text = ROTEIRO.read_text(encoding="utf-8")
    text = re.sub(r"\bhobby\b", "passatempo", text, flags=re.IGNORECASE)
    text = re.sub(r"\bMPB\b", "música popular brasileira", text, flags=re.IGNORECASE)
    lowered = text.lower()
    if "hobby" in lowered or "passatempo" not in lowered:
        raise RuntimeError("Normalização de 'hobby' falhou no A1-008.")
    if "gosto de mpb" in lowered or "música popular brasileira" not in lowered:
        raise RuntimeError("Normalização de 'MPB' falhou no A1-008.")
    ROTEIRO.write_text(text, encoding="utf-8")


def patch_pronunciation_dictionary() -> None:
    text = CORE.read_text(encoding="utf-8")
    marker = "r'\\bMPB\\b': 'música popular brasileira'"
    if marker in text:
        return
    needle = "    r'\\bOMS\\b': 'O M S',"
    if needle not in text:
        raise RuntimeError("Ponto de inserção do dicionário MPB não encontrado.")
    text = text.replace(needle, "    r'\\bMPB\\b': 'música popular brasileira',\n" + needle, 1)
    CORE.write_text(text, encoding="utf-8")


def patch_renderer_defaults() -> None:
    text = REMASTER.read_text(encoding="utf-8")
    text = text.replace('VERSION = "n3-cast-20260901c"', f'VERSION = "{HOTFIX_VERSION}"')

    old_common = '        return ["pt-BR-AntonioNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural"]'
    narrator_new = '        return ["pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural", "pt-BR-AntonioNeural", "pt-BR-ThalitaMultilingualNeural"]'
    male_new = '        return ["pt-BR-AntonioNeural", "pt-BR-MacerioMultilingualNeural", "pt-BR-FabioNeural", "pt-BR-DonatoNeural", "pt-BR-HumbertoNeural", "pt-BR-JulioNeural", "pt-BR-NicolauNeural", "pt-BR-ValerioNeural"]'
    if old_common in text:
        text = text.replace(old_common, narrator_new, 1)
    if old_common in text:
        text = text.replace(old_common, male_new, 1)

    text = text.replace(
        '    "ABORDADOR_M": {"rate": 0, "pitch": 1, "label": "masculino-profissional"},',
        '    "ABORDADOR_M": {"rate": 0, "pitch": 3, "label": "masculino-profissional"},',
    )
    text = text.replace(
        '    "TENTANTE_M": {"rate": -2, "pitch": -3, "label": "masculino-crise"},',
        '    "TENTANTE_M": {"rate": -3, "pitch": -5, "label": "masculino-crise-dsp"},',
    )

    if "CHARACTER_DSP =" not in text:
        insertion = '''\n\nCHARACTER_DSP = {\n    "TENTANTE_M": {"pitch_shift_semitones": -2.2, "high_pass_hz": 80, "low_pass_hz": 4200},\n}\n\n\ndef character_dsp_profile(speaker: str) -> dict:\n    return CHARACTER_DSP.get(speaker, {"pitch_shift_semitones": 0.0})\n\n\ndef apply_character_dsp(segment: AudioSegment, speaker: str) -> AudioSegment:\n    cfg = CHARACTER_DSP.get(speaker)\n    if not cfg:\n        return segment\n    semitones = float(cfg["pitch_shift_semitones"])\n    factor = 2.0 ** (semitones / 12.0)\n    shifted_rate = max(8000, int(segment.frame_rate * factor))\n    segment = segment._spawn(segment.raw_data, overrides={"frame_rate": shifted_rate}).set_frame_rate(segment.frame_rate)\n    segment = segment.high_pass_filter(int(cfg["high_pass_hz"]))\n    segment = segment.low_pass_filter(int(cfg["low_pass_hz"]))\n    return segment\n'''
        needle = "\ndef normalize_space(text: str) -> str:\n"
        if needle not in text:
            raise RuntimeError("Ponto de inserção do DSP não encontrado no renderizador.")
        text = text.replace(needle, insertion + needle, 1)

    old_append = '        sequence.append((part, 0 if idx == len(turns)-1 else pause))'
    new_append = '        sequence.append((part, 0 if idx == len(turns)-1 else pause, turn["speaker"]))'
    if old_append in text:
        text = text.replace(old_append, new_append, 1)

    old_loop = '    for part, pause in sequence:\n        audio += AudioSegment.from_file(part, format="mp3")'
    new_loop = '    for part, pause, speaker in sequence:\n        rendered = AudioSegment.from_file(part, format="mp3")\n        audio += apply_character_dsp(rendered, speaker)'
    if old_loop in text:
        text = text.replace(old_loop, new_loop, 1)

    if '"speaker_dsp": {s: character_dsp_profile(s) for s in episode_speakers},' not in text:
        needle = '        "speaker_persona": {s: persona_for(s) for s in episode_speakers},\n'
        if needle not in text:
            raise RuntimeError("Ponto de inserção do relatório DSP não encontrado.")
        text = text.replace(
            needle,
            needle + '        "speaker_dsp": {s: character_dsp_profile(s) for s in episode_speakers},\n',
            1,
        )

    required = [
        f'VERSION = "{HOTFIX_VERSION}"',
        'return ["pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural"',
        '"TENTANTE_M": {"rate": -3, "pitch": -5, "label": "masculino-crise-dsp"}',
        'CHARACTER_DSP = {',
        'apply_character_dsp(rendered, speaker)',
        '"speaker_dsp": {s: character_dsp_profile(s) for s in episode_speakers}',
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise RuntimeError(f"Blindagem permanente de personagem incompleta: {missing}")
    REMASTER.write_text(text, encoding="utf-8")


def patch_app_cache_buster() -> None:
    text = APP.read_text(encoding="utf-8")
    old = "assets/audio/serie-1/a1-008-n3.mp3?v=n3-cast-20260901c"
    new = f"assets/audio/serie-1/a1-008-n3.mp3?v={HOTFIX_VERSION}"
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise RuntimeError("URL do A1-008 não localizada em app.js.")
    APP.write_text(text, encoding="utf-8")


async def require_voice(voice: str, gender: str) -> str:
    if voice_gender(voice) != gender:
        raise RuntimeError(f"Gênero inesperado para {voice}.")
    if not await n3.probe_voice(voice):
        raise RuntimeError(f"Voz operacional obrigatória indisponível: {voice}")
    return voice


def forced_cast_factory(narrator: str, male: str):
    def force_cast(turns: list[dict], pool: list[dict]) -> dict[str, str]:
        speakers = {turn["speaker"] for turn in turns}
        expected = {"INSTRUTOR", "ABORDADOR_M", "TENTANTE_M"}
        if speakers != expected:
            raise RuntimeError(f"Locutores inesperados no A1-008: {sorted(speakers)}")
        cast = {
            "INSTRUTOR": narrator,
            "ABORDADOR_M": male,
            "TENTANTE_M": male,
        }
        if "Multilingual" in cast["INSTRUTOR"] or "Multilingual" in cast["ABORDADOR_M"]:
            raise RuntimeError(f"Narrador/abordador multilíngue proibido: {cast}")
        return cast

    return force_cast


def speakable_ptbr_factory(original):
    def speakable_ptbr(text: str) -> str:
        text = re.sub(r"\bhobby\b", "passatempo", text, flags=re.IGNORECASE)
        text = re.sub(r"\bMPB\b", "música popular brasileira", text, flags=re.IGNORECASE)
        return original(text)

    return speakable_ptbr


def transform_tentante_file(path) -> bool:
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    audio = AudioSegment.from_file(path, format="mp3")
    factor = 2.0 ** (float(TENTANTE_DSP["pitch_shift_semitones"]) / 12.0)
    shifted_rate = max(8000, int(audio.frame_rate * factor))
    audio = audio._spawn(audio.raw_data, overrides={"frame_rate": shifted_rate}).set_frame_rate(audio.frame_rate)
    audio = audio.high_pass_filter(int(TENTANTE_DSP["high_pass_hz"]))
    audio = audio.low_pass_filter(int(TENTANTE_DSP["low_pass_hz"]))
    audio.export(path, format="mp3", bitrate="128k")
    after = hashlib.sha256(path.read_bytes()).hexdigest()
    return before != after


def synth_with_character_dsp_factory(original_synth, expected_turns: list[dict], audit: dict):
    state = {"index": 0}

    async def synth_with_character_dsp(text, voice, rate, pitch, path, sem):
        idx = state["index"]
        if idx >= len(expected_turns):
            raise RuntimeError("Mais chamadas TTS do que turnos esperados no A1-008.")
        turn = expected_turns[idx]
        state["index"] += 1
        if n3.normalize_space(turn["text"]) != n3.normalize_space(text):
            raise RuntimeError(f"Desalinhamento de turno no DSP: esperado={turn['speaker']}")
        await original_synth(text, voice, rate, pitch, path, sem)
        if turn["speaker"] == "TENTANTE_M":
            if not transform_tentante_file(path):
                raise RuntimeError("DSP do tentante não alterou o segmento de áudio.")
            audit["transformed_segments"] += 1

    return synth_with_character_dsp


async def main() -> None:
    patch_roteiro()
    patch_pronunciation_dictionary()
    patch_renderer_defaults()

    n3.TMP.mkdir(parents=True, exist_ok=True)
    narrator = await require_voice(NARRATOR, "F")
    male = await require_voice(MALE_BASE, "M")
    pool = [
        {"voice": narrator, "gender": "F"},
        {"voice": male, "gender": "M"},
    ]

    # Persona perceptual: o abordador fica mais claro/estável e o tentante mais
    # grave/lento; o tentante recebe ainda transformação pós-síntese.
    n3.SPEAKER_PERSONA["ABORDADOR_M"] = {"rate": 0, "pitch": 3, "label": "masculino-profissional"}
    n3.SPEAKER_PERSONA["TENTANTE_M"] = {"rate": -3, "pitch": -5, "label": "masculino-crise-dsp"}

    expected_turns = n3.compact_turns(n3.raw_turns(EPISODE))
    audit = {"transformed_segments": 0}
    original_cast = n3.build_episode_cast
    original_speakable = n3.speakable
    original_synth = n3.synth
    n3.build_episode_cast = forced_cast_factory(narrator, male)
    n3.speakable = speakable_ptbr_factory(original_speakable)
    n3.synth = synth_with_character_dsp_factory(original_synth, expected_turns, audit)
    try:
        result = await n3.build_episode(EPISODE, pool, asyncio.Semaphore(1))
    finally:
        n3.build_episode_cast = original_cast
        n3.speakable = original_speakable
        n3.synth = original_synth
        shutil.rmtree(n3.TMP / f"a1-{EPISODE:03d}", ignore_errors=True)

    if audit["transformed_segments"] <= 0:
        raise RuntimeError("Nenhum segmento do tentante recebeu DSP.")

    output = n3.OUT / result["output"]
    if not output.exists() or output.stat().st_size <= 1000:
        raise RuntimeError(f"Master A1-008 inválido: {output}")

    result["version"] = HOTFIX_VERSION
    result["hotfix_language_guard"] = True
    result["hotfix_distinct_male_characters"] = True
    result["base_voice_shared_due_provider"] = True
    result["character_dsp_applied_segments"] = audit["transformed_segments"]
    result["speaker_dsp"] = {
        "ABORDADOR_M": {"pitch_shift_semitones": 0.0},
        "TENTANTE_M": dict(TENTANTE_DSP),
    }
    result["normalized_terms"] = {
        "hobby": "passatempo",
        "MPB": "música popular brasileira",
    }

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    episodes = report.get("episodes", [])
    replaced = False
    for idx, episode in enumerate(episodes):
        if episode.get("episode") == EPISODE:
            episodes[idx] = result
            replaced = True
            break
    if not replaced:
        raise RuntimeError("A1-008 não encontrado em quality-n3.json")
    report["episodes"] = episodes
    report["latest_hotfix"] = {
        "episode": EPISODE,
        "version": HOTFIX_VERSION,
        "reason": "personagens masculinos semelhantes e trecho com sonoridade estrangeira",
        "strategy": "PT-BR fixo + DSP perceptual do tentante",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    patch_app_cache_buster()
    HOTFIX_REPORT.parent.mkdir(parents=True, exist_ok=True)
    HOTFIX_REPORT.write_text(
        json.dumps(
            {
                "episode": EPISODE,
                "version": HOTFIX_VERSION,
                "speaker_cast": result["speaker_cast"],
                "voice_identity": result["voice_identity"],
                "base_voice_shared_due_provider": True,
                "distinct_character_identities": result["voice_identity"]["ABORDADOR_M"] != result["voice_identity"]["TENTANTE_M"],
                "character_dsp_applied_segments": audit["transformed_segments"],
                "speaker_dsp": result["speaker_dsp"],
                "normalizations": result["normalized_terms"],
                "output": str(output.relative_to(n3.ROOT)),
                "duration_seconds": result["duration_seconds"],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
