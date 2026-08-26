from __future__ import annotations

"""Remasterização autônoma da Série 1 com fala orgânica e respirada.

Fonte textual: roteiros congelados existentes em roteiros/serie-1.
Nenhuma palavra é reescrita, resumida ou ampliada. A correção atua apenas em
segmentação respiratória, cadência, prosódia, pausas e acabamento sonoro.
"""

import asyncio
import json
import re
from pathlib import Path

import edge_tts
from pydub import AudioSegment, effects

ROOT = Path(__file__).resolve().parents[1]
ROTEIROS = ROOT / "roteiros" / "serie-1"
OUT = ROOT / "assets" / "audio" / "serie-1"
TMP = ROOT / ".tmp_serie1_organic"
APP = ROOT / "app.js"
INDEX = ROOT / "index.html"

VOICE_INSTRUTOR = "pt-BR-AntonioNeural"
VOICE_PROFISSIONAL = "pt-BR-FranciscaNeural"
BASE_RATE = {VOICE_INSTRUTOR: -8, VOICE_PROFISSIONAL: -5}
BASE_PITCH = {VOICE_INSTRUTOR: -1, VOICE_PROFISSIONAL: 1}

OPENING_SILENCE_MS = 180
ENDING_SILENCE_MS = 340
TARGET_DBFS = -18.0
MAX_CONCURRENT_SYNTH = 6
SYNTH_TIMEOUT_SECONDS = 45
VERSION_TAG = "organic-v3"

MIN_BREATH_WORDS = 9
TARGET_BREATH_WORDS = 14
MAX_BREATH_WORDS = 19

SOFT_BREAK_BEFORE = {
    "mas", "porém", "porem", "contudo", "entretanto", "porque", "quando",
    "enquanto", "então", "entao", "assim", "agora", "portanto", "se",
    "como", "além", "alem", "ainda", "inclusive", "depois", "antes",
}

QUESTION_STARTS = (
    "o que ", "mas o que ", "como ", "por que ", "qual ", "quais ",
    "quem ", "onde ", "quando ", "será ", "sera ", "sabe o que ",
)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_word(word: str) -> str:
    return re.sub(r"^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$", "", word.lower())


def chunk_unpunctuated(text: str) -> list[str]:
    """Cria grupos de respiração sem alterar palavras nem sua ordem."""
    words = text.split()
    if len(words) <= MAX_BREATH_WORDS:
        return [text]

    units: list[str] = []
    start = 0
    total = len(words)

    while total - start > MAX_BREATH_WORDS:
        low = start + MIN_BREATH_WORDS
        high = min(start + MAX_BREATH_WORDS, total)
        target = min(start + TARGET_BREATH_WORDS, high)

        candidates = []
        for idx in range(low, high):
            if clean_word(words[idx]) in SOFT_BREAK_BEFORE:
                candidates.append(idx)

        cut = min(candidates, key=lambda idx: abs(idx - target)) if candidates else target
        if total - cut < 6:
            cut = max(low, total - 7)

        units.append(" ".join(words[start:cut]))
        start = cut

    if start < total:
        units.append(" ".join(words[start:]))

    return [unit for unit in units if unit]


def breath_units(text: str) -> list[str]:
    """Respeita pontuação existente e infere respirações quando ela inexiste."""
    text = normalize_text(text)
    if not text:
        return []

    sentences = [
        part.strip()
        for part in re.split(r"(?<=[.!?…])\s+", text)
        if part.strip()
    ]

    units: list[str] = []
    for sentence in sentences:
        if len(sentence.split()) <= MAX_BREATH_WORDS:
            units.append(sentence)
            continue

        clauses = [
            part.strip()
            for part in re.split(r"(?<=[;:,])\s+", sentence)
            if part.strip()
        ]
        if len(clauses) > 1:
            for clause in clauses:
                units.extend(chunk_unpunctuated(clause))
        else:
            units.extend(chunk_unpunctuated(sentence))

    return units


def read_frozen_turns(number: int):
    path = ROTEIROS / f"a1-{number:03d}.txt"
    if not path.exists():
        raise RuntimeError(f"Roteiro congelado ausente: {path}")

    turns = []
    frozen_parts = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("PROFISSIONAL:"):
            voice = VOICE_PROFISSIONAL
            text = line.split(":", 1)[1].strip()
        elif line.startswith("INSTRUTOR:"):
            voice = VOICE_INSTRUTOR
            text = line.split(":", 1)[1].strip()
        else:
            voice = VOICE_INSTRUTOR
            text = line

        if not text:
            continue
        frozen_parts.append(text)
        turns.extend((voice, unit) for unit in breath_units(text))

    frozen = normalize_text(" ".join(frozen_parts))
    rebuilt = normalize_text(" ".join(text for _, text in turns))
    if not frozen or frozen != rebuilt:
        raise RuntimeError(f"Gate de integridade textual falhou no episódio {number:03d}.")
    return turns, frozen


