from __future__ import annotations

"""Correção cirúrgica v5 da abertura da Série 1.

Objetivos:
- A1-001: separar claramente título, saudação e corpo, como nos demais episódios;
- toda ocorrência de "Olá pessoal" na Série 1: transformá-la em unidade própria de
  saudação, com pontuação, ritmo e pausa naturais;
- preservar integralmente a sequência lexical dos roteiros congelados.
"""

import asyncio
import json
import re

from pydub import AudioSegment, effects

import remaster_series1_organic as base


base.VERSION_TAG = "organic-v5"
base.TMP = base.ROOT / ".tmp_serie1_organic_v5"

GREETING_RATE = "-11%"
GREETING_PITCH = "+0Hz"
GREETING_PAUSE_MS = 700
TITLE_001_RATE = "-9%"
TITLE_001_PITCH = "-1Hz"
TITLE_001_PAUSE_MS = 590
DEFAULT_BLOCK_PAUSE_MS = 520


def _tokens(text: str) -> list[str]:
    return base.lexical_tokens(text)


def _is_greeting(text: str) -> bool:
    return _tokens(text) == ["olá", "pessoal"]


def _is_title_001(text: str) -> bool:
    return _tokens(text) == ["abordagem", "técnica", "comunicação", "que", "salva"]


def _apply_opening_structure(text: str, number: int) -> str:
    """Acrescenta somente pontuação/capitalização de leitura, sem trocar palavras."""
    original_tokens = _tokens(text)

    # A1-001 veio congelado sem separação entre título e saudação.
    if number == 1:
        text = re.sub(
            r"^\s*abordagem\s+técnica\s+comunicação\s+que\s+salva(?=\s+olá\s*,?\s*pessoal\b)",
            "Abordagem técnica: comunicação que salva.",
            text,
            count=1,
            flags=re.IGNORECASE,
        )

    # Padroniza a saudação como frase própria. O ponto evita que o TTS a emende
    # ao conteúdo seguinte; a vírgula preserva a curva natural de vocativo.
    text = re.sub(
        r"\bolá\s*,?\s+pessoal\b[.!?…]*",
        "Olá, pessoal.",
        text,
        flags=re.IGNORECASE,
    )

    # Se a saudação ainda estiver colada ao título/frase anterior, cria o limite.
    text = re.sub(
        r"(?<![.!?…])\s+(Olá, pessoal\.)",
        r". \1",
        text,
        count=1,
    )

    if _tokens(text) != original_tokens:
        raise RuntimeError(
            f"Gate lexical falhou ao estruturar a abertura do episódio {number:03d}."
        )
    return text


def chunk_spoken_text(text: str) -> list[str]:
    """Mantém 'Olá, pessoal.' isolado para receber prosódia própria."""
    text = base.normalize_text(text)
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?…])\s+", text)
        if sentence.strip()
    ]
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    def flush_current() -> None:
        nonlocal current, current_len
        if current:
            chunks.append(" ".join(current))
            current = []
            current_len = 0

    for sentence in sentences:
        if _is_greeting(sentence):
            flush_current()
            chunks.append(sentence)
            continue

        projected = current_len + (1 if current else 0) + len(sentence)
        if current and projected > base.MAX_SYNTH_CHARS:
            flush_current()

        current.append(sentence)
        current_len = sum(len(part) for part in current) + max(0, len(current) - 1)

    flush_current()
    return chunks


_original_prosody_for = base.prosody_for


def prosody_for(voice: str, text: str, turn_index: int):
    if _is_greeting(text):
        # Saudação curta: mais lenta e neutra, sem a subida artificial que estava
        # dando sensação de locução apressada/robotizada.
        return GREETING_RATE, GREETING_PITCH
    if _is_title_001(text):
        return TITLE_001_RATE, TITLE_001_PITCH
    return _original_prosody_for(voice, text, turn_index)


