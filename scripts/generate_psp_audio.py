from __future__ import annotations

# Gerador oficial dos MP3s da Série 3 — execução validada por pull request.
import asyncio
import re
from pathlib import Path

import edge_tts
from pydub import AudioSegment

ROOT = Path(__file__).resolve().parents[1]
ROTEIROS = ROOT / "roteiros" / "serie-3"
OUT = ROOT / "assets" / "audio" / "serie-3"
TMP = ROOT / ".tmp_psp_audio"

VOICE_INSTRUTOR = "pt-BR-AntonioNeural"
VOICE_PROFISSIONAL = "pt-BR-FranciscaNeural"
RATE_INSTRUTOR = "-7%"
RATE_PROFISSIONAL = "-3%"
PAUSE_MS = 380

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


async def synthesize(text: str, voice: str, rate: str, output: Path):
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume="+0%")
    await communicate.save(str(output))


async def build_lesson(number: int):
    script = ROTEIROS / f"psp-{number:02d}.md"
    turns = read_turns(script)
    work = TMP / f"psp-{number:02d}"
    work.mkdir(parents=True, exist_ok=True)

    pieces = []
    for idx, (speaker, text) in enumerate(turns):
        segment = work / f"{idx:02d}.mp3"
        if speaker == "INSTRUTOR":
            await synthesize(text, VOICE_INSTRUTOR, RATE_INSTRUTOR, segment)
        else:
            await synthesize(text, VOICE_PROFISSIONAL, RATE_PROFISSIONAL, segment)
        pieces.append(segment)

    merged = AudioSegment.empty()
    pause = AudioSegment.silent(duration=PAUSE_MS)
    for idx, piece in enumerate(pieces):
        merged += AudioSegment.from_file(piece, format="mp3")
        if idx < len(pieces) - 1:
            merged += pause

    if merged.max_dBFS != float("-inf"):
        merged = merged.apply_gain(-1.5 - merged.max_dBFS)

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"psp-{number:02d}.mp3"
    merged.export(target, format="mp3", bitrate="96k", parameters=["-ac", "1", "-ar", "44100"])
    seconds = len(merged) / 1000
    if not 120 <= seconds <= 240:
        raise RuntimeError(f"Duração fora do alvo em {target.name}: {seconds:.1f}s")
    print(f"{target.name}: {seconds:.1f}s")


async def main():
    TMP.mkdir(parents=True, exist_ok=True)
    for number in range(1, 11):
        await build_lesson(number)


if __name__ == "__main__":
    asyncio.run(main())
