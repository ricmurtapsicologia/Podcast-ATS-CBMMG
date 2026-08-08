from __future__ import annotations

"""Geração dos MP3s da Série 3 — padrão de áudio N2.

Princípios do N2:
- preserva integralmente o texto narrado dos roteiros;
- usa vozes neurais pt-BR já validadas no projeto;
- segmenta a fala em unidades naturais sem reescrever o conteúdo;
- varia discretamente ritmo e pitch conforme função da frase;
- aplica pausas contextuais entre frases e interlocutores;
- faz compressão leve e normalização para escuta mais uniforme.
"""

import asyncio
import re
from pathlib import Path

import edge_tts
from pydub import AudioSegment, effects

ROOT = Path(__file__).resolve().parents[1]
ROTEIROS = ROOT / "roteiros" / "serie-3"
OUT = ROOT / "assets" / "audio" / "serie-3"
TMP = ROOT / ".tmp_psp_audio_n2"

VOICE_INSTRUTOR = "pt-BR-AntonioNeural"
VOICE_PROFISSIONAL = "pt-BR-FranciscaNeural"

# Ritmo-base menos uniforme que a versão anterior, preservando clareza didática.
BASE_RATE = {
    "INSTRUTOR": -4,
    "PROFISSIONAL": -1,
}
BASE_PITCH = {
    "INSTRUTOR": -1,
    "PROFISSIONAL": 1,
}

TURN_PAUSE_MS = 520
OPENING_SILENCE_MS = 130
ENDING_SILENCE_MS = 240
TARGET_DBFS = -18.0

PATTERN = re.compile(r"^\*\*(INSTRUTOR|PROFISSIONAL):\*\*\s*(.+)$")
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ0-9\"“])")
CLAUSE_BOUNDARY = re.compile(r"(?<=[;:])\s+")


def read_turns(path: Path):
    turns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = PATTERN.match(line.strip())
        if match:
            turns.append((match.group(1), match.group(2).strip()))
    if not turns:
        raise RuntimeError(f"Nenhuma fala encontrada em {path}")
    return turns


def split_natural(text: str) -> list[str]:
    """Divide para prosódia sem mudar palavras, pontuação ou ordem do texto."""
    sentences = [part for part in SENTENCE_BOUNDARY.split(text) if part]
    chunks: list[str] = []
    for sentence in sentences:
        if len(sentence) <= 290:
            chunks.append(sentence)
            continue
        clauses = [part for part in CLAUSE_BOUNDARY.split(sentence) if part]
        if len(clauses) == 1:
            chunks.append(sentence)
        else:
            chunks.extend(clauses)
    return chunks


def pause_after(text: str) -> int:
    stripped = text.rstrip()
    if stripped.endswith("?"):
        return 440
    if stripped.endswith("!"):
        return 390
    if stripped.endswith((".", "…")):
        return 360
    if stripped.endswith(":"):
        return 300
    if stripped.endswith(";"):
        return 260
    return 220


def prosody_for(speaker: str, text: str, chunk_index: int, chunk_total: int) -> tuple[str, str]:
    rate = BASE_RATE[speaker]
    pitch = BASE_PITCH[speaker]
    normalized = text.strip().lower()

    # Perguntas ganham leve subida e fluxo um pouco mais conversacional.
    if text.rstrip().endswith("?"):
        rate += 2
        pitch += 2

    # Sínteses e frases de retenção ficam discretamente mais lentas.
    if normalized.startswith(("guarde", "em resumo", "microchecagem", "pense", "imagine", "o ponto")):
        rate -= 2

    # Evita uma cadência idêntica em todos os períodos, sem dramatização.
    if chunk_total > 1:
        cycle = (-1, 0, 1, 0)
        rate += cycle[chunk_index % len(cycle)]

    rate = max(-10, min(4, rate))
    pitch = max(-4, min(4, pitch))
    return f"{rate:+d}%", f"{pitch:+d}Hz"


async def synthesize(text: str, voice: str, rate: str, pitch: str, output: Path):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume="+0%",
        pitch=pitch,
    )
    await communicate.save(str(output))


async def build_lesson(number: int):
    script = ROTEIROS / f"psp-{number:02d}.md"
    turns = read_turns(script)
    work = TMP / f"psp-{number:02d}"
    work.mkdir(parents=True, exist_ok=True)

    merged = AudioSegment.silent(duration=OPENING_SILENCE_MS)
    segment_number = 0

    for turn_index, (speaker, text) in enumerate(turns):
        chunks = split_natural(text)
        voice = VOICE_INSTRUTOR if speaker == "INSTRUTOR" else VOICE_PROFISSIONAL

        for chunk_index, chunk in enumerate(chunks):
            rate, pitch = prosody_for(speaker, chunk, chunk_index, len(chunks))
            segment = work / f"{segment_number:03d}.mp3"
            await synthesize(chunk, voice, rate, pitch, segment)
            merged += AudioSegment.from_file(segment, format="mp3")
            segment_number += 1

            is_last_chunk = chunk_index == len(chunks) - 1
            is_last_turn = turn_index == len(turns) - 1
            if not (is_last_chunk and is_last_turn):
                merged += AudioSegment.silent(
                    duration=TURN_PAUSE_MS if is_last_chunk else pause_after(chunk)
                )

    merged += AudioSegment.silent(duration=ENDING_SILENCE_MS)

    # Pós-processamento leve: reduz picos e estabiliza nível sem esmagar a dinâmica da fala.
    merged = effects.compress_dynamic_range(
        merged,
        threshold=-20.0,
        ratio=2.0,
        attack=8.0,
        release=70.0,
    )
    if merged.dBFS != float("-inf"):
        merged = merged.apply_gain(TARGET_DBFS - merged.dBFS)
    if merged.max_dBFS > -1.2:
        merged = merged.apply_gain(-1.2 - merged.max_dBFS)

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"psp-{number:02d}.mp3"
    merged.export(
        target,
        format="mp3",
        bitrate="128k",
        parameters=["-ac", "1", "-ar", "44100"],
    )

    seconds = len(merged) / 1000
    if not 105 <= seconds <= 300:
        raise RuntimeError(f"Duração fora do intervalo de segurança em {target.name}: {seconds:.1f}s")
    print(f"{target.name}: {seconds:.1f}s | padrão N2")


async def main():
    TMP.mkdir(parents=True, exist_ok=True)
    for number in range(1, 11):
        await build_lesson(number)


if __name__ == "__main__":
    asyncio.run(main())