def read_frozen_turns(number: int):
    path = base.ROTEIROS / f"a1-{number:03d}.txt"
    if not path.exists():
        raise RuntimeError(f"Roteiro congelado ausente: {path}")

    turns = []
    source_words: list[str] = []
    spoken_words: list[str] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("PROFISSIONAL:"):
            voice = base.VOICE_PROFISSIONAL
            text = line.split(":", 1)[1].strip()
        elif line.startswith("INSTRUTOR:"):
            voice = base.VOICE_INSTRUTOR
            text = line.split(":", 1)[1].strip()
        else:
            voice = base.VOICE_INSTRUTOR
            text = line

        if not text:
            continue

        source_words.extend(_tokens(text))

        # Primeiro restaura a pontuação semântica geral do perfil v4; depois
        # aplica a estrutura específica de abertura, evitando que a saudação seja
        # novamente absorvida por um bloco longo.
        spoken = base.add_prosodic_punctuation(text)
        spoken = _apply_opening_structure(spoken, number)
        spoken_words.extend(_tokens(spoken))
        turns.extend((voice, chunk) for chunk in chunk_spoken_text(spoken))

    if not turns or source_words != spoken_words:
        raise RuntimeError(
            f"Gate de integridade lexical falhou no episódio {number:03d}."
        )

    return turns, len(source_words)


async def synth_episode(number: int, turns, semaphore: asyncio.Semaphore):
    work = base.TMP / f"a1-{number:03d}"
    work.mkdir(parents=True, exist_ok=True)
    tasks = []
    sequence = []

    for idx, (voice, text) in enumerate(turns):
        rate, pitch = prosody_for(voice, text, idx)
        part = work / f"{idx:03d}.mp3"

        if idx >= len(turns) - 1:
            pause_ms = 0
        elif _is_greeting(text):
            pause_ms = GREETING_PAUSE_MS
        elif number == 1 and _is_title_001(text):
            pause_ms = TITLE_001_PAUSE_MS
        else:
            pause_ms = DEFAULT_BLOCK_PAUSE_MS

        sequence.append((part, pause_ms))
        tasks.append(base.synthesize(text, voice, rate, pitch, part, semaphore))

    await asyncio.gather(*tasks)

    merged = AudioSegment.silent(duration=base.OPENING_SILENCE_MS)
    for part, pause_ms in sequence:
        merged += AudioSegment.from_file(part, format="mp3")
        if pause_ms:
            merged += AudioSegment.silent(duration=pause_ms)
    merged += AudioSegment.silent(duration=base.ENDING_SILENCE_MS)

    merged = effects.compress_dynamic_range(
        merged,
        threshold=-20.0,
        ratio=2.0,
        attack=8.0,
        release=70.0,
    )
    if merged.dBFS != float("-inf"):
        merged = merged.apply_gain(base.TARGET_DBFS - merged.dBFS)
    if merged.max_dBFS > -1.2:
        merged = merged.apply_gain(-1.2 - merged.max_dBFS)

    base.OUT.mkdir(parents=True, exist_ok=True)
    target = base.OUT / f"a1-{number:03d}-{base.VERSION_TAG}.mp3"
    merged.export(
        target,
        format="mp3",
        bitrate="128k",
        parameters=["-ac", "1", "-ar", "44100"],
    )
    return target, round(len(merged) / 1000, 1)


async def process_episode(number: int, semaphore: asyncio.Semaphore):
    turns, word_count = read_frozen_turns(number)
    greeting_units = sum(1 for _, text in turns if _is_greeting(text))
    target, seconds = await synth_episode(number, turns, semaphore)
    print(
        f"[{number:03d}] orgânico v5 | blocos={len(turns)} | "
        f"saudações={greeting_units} | duração={seconds}s"
    )
    return {
        "episode": number,
        "output": target.name,
        "lexical_integrity": 1.0,
        "source_words": word_count,
        "synth_blocks": len(turns),
        "greeting_units": greeting_units,
        "duration_seconds": seconds,
        "audio_profile": "serie-1-organic-v5-opening-fix",
        "base_rate": {"instrutor": -7, "profissional": -4},
        "greeting_rate": GREETING_RATE,
        "greeting_pause_ms": GREETING_PAUSE_MS,
        "a1_001_title_separated": number == 1,
        "prosodic_punctuation": True,
    }


async def main():
    base.OUT.mkdir(parents=True, exist_ok=True)
    base.TMP.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(base.MAX_CONCURRENT_SYNTH)

    quality = await asyncio.gather(*[
        process_episode(number, semaphore)
        for number in range(1, 22)
    ])
    quality.sort(key=lambda item: item["episode"])

    base.patch_app_urls()
    base.patch_index_cache()
    (base.OUT / "quality-organic-v5.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Série 1 concluída no perfil orgânico v5 com abertura padronizada.")


if __name__ == "__main__":
    asyncio.run(main())
