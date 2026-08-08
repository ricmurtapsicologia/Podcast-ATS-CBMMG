from __future__ import annotations

"""Ressíntese da Série 2 com paridade sonora real com a Série 3.

Regras editoriais:
- usa os roteiros congelados já extraídos dos MP3s originais;
- não reescreve, resume ou amplia o texto;
- usa a mesma família de vozes, cadência, pausas e pós-processamento da Série 3;
- sintetiza em unidades curtas de fala para evitar o efeito de locução robótica;
- grava com novos nomes de arquivo para impedir reaproveitamento de cache.
"""

import asyncio
import json
import re
from pathlib import Path

import edge_tts
from pydub import AudioSegment, effects

ROOT = Path(__file__).resolve().parents[1]
ROTEIROS = ROOT / "roteiros" / "serie-2"
OUT = ROOT / "assets" / "audio" / "serie-2"
TMP = ROOT / ".tmp_serie2_s3_parity"
APP = ROOT / "app.js"

VOICE_INSTRUTOR = "pt-BR-AntonioNeural"
VOICE_PROFISSIONAL = "pt-BR-FranciscaNeural"
BASE_RATE = {VOICE_INSTRUTOR: -4, VOICE_PROFISSIONAL: -1}
BASE_PITCH = {VOICE_INSTRUTOR: -1, VOICE_PROFISSIONAL: 1}

OPENING_SILENCE_MS = 130
ENDING_SILENCE_MS = 240
TARGET_DBFS = -18.0
MAX_CONCURRENT_SYNTH = 4
SYNTH_TIMEOUT_SECONDS = 35
MAX_UTTERANCE_CHARS = 260
VERSION_TAG = "s3v2"


def read_frozen_text(number: int) -> str:
    path = ROTEIROS / f"a2-{number:03d}.txt"
    if not path.exists():
        raise RuntimeError(f"Roteiro congelado ausente: {path}")
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("#")]
    text = re.sub(r"\s+", " ", " ".join(lines)).strip()
    if not text:
        raise RuntimeError(f"Roteiro vazio: {path}")
    return text


def split_long_unit(text: str) -> list[str]:
    if len(text) <= MAX_UTTERANCE_CHARS:
        return [text.strip()]

    parts = re.split(r"(?<=[,;:])\s+", text)
    chunks: list[str] = []
    current = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        candidate = f"{current} {part}".strip() if current else part
        if current and len(candidate) > MAX_UTTERANCE_CHARS:
            chunks.append(current)
            current = part
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def speech_units(text: str) -> list[str]:
    # Mesma lógica perceptiva da Série 3: fala curta + pausa + nova decisão de prosódia.
    sentences = re.split(r"(?<=[.!?…])\s+", text)
    units: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:
            units.extend(split_long_unit(sentence))
    if not units:
        raise RuntimeError("Nenhuma unidade de fala gerada.")

    # Gate de conteúdo: apenas espaços de junção podem mudar.
    rebuilt = re.sub(r"\s+", " ", " ".join(units)).strip()
    expected = re.sub(r"\s+", " ", text).strip()
    if rebuilt != expected:
        raise RuntimeError("Gate de integridade textual falhou ao segmentar o roteiro.")
    return units


def voice_for_episode(number: int) -> str:
    # Mantém a mesma família de vozes da Série 3. Nos episódios originalmente
    # apresentados como entrevistas, usa a voz profissional feminina de forma estável,
    # sem inventar alternância de interlocutores sem diarização confiável.
    return VOICE_PROFISSIONAL if number in {7, 8} else VOICE_INSTRUTOR


def prosody_for(voice: str, text: str, turn_index: int) -> tuple[str, str, int]:
    # Espelha generate_psp_audio.py (Série 3).
    rate = BASE_RATE[voice]
    pitch = BASE_PITCH[voice]
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


async def synthesize(text: str, voice: str, rate: str, pitch: str, output: Path, semaphore: asyncio.Semaphore):
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
                await asyncio.wait_for(communicate.save(str(output)), timeout=SYNTH_TIMEOUT_SECONDS)
                return
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(0.8 * attempt)


async def build_episode(number: int, semaphore: asyncio.Semaphore):
    text = read_frozen_text(number)
    units = speech_units(text)
    voice = voice_for_episode(number)
    work = TMP / f"a2-{number:03d}"
    work.mkdir(parents=True, exist_ok=True)

    sequence = []
    tasks = []
    for idx, unit in enumerate(units):
        rate, pitch, pause_ms = prosody_for(voice, unit, idx)
        segment = work / f"{idx:03d}.mp3"
        sequence.append((segment, 0 if idx == len(units) - 1 else pause_ms))
        tasks.append(synthesize(unit, voice, rate, pitch, segment, semaphore))

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
    target = OUT / f"a2-{number:03d}-{VERSION_TAG}.mp3"
    merged.export(target, format="mp3", bitrate="128k", parameters=["-ac", "1", "-ar", "44100"])
    return {
        "episode": number,
        "output": target.name,
        "text_integrity": 1.0,
        "speech_units": len(units),
        "duration_seconds": round(len(merged) / 1000, 1),
        "voice": voice,
        "audio_profile": "serie-3-parity",
    }


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
        replacement = f'{{title:"{title}",url:"assets/audio/serie-2/a2-{idx:03d}-{VERSION_TAG}.mp3"}}'
        new_block = new_block[:match.start()] + replacement + new_block[match.end():]

    content = content[:block_match.start(1)] + new_block + content[block_match.end(1):]
    APP.write_text(content, encoding="utf-8")


async def main():
    TMP.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SYNTH)
    quality = []
    for number in range(14):
        print(f"[{number:03d}] ressintetizando com paridade Série 3")
        quality.append(await build_episode(number, semaphore))

    patch_app_urls()
    (OUT / "quality-s3-parity.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Série 2 concluída com o mesmo perfil sonoro da Série 3.")


if __name__ == "__main__":
    asyncio.run(main())
