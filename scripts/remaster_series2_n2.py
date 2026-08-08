from __future__ import annotations

"""Remasterização N2 da Série 2 a partir dos MP3s originais.

Objetivos editoriais:
- usar o áudio original como fonte de verdade;
- congelar uma transcrição por episódio;
- preservar a sequência verbal sem reescrita editorial;
- ressintetizar com voz neural pt-BR e prosódia discreta;
- manter os MP3s antigos intactos como backup;
- validar o novo áudio por retranscrição e similaridade textual.
"""

import asyncio
import json
import re
import unicodedata
from difflib import SequenceMatcher
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
MODEL_NAME = "small"
MAX_CHARS = 620
TARGET_DBFS = -18.0
PAUSE_MS = 430
INTERVIEW_EPISODES = {7, 8}


def source_file(number: int) -> Path:
    prefix = f"A2 {number:03d}" if number <= 12 else "A3 013"
    matches = sorted(ROOT.glob(prefix + "*.mp3"))
    if len(matches) != 1:
        raise RuntimeError(f"Esperado 1 MP3 para {prefix}; encontrados {len(matches)}: {matches}")
    return matches[0]


def transcribe(model: WhisperModel, audio: Path):
    segments, info = model.transcribe(
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
    return rows, info


def freeze_transcript(number: int, source: Path, rows) -> str:
    text = " ".join(row["text"] for row in rows).strip()
    ROTEIROS.mkdir(parents=True, exist_ok=True)
    target = ROTEIROS / f"a2-{number:03d}.txt"
    target.write_text(
        f"# Série 2 — Episódio {number:03d}\n"
        f"# Fonte de verdade: {source.name}\n"
        f"# Gerado automaticamente a partir do MP3 original; não editar durante a remasterização N2.\n\n"
        + text + "\n",
        encoding="utf-8",
    )
    return text


def chunks_from_rows(number: int, rows):
    if number in INTERVIEW_EPISODES:
        return [(row["text"], idx % 2) for idx, row in enumerate(rows)]

    chunks = []
    current = []
    current_len = 0
    for row in rows:
        text = row["text"]
        projected = current_len + (1 if current else 0) + len(text)
        if current and projected > MAX_CHARS:
            chunks.append((" ".join(current), 0))
            current = [text]
            current_len = len(text)
        else:
            current.append(text)
            current_len = projected
    if current:
        chunks.append((" ".join(current), 0))
    return chunks


def prosody(index: int, voice_slot: int):
    if voice_slot == 0:
        base_rate, base_pitch = -3, -1
    else:
        base_rate, base_pitch = -1, 1
    rate = base_rate + (-1, 0, 1, 0)[index % 4]
    pitch = base_pitch + (0, 1, 0, -1)[index % 4]
    return f"{rate:+d}%", f"{pitch:+d}Hz"


async def synth_one(text: str, voice: str, rate: str, pitch: str, out: Path):
    for attempt in range(1, 4):
        try:
            comm = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch, volume="+0%")
            await asyncio.wait_for(comm.save(str(out)), timeout=90)
            return
        except Exception:
            if attempt == 3:
                raise
            await asyncio.sleep(attempt)


async def synth_episode(number: int, chunks):
    work = TMP / f"a2-{number:03d}"
    work.mkdir(parents=True, exist_ok=True)
    pieces = []
    for idx, (text, voice_slot) in enumerate(chunks):
        voice = VOICE_A if voice_slot == 0 else VOICE_B
        rate, pitch = prosody(idx, voice_slot)
        part = work / f"{idx:03d}.mp3"
        await synth_one(text, voice, rate, pitch, part)
        pieces.append(part)

    merged = AudioSegment.silent(duration=130)
    for idx, part in enumerate(pieces):
        merged += AudioSegment.from_file(part, format="mp3")
        if idx < len(pieces) - 1:
            merged += AudioSegment.silent(duration=PAUSE_MS)
    merged += AudioSegment.silent(duration=240)

    merged = effects.compress_dynamic_range(merged, threshold=-20.0, ratio=2.0, attack=8.0, release=70.0)
    if merged.dBFS != float("-inf"):
        merged = merged.apply_gain(TARGET_DBFS - merged.dBFS)
    if merged.max_dBFS > -1.2:
        merged = merged.apply_gain(-1.2 - merged.max_dBFS)

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"a2-{number:03d}.mp3"
    merged.export(target, format="mp3", bitrate="128k", parameters=["-ac", "1", "-ar", "44100"])
    return target


def norm_words(text: str):
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.findall(r"[a-z0-9]+", text)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(a=norm_words(a), b=norm_words(b), autojunk=False).ratio()


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
    quality = []

    for number in range(14):
        source = source_file(number)
        print(f"[{number:03d}] transcrevendo {source.name}")
        rows, _ = transcribe(model, source)
        frozen = freeze_transcript(number, source, rows)
        chunks = chunks_from_rows(number, rows)
        print(f"[{number:03d}] sintetizando {len(chunks)} bloco(s) N2")
        target = await synth_episode(number, chunks)

        verify_rows, _ = transcribe(model, target)
        verified = " ".join(row["text"] for row in verify_rows)
        score = similarity(frozen, verified)
        print(f"[{number:03d}] preservação textual ASR: {score:.4f}")
        if score < 0.975:
            raise RuntimeError(f"Gate de preservação textual falhou no episódio {number:03d}: {score:.4f}")
        quality.append({
            "episode": number,
            "source": source.name,
            "output": target.name,
            "similarity": round(score, 4),
            "chunks": len(chunks),
        })

    patch_app_urls()
    (OUT / "quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Série 2 N2 concluída: 14 episódios, roteiros congelados e app.js atualizado.")


if __name__ == "__main__":
    asyncio.run(main())
