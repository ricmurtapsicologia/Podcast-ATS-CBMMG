from __future__ import annotations

"""Ressíntese da Série 2 com paridade sonora real com a Série 3.

Regras editoriais:
- usa os roteiros congelados já extraídos dos MP3s originais;
- não resume nem amplia o conteúdo;
- usa a mesma família de vozes, a mesma função de prosódia, pausas e pós-processamento da Série 3;
- cria turnos de tamanho semelhante aos da Série 3, evitando tanto blocos enormes quanto fala picotada;
- usa duas vozes apenas em episódios originalmente dialogados e somente quando a estrutura textual permite distingui-las;
- grava novos nomes de arquivo para impedir reaproveitamento de cache.
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
TMP = ROOT / ".tmp_serie2_s3_parity_v3"
APP = ROOT / "app.js"

VOICE_INSTRUTOR = "pt-BR-AntonioNeural"
VOICE_PROFISSIONAL = "pt-BR-FranciscaNeural"
BASE_RATE = {VOICE_INSTRUTOR: -4, VOICE_PROFISSIONAL: -1}
BASE_PITCH = {VOICE_INSTRUTOR: -1, VOICE_PROFISSIONAL: 1}

OPENING_SILENCE_MS = 130
ENDING_SILENCE_MS = 240
TARGET_DBFS = -18.0
MAX_CONCURRENT_SYNTH = 4
SYNTH_TIMEOUT_SECONDS = 40
MAX_TURN_CHARS = 560
VERSION_TAG = "s3v3"
DIALOGUE_EPISODES = {7, 8, 9}


def read_frozen_text(number: int) -> str:
    path = ROTEIROS / f"a2-{number:03d}.txt"
    if not path.exists():
        raise RuntimeError(f"Roteiro congelado ausente: {path}")
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("#")]
    text = re.sub(r"\s+", " ", " ".join(lines)).strip()
    if not text:
        raise RuntimeError(f"Roteiro vazio: {path}")
    return text


def sentences_from(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text) if s.strip()]


def join_gate(text: str, turns: list[tuple[str, str]]):
    rebuilt = re.sub(r"\s+", " ", " ".join(t for _, t in turns)).strip()
    expected = re.sub(r"\s+", " ", text).strip()
    if rebuilt != expected:
        raise RuntimeError("Gate de integridade textual falhou ao organizar os turnos.")


def chunk_narration(sentences: list[str], voice: str) -> list[tuple[str, str]]:
    turns: list[tuple[str, str]] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        projected = current_len + (1 if current else 0) + len(sentence)
        # Perguntas ficam como turnos próprios para receber a mesma inflexão da Série 3.
        if sentence.endswith("?"):
            if current:
                turns.append((voice, " ".join(current)))
                current, current_len = [], 0
            turns.append((voice, sentence))
            continue
        if current and projected > MAX_TURN_CHARS:
            turns.append((voice, " ".join(current)))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len = projected
    if current:
        turns.append((voice, " ".join(current)))
    return turns


def looks_like_host(sentence: str) -> bool:
    n = sentence.strip().lower()
    return sentence.endswith("?") or n.startswith((
        "programa ", "estamos de volta", "entrevistador", "obrigad", "doutor", "dra.", "dr. ",
        "no próximo episódio", "no proximo episódio", "no proximo episodio", "até breve", "ate breve",
    ))


def dialogue_turns(sentences: list[str]) -> list[tuple[str, str]]:
    """Organiza entrevista sem inventar conteúdo.

    Pergunta = voz do instrutor/apresentador. Respostas seguintes = voz profissional,
    até a próxima pergunta. Aberturas/encerramentos reconhecíveis permanecem com o apresentador.
    """
    turns: list[tuple[str, str]] = []
    current_voice = VOICE_INSTRUTOR
    current: list[str] = []
    current_len = 0

    def flush():
        nonlocal current, current_len
        if current:
            turns.append((current_voice, " ".join(current)))
            current, current_len = [], 0

    for sentence in sentences:
        if looks_like_host(sentence):
            flush()
            turns.append((VOICE_INSTRUTOR, sentence))
            current_voice = VOICE_PROFISSIONAL if sentence.endswith("?") else VOICE_INSTRUTOR
            continue

        projected = current_len + (1 if current else 0) + len(sentence)
        if current and projected > MAX_TURN_CHARS:
            flush()
        current.append(sentence)
        current_len = sum(len(x) for x in current) + max(0, len(current) - 1)

    flush()
    return turns


def build_turns(number: int, text: str) -> list[tuple[str, str]]:
    sentences = sentences_from(text)
    if number in DIALOGUE_EPISODES:
        turns = dialogue_turns(sentences)
    else:
        turns = chunk_narration(sentences, VOICE_INSTRUTOR)
    if not turns:
        raise RuntimeError("Nenhum turno de fala gerado.")
    join_gate(text, turns)
    return turns


def prosody_for(voice: str, text: str, turn_index: int) -> tuple[str, str, int]:
    # Espelha a função usada em generate_psp_audio.py (Série 3).
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
    turns = build_turns(number, text)
    work = TMP / f"a2-{number:03d}"
    work.mkdir(parents=True, exist_ok=True)

    sequence = []
    tasks = []
    voices_used = []
    for idx, (voice, turn) in enumerate(turns):
        rate, pitch, pause_ms = prosody_for(voice, turn, idx)
        segment = work / f"{idx:03d}.mp3"
        sequence.append((segment, 0 if idx == len(turns) - 1 else pause_ms))
        voices_used.append(voice)
        tasks.append(synthesize(turn, voice, rate, pitch, segment, semaphore))

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
        "turns": len(turns),
        "duration_seconds": round(len(merged) / 1000, 1),
        "voices": sorted(set(voices_used)),
        "audio_profile": "serie-3-parity-v3",
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
        print(f"[{number:03d}] ressintetizando com paridade Série 3 v3")
        quality.append(await build_episode(number, semaphore))

    patch_app_urls()
    (OUT / "quality-s3-parity.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Série 2 concluída com perfil sonoro Série 3 v3.")


if __name__ == "__main__":
    asyncio.run(main())
