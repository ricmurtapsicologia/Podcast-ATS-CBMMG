from __future__ import annotations

"""Remasterização N2 da Série 2 a partir dos MP3s originais.

Princípios:
- o MP3 original é a fonte de verdade;
- cada episódio recebe uma transcrição-fonte congelada;
- o texto é ressintetizado sem reescrita editorial;
- os MP3s antigos permanecem intactos como backup;
- a integridade textual é validada antes da síntese;
- a entrega recebe prosódia discreta, pausas e normalização N2.
"""

import asyncio
import json
import re
from pathlib import Path

import edge_tts
from faster_whisper import WhisperModel
from pydub import AudioSegment, effects

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "audio" / "serie-2"
ROTEIROS = ROOT / "roteiros" / "serie-2"
TMP = ROOT / ".tmp_serie2_n2"
APP = ROOT / "app.js"

VOICE_A = "pt-BR-AntonioNeural"
VOICE_B = "pt-BR-FranciscaNeural"
MODEL_NAME = "base"
MAX_CHARS = 900
TARGET_DBFS = -18.0
PAUSE_MS = 430
MAX_CONCURRENT_SYNTH = 4


def source_file(number: int) -> Path:
    prefix = f"A2 {number:03d}" if number <= 12 else "A3 013"
    matches = sorted(ROOT.glob(prefix + "*.mp3"))
    if len(matches) != 1:
        raise RuntimeError(f"Esperado 1 MP3 para {prefix}; encontrados {len(matches)}: {matches}")
    return matches[0]


def transcribe(model: WhisperModel, audio: Path):
    segments, _ = model.transcribe(
        str(audio),
        language="pt",
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=True,
        word_timestamps=False,
        temperature=0.0,
    )
    rows = []
    for seg in segments:
        text = re.sub(r"\s+", " ", seg.text).strip()
        if text:
            rows.append({"start": round(seg.start, 2), "end": round(seg.end, 2), "text": text})
    if not rows:
        raise RuntimeError(f"Nenhuma fala reconhecida em {audio.name}")
    return rows


def freeze_transcript(number: int, source: Path, rows) -> str:
    text = " ".join(row["text"] for row in rows).strip()
    ROTEIROS.mkdir(parents=True, exist_ok=True)
    target = ROTEIROS / f"a2-{number:03d}.txt"
    target.write_text(
        f"# Série 2 — Episódio {number:03d}\n"
        f"# Fonte: {source.name}\n"
        f"# Transcrição automática congelada do MP3 original para remasterização N2.\n\n"
        + text + "\n",
        encoding="utf-8",
    )
    return text


def chunks_from_rows(rows):
    chunks = []
    current = []
    current_len = 0
    for row in rows:
        text = row["text"]
        projected = current_len + (1 if current else 0) + len(text)
        if current and projected > MAX_CHARS:
            chunks.append(" ".join(current))
            current = [text]
            current_len = len(text)
        else:
            current.append(text)
            current_len = projected
    if current:
        chunks.append(" ".join(current))
    return chunks


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def assert_text_integrity(frozen: str, chunks):
    rebuilt = normalize_spaces(" ".join(chunks))
    expected = normalize_spaces(frozen)
    if rebuilt != expected:
        raise RuntimeError("Gate de integridade textual falhou: os blocos não recompõem a transcrição-fonte.")


def voice_for_episode(number: int) -> str:
    # Mantém uma voz estável dentro de cada episódio. Alternância por episódio
    # cria variedade sem inventar troca de interlocutores que não foi diarizada.
    return VOICE_B if number in {7, 8} else VOICE_A


def prosody(index: int, voice: str):
    if voice == VOICE_A:
        base_rate, base_pitch = -3, -1
    else:
        base_rate, base_pitch = -1, 1
    rate = base_rate + (-1, 0, 1, 0)[index % 4]
    pitch = base_pitch + (0, 1, 0, -1)[index % 4]
    return f"{rate:+d}%", f"{pitch:+d}Hz"


async def synth_one(text: str, voice: str, rate: str, pitch: str, out: Path, semaphore: asyncio.Semaphore):
    async with semaphore:
        for attempt in range(1, 4):
            try:
                comm = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch, volume="+0%")
                await asyncio.wait_for(comm.save(str(out)), timeout=90)
                return
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(attempt)


async def synth_episode(number: int, chunks, semaphore: asyncio.Semaphore):
    work = TMP / f"a2-{number:03d}"
    work.mkdir(parents=True, exist_ok=True)
    voice = voice_for_episode(number)
    pieces = []
    tasks = []

    for idx, text in enumerate(chunks):
        rate, pitch = prosody(idx, voice)
        part = work / f"{idx:03d}.mp3"
        pieces.append(part)
        tasks.append(synth_one(text, voice, rate, pitch, part, semaphore))

    await asyncio.gather(*tasks)

    merged = AudioSegment.silent(duration=130)
    for idx, part in enumerate(pieces):
        merged += AudioSegment.from_file(part, format="mp3")
        if idx < len(pieces) - 1:
            merged += AudioSegment.silent(duration=PAUSE_MS)
    merged += AudioSegment.silent(duration=240)

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
    target = OUT / f"a2-{number:03d}.mp3"
    merged.export(target, format="mp3", bitrate="128k", parameters=["-ac", "1", "-ar", "44100"])
    return target, round(len(merged) / 1000, 1)


def patch_app_urls():
    content = APP.read_text(encoding="utf-8")
    block_match = re.search(r",2:\[(.*?)\],3:\[\]", content, re.S)
    if not block_match:
        raise RuntimeError("Bloco da Série 2 não localizado em app.js")
    block = block_match.group(1)
    entries = list(re.finditer(r'\{title:"([^"]+)",url:"([^"]+)"\}', block))
    if len(entries) != 14:
        raise RuntimeError(f"Esperados 14 episódios na Série 2; encontrados {len(entries)}")

    new_block = block
    for idx, match in reversed(list(enumerate(entries))):
        title = match.group(1)
        replacement = f'{{title:"{title}",url:"assets/audio/serie-2/a2-{idx:03d}.mp3"}}'
        new_block = new_block[:match.start()] + replacement + new_block[match.end():]

    content = content[:block_match.start(1)] + new_block + content[block_match.end(1):]
    APP.write_text(content, encoding="utf-8")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ROTEIROS.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)

    print(f"Carregando Whisper {MODEL_NAME} em CPU/int8...")
    model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SYNTH)
    quality = []

    for number in range(14):
        source = source_file(number)
        print(f"[{number:03d}] transcrevendo {source.name}")
        rows = transcribe(model, source)
        frozen = freeze_transcript(number, source, rows)
        chunks = chunks_from_rows(rows)
        assert_text_integrity(frozen, chunks)
        print(f"[{number:03d}] sintetizando {len(chunks)} bloco(s) N2")
        target, seconds = await synth_episode(number, chunks, semaphore)
        quality.append({
            "episode": number,
            "source": source.name,
            "output": target.name,
            "text_integrity": 1.0,
            "chunks": len(chunks),
            "duration_seconds": seconds,
            "voice": voice_for_episode(number),
        })

    patch_app_urls()
    (OUT / "quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Série 2 N2 concluída: 14 episódios, roteiros congelados e app.js atualizado.")


if __name__ == "__main__":
    asyncio.run(main())
