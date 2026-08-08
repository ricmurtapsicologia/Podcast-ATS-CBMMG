from __future__ import annotations

"""Geração dos MP3s da Série 3 — padrão de áudio N2.

O N2 preserva integralmente o texto narrado e melhora a entrega por:
- vozes neurais pt-BR já validadas no projeto;
- prosódia variável por fala, sem reescrita;
- pausas contextuais entre interlocutores;
- compressão leve e normalização de nível;
- geração concorrente limitada, com timeout e retentativas.
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
BASE_RATE = {"INSTRUTOR": -4, "PROFISSIONAL": -1}
BASE_PITCH = {"INSTRUTOR": -1, "PROFISSIONAL": 1}

OPENING_SILENCE_MS = 130
ENDING_SILENCE_MS = 240
TARGET_DBFS = -18.0
MAX_CONCURRENT_SYNTH = 4
SYNTH_TIMEOUT_SECONDS = 35
PATTERN = re.compile(r"^\*\*(INSTRUTOR|PROFISSIONAL):\*\*\s*(.+)$")


def read_turns(path: Path):
    turns = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = PATTERN.match(line.strip())
        if match:
            turns.append((match.group(1), match.group(2).strip()))
    if not turns:
        raise RuntimeError(f"Nenhuma fala encontrada em {path}")
    return turns


def prosody_for(speaker: str, text: str, turn_index: int) -> tuple[str, str, int]:
    rate = BASE_RATE[speaker]
    pitch = BASE_PITCH[speaker]
    normalized = text.strip().lower()

    if text.rstrip().endswith("?"):
        rate += 2
        pitch += 2
    if normalized.startswith(("guarde", "em resumo", "pense", "imagine", "o ponto")):
        rate -= 2
    rate += (-1, 0, 1, 0)[turn_index % 4]

    if text.rstrip().endswith("?"):
        pause_ms = 560
    elif text.rstrip().endswith("!"):
        pause_ms = 500
    else:
        pause_ms = 520

    rate = max(-10, min(4, rate))
    pitch = max(-4, min(4, pitch))
    return f"{rate:+d}%", f"{pitch:+d}Hz", pause_ms


async def synthesize(text, voice, rate, pitch, output, semaphore):
    async with semaphore:
        for attempt in range(1, 4):
            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate=rate,
                    volume="+0%",
                    pitch=pitch,
                )
                await asyncio.wait_for(
                    communicate.save(str(output)),
                    timeout=SYNTH_TIMEOUT_SECONDS,
                )
                return
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(0.8 * attempt)


async def build_lesson(number: int, semaphore: asyncio.Semaphore):
    script = ROTEIROS / f"psp-{number:02d}.md"
    turns = read_turns(script)
    work = TMP / f"psp-{number:02d}"
    work.mkdir(parents=True, exist_ok=True)

    sequence = []
    tasks = []

    for turn_index, (speaker, text) in enumerate(turns):
        voice = VOICE_INSTRUTOR if speaker == "INSTRUTOR" else VOICE_PROFISSIONAL
        rate, pitch, pause_ms = prosody_for(speaker, text, turn_index)
        segment = work / f"{turn_index:03d}.mp3"
        sequence.append((segment, 0 if turn_index == len(turns) - 1 else pause_ms))
        tasks.append(synthesize(text, voice, rate, pitch, segment, semaphore))

    await asyncio.gather(*tasks)

    merged = AudioSegment.silent(duration=OPENING_SILENCE_MS)
    for segment, pause_ms in sequence:
        merged += AudioSegment.from_file(segment, format="mp3")
        if pause_ms:
            merged += AudioSegment.silent(duration=pause_ms)
    merged += AudioSegment.silent(duration=ENDING_SILENCE_MS)

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
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SYNTH)
    for number in range(1, 11):
        await build_lesson(number, semaphore)


if __name__ == "__main__":
    asyncio.run(main())
