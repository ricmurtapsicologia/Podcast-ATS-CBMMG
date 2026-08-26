from __future__ import annotations

"""Remasterização autônoma da Série 1 com fala orgânica e respirada.

Fonte textual: roteiros congelados existentes em roteiros/serie-1.
Nenhuma palavra é reescrita, resumida ou ampliada. Para a síntese, são
inseridos apenas sinais de pontuação prosódica, preservando 100% da sequência
de palavras. Isso devolve respiração e fraseado aos roteiros que foram
congelados praticamente sem pontuação.
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
TMP = ROOT / ".tmp_serie1_organic_v4"
APP = ROOT / "app.js"
INDEX = ROOT / "index.html"

VOICE_INSTRUTOR = "pt-BR-AntonioNeural"
VOICE_PROFISSIONAL = "pt-BR-FranciscaNeural"
BASE_RATE = {VOICE_INSTRUTOR: -7, VOICE_PROFISSIONAL: -4}
BASE_PITCH = {VOICE_INSTRUTOR: -1, VOICE_PROFISSIONAL: 1}

OPENING_SILENCE_MS = 180
ENDING_SILENCE_MS = 340
TARGET_DBFS = -18.0
MAX_CONCURRENT_SYNTH = 8
SYNTH_TIMEOUT_SECONDS = 45
MAX_SYNTH_CHARS = 720
VERSION_TAG = "organic-v4"

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


def lexical_tokens(text: str) -> list[str]:
    """Representação usada no gate: ignora apenas pontuação adicionada."""
    return re.findall(r"[\wÀ-ÿ]+", text.lower(), flags=re.UNICODE)


def breath_units(text: str) -> list[str]:
    """Divide em unidades semânticas curtas, sem mudar palavras ou ordem."""
    text = normalize_text(text)
    words = text.split()
    if len(words) <= MAX_BREATH_WORDS:
        return [text] if text else []

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


def add_prosodic_punctuation(text: str) -> str:
    """Insere apenas pontuação para orientar a voz; nunca altera palavras."""
    text = normalize_text(text)
    if not text:
        return ""

    # Se a transcrição já tem pontuação suficiente, preserva-a.
    punctuation_marks = len(re.findall(r"[.!?;:,…]", text))
    if punctuation_marks >= max(2, len(text.split()) // 25):
        return text

    units = breath_units(text)
    spoken_parts: list[str] = []
    for idx, unit in enumerate(units):
        raw = unit.rstrip()
        if raw.endswith((".", "!", "?", ";", ":", ",", "…")):
            spoken_parts.append(raw)
            continue

        normalized = raw.lower()
        is_question = normalized.startswith(QUESTION_STARTS)
        is_last = idx == len(units) - 1

        if is_question:
            mark = "?"
        elif is_last or (idx + 1) % 3 == 0:
            mark = "."
        else:
            mark = ","
        spoken_parts.append(raw + mark)

    spoken = " ".join(spoken_parts)
    if lexical_tokens(spoken) != lexical_tokens(text):
        raise RuntimeError("Gate lexical falhou ao inserir pontuação prosódica.")
    return spoken


def chunk_spoken_text(text: str) -> list[str]:
    """Agrupa frases em blocos maiores; pausas internas ficam a cargo da pontuação."""
    text = normalize_text(text)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text) if s.strip()]
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        projected = current_len + (1 if current else 0) + len(sentence)
        if current and projected > MAX_SYNTH_CHARS:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len = projected
    if current:
        chunks.append(" ".join(current))
    return chunks


def read_frozen_turns(number: int):
    path = ROTEIROS / f"a1-{number:03d}.txt"
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

        spoken = add_prosodic_punctuation(text)
        source_words.extend(lexical_tokens(text))
        spoken_words.extend(lexical_tokens(spoken))
        turns.extend((voice, chunk) for chunk in chunk_spoken_text(spoken))

    if not turns or source_words != spoken_words:
        raise RuntimeError(f"Gate de integridade lexical falhou no episódio {number:03d}.")

    return turns, len(source_words)


def prosody_for(voice: str, text: str, turn_index: int):
    rate = BASE_RATE[voice]
    pitch = BASE_PITCH[voice]
    normalized = text.strip().lower()

    # Microvariação imperceptível evita ritmo de metrônomo.
    rate += (-1, 0, 0, 1, 0, 0)[turn_index % 6]
    if normalized.startswith(QUESTION_STARTS):
        rate -= 1
        pitch += 1

    rate = max(-12, min(0, rate))
    pitch = max(-4, min(4, pitch))
    return f"{rate:+d}%", f"{pitch:+d}Hz"


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
        rate, pitch = prosody_for(voice, text, idx)
        part = work / f"{idx:03d}.mp3"
        # Só há pausa explícita entre blocos longos; micro-pausas vêm da pontuação.
        pause_ms = 520 if idx < len(turns) - 1 else 0
        sequence.append((part, pause_ms))
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
        turns, word_count = read_frozen_turns(number)
        target, seconds = await synth_episode(number, turns, semaphore)
        quality.append({
            "episode": number,
            "output": target.name,
            "lexical_integrity": 1.0,
            "source_words": word_count,
            "synth_blocks": len(turns),
            "duration_seconds": seconds,
            "audio_profile": "serie-1-organic-v4",
            "base_rate": {"instrutor": -7, "profissional": -4},
            "prosodic_punctuation": True,
        })
        print(f"[{number:03d}] orgânico v4 | blocos={len(turns)} | duração={seconds}s")

    patch_app_urls()
    patch_index_cache()
    (OUT / "quality-organic-v4.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Série 1 concluída no perfil orgânico v4.")


if __name__ == "__main__":
    asyncio.run(main())