def prosody_for(voice: str, text: str, turn_index: int):
    rate = BASE_RATE[voice]
    pitch = BASE_PITCH[voice]
    normalized = text.strip().lower()
    stripped = text.rstrip()

    rate += (-1, 0, 0, 1, 0, 0)[turn_index % 6]

    inferred_question = normalized.startswith(QUESTION_STARTS)
    if stripped.endswith("?") or inferred_question:
        rate -= 1
        pitch += 2
        pause_ms = 700
    elif stripped.endswith("…"):
        rate -= 2
        pause_ms = 820
    elif stripped.endswith("!"):
        pause_ms = 640
    elif stripped.endswith("."):
        pause_ms = 570
    elif stripped.endswith(":"):
        pause_ms = 450
    elif stripped.endswith(";"):
        pause_ms = 400
    elif stripped.endswith(","):
        pause_ms = 310
    else:
        pause_ms = 390

    if normalized.startswith((
        "guarde", "em resumo", "pense", "imagine", "o ponto", "observe",
        "lembre", "repare", "atenção", "atencao",
    )):
        rate -= 2
        pause_ms += 90

    rate = max(-13, min(0, rate))
    pitch = max(-4, min(4, pitch))
    return f"{rate:+d}%", f"{pitch:+d}Hz", pause_ms


async def synthesize(text: str, voice: str, rate: str, pitch: str, output: Path, semaphore: asyncio.Semaphore):
    async with semaphore:
        for attempt in range(1, 4):
            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                    volume="+0%",
                )
                await asyncio.wait_for(communicate.save(str(output)), timeout=SYNTH_TIMEOUT_SECONDS)
                return
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(0.8 * attempt)


async def synth_episode(number: int, turns, semaphore: asyncio.Semaphore):
    work = TMP / f"a1-{number:03d}"
    work.mkdir(parents=True, exist_ok=True)
    tasks = []
    sequence = []

    for idx, (voice, text) in enumerate(turns):
        rate, pitch, pause_ms = prosody_for(voice, text, idx)
        part = work / f"{idx:03d}.mp3"
        sequence.append((part, 0 if idx == len(turns) - 1 else pause_ms))
        tasks.append(synthesize(text, voice, rate, pitch, part, semaphore))

    await asyncio.gather(*tasks)

    merged = AudioSegment.silent(duration=OPENING_SILENCE_MS)
    for part, pause_ms in sequence:
        merged += AudioSegment.from_file(part, format="mp3")
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
    target = OUT / f"a1-{number:03d}-{VERSION_TAG}.mp3"
    merged.export(target, format="mp3", bitrate="128k", parameters=["-ac", "1", "-ar", "44100"])
    return target, round(len(merged) / 1000, 1)


def patch_app_urls():
    content = APP.read_text(encoding="utf-8")
    block_match = re.search(r"const AUDIOS=\{1:\[(.*?)\],2:\[", content, re.S)
    if not block_match:
        raise RuntimeError("Bloco da Série 1 não localizado em app.js")

    block = block_match.group(1)
    entries = list(re.finditer(r'\{title:"([^"]+)",url:"([^"]+)"\}', block))
    if len(entries) != 21:
        raise RuntimeError(f"Esperados 21 episódios na Série 1; encontrados {len(entries)}")

    new_block = block
    for idx, match in reversed(list(enumerate(entries, start=1))):
        title = match.group(1)
        replacement = f'{{title:"{title}",url:"assets/audio/serie-1/a1-{idx:03d}-{VERSION_TAG}.mp3"}}'
        new_block = new_block[:match.start()] + replacement + new_block[match.end():]

    content = content[:block_match.start(1)] + new_block + content[block_match.end(1):]
    APP.write_text(content, encoding="utf-8")


def patch_index_cache():
    content = INDEX.read_text(encoding="utf-8")
    content = re.sub(
        r'app\.js(?:\?v=[^"\']+)?',
        f'app.js?v=20260825-s1-{VERSION_TAG}',
        content,
        count=1,
    )
    INDEX.write_text(content, encoding="utf-8")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SYNTH)
    quality = []

    for number in range(1, 22):
        turns, frozen = read_frozen_turns(number)
        target, seconds = await synth_episode(number, turns, semaphore)
        quality.append({
            "episode": number,
            "output": target.name,
            "text_integrity": 1.0,
            "frozen_characters": len(frozen),
            "turns": len(turns),
            "voices": sorted(set(voice for voice, _ in turns)),
            "duration_seconds": seconds,
            "audio_profile": "serie-1-organic-v3",
            "breath_pause_ms": 390,
            "base_rate": {"instrutor": -8, "profissional": -5},
        })
        print(f"[{number:03d}] orgânico v3 | turnos={len(turns)} | duração={seconds}s")

    patch_app_urls()
    patch_index_cache()
    (OUT / "quality-organic-v3.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Série 1 concluída no perfil orgânico v3.")


if __name__ == "__main__":
    asyncio.run(main())
