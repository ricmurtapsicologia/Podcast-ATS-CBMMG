from __future__ import annotations

"""Hotfix cirúrgico de prosódia do A1-001.

Objetivo: corrigir a sensação de fala acelerada, cadência artificial e ausência de
respiração sem alterar uma única palavra do roteiro canônico. A intervenção
acontece somente na camada de direção de locução: segmentação semântica,
pontuação, rate, pitch, pausas e pós-produção discreta.
"""

import asyncio
import json
import re
import shutil
from pathlib import Path

from pydub import AudioSegment, effects

import remaster_series1_n3 as n3

EPISODE = 1
VERSION = "n3-a1-001-prosody-20260902a"
VOICE = "pt-BR-FranciscaNeural"
REPORT = n3.OUT / "quality-n3.json"
HOTFIX_REPORT = n3.ROOT / "reports" / "a1-001-prosody-hotfix.json"

OPENING_MS = 220
ENDING_MS = 420
TARGET_DBFS = -18.0


def tokens(text: str) -> list[str]:
    return n3.lexical_tokens(text)


def canonical_source() -> str:
    path = n3.ROTEIROS / "a1-001.txt"
    chunks: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("INSTRUTOR:"):
            line = line.split(":", 1)[1].strip()
        chunks.append(line)
    return re.sub(r"\s+", " ", " ".join(chunks)).strip()


# Segmentação curada semanticamente. Só pontuação/capitalização é acrescentada;
# a sequência lexical permanece idêntica ao roteiro congelado.
SEGMENTS = [
    {"text": "Abordagem técnica: comunicação que salva.", "rate": "-12%", "pitch": "-1Hz", "pause": 720, "intent": "title"},
    {"text": "Olá, caros abordadores.", "rate": "-10%", "pitch": "+0Hz", "pause": 760, "intent": "greeting"},
    {"text": "Hoje vamos mergulhar no que chamamos de abordagem técnica,", "rate": "-9%", "pitch": "+0Hz", "pause": 360, "intent": "opening"},
    {"text": "uma das ferramentas mais poderosas que temos para lidar com situações de crise.", "rate": "-10%", "pitch": "-1Hz", "pause": 560, "intent": "explain"},
    {"text": "Mas o que é exatamente essa abordagem?", "rate": "-8%", "pitch": "+1Hz", "pause": 650, "intent": "question"},
    {"text": "É a aplicação da comunicação, tanto verbal quanto não verbal, para estabelecer um vínculo de confiança com o tentante,", "rate": "-10%", "pitch": "-1Hz", "pause": 390, "intent": "definition"},
    {"text": "compreender seus pensamentos e, com empatia, guiá-lo a abandonar o ato autodestrutivo.", "rate": "-11%", "pitch": "-1Hz", "pause": 620, "intent": "definition_resolution"},
    {"text": "E sabe o que faz tudo isso funcionar?", "rate": "-9%", "pitch": "+1Hz", "pause": 520, "intent": "question"},
    {"text": "Cada detalhe importa.", "rate": "-13%", "pitch": "-1Hz", "pause": 650, "intent": "emphasis"},
    {"text": "A forma como nos posicionamos, o tom de voz, o olhar atento, até a inclinação do corpo...", "rate": "-11%", "pitch": "-1Hz", "pause": 460, "intent": "enumeration"},
    {"text": "tudo conta para passar segurança e acolhimento.", "rate": "-11%", "pitch": "-1Hz", "pause": 600, "intent": "resolution"},
    {"text": "Essa combinação de palavras e linguagem corporal transforma o contato em algo genuíno e eficaz.", "rate": "-10%", "pitch": "-1Hz", "pause": 620, "intent": "explain"},
    {"text": "Comunicar é salvar vidas.", "rate": "-13%", "pitch": "-1Hz", "pause": 760, "intent": "key_message"},
    {"text": "E no próximo episódio, vamos explorar ainda mais como palavras e gestos podem ser a ponte para a esperança.", "rate": "-10%", "pitch": "-1Hz", "pause": 560, "intent": "conclusion"},
    {"text": "Não perca.", "rate": "-9%", "pitch": "-1Hz", "pause": 0, "intent": "closing"},
]


def validate_lexical_integrity() -> int:
    source = canonical_source()
    spoken = " ".join(item["text"] for item in SEGMENTS)
    source_tokens = tokens(source)
    spoken_tokens = tokens(spoken)
    if source_tokens != spoken_tokens:
        for idx, (a, b) in enumerate(zip(source_tokens, spoken_tokens)):
            if a != b:
                raise RuntimeError(f"Gate lexical falhou no token {idx}: {a!r} != {b!r}")
        raise RuntimeError(
            f"Gate lexical falhou por tamanho: fonte={len(source_tokens)} síntese={len(spoken_tokens)}"
        )
    return len(source_tokens)


async def synth_segment(item: dict, idx: int, work: Path, sem: asyncio.Semaphore) -> Path:
    out = work / f"{idx:03d}.mp3"
    await n3.synth(item["text"], VOICE, item["rate"], item["pitch"], out, sem)
    return out


async def main() -> None:
    word_count = validate_lexical_integrity()
    if word_count != 143:
        raise RuntimeError(f"Contagem lexical inesperada no A1-001: {word_count}")

    work = n3.TMP / "a1-001-prosody-hotfix"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(2)

    parts = await asyncio.gather(*[
        synth_segment(item, idx, work, sem) for idx, item in enumerate(SEGMENTS)
    ])

    audio = AudioSegment.silent(duration=OPENING_MS)
    for item, part in zip(SEGMENTS, parts):
        rendered = AudioSegment.from_file(part, format="mp3")
        audio += rendered
        if item["pause"]:
            audio += AudioSegment.silent(duration=int(item["pause"]))
    audio += AudioSegment.silent(duration=ENDING_MS)

    # Compressão mais leve que a master anterior para preservar microdinâmica.
    audio = effects.compress_dynamic_range(
        audio,
        threshold=-20.0,
        ratio=1.6,
        attack=12.0,
        release=95.0,
    )
    if audio.dBFS != float("-inf"):
        audio = audio.apply_gain(TARGET_DBFS - audio.dBFS)
    if audio.max_dBFS > -1.2:
        audio = audio.apply_gain(-1.2 - audio.max_dBFS)

    duration_seconds = len(audio) / 1000.0
    wpm = word_count / duration_seconds * 60.0
    if not (62.0 <= duration_seconds <= 78.0):
        raise RuntimeError(f"Duração fora da janela humana esperada: {duration_seconds:.1f}s")
    if not (110.0 <= wpm <= 138.0):
        raise RuntimeError(f"Ritmo fora da janela esperada: {wpm:.1f} palavras/min")

    target = n3.OUT / "a1-001-n3.mp3"
    target.parent.mkdir(parents=True, exist_ok=True)
    audio.export(target, format="mp3", bitrate="128k", parameters=["-ac", "1", "-ar", "44100"])

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    episode = next((e for e in report.get("episodes", []) if e.get("episode") == EPISODE), None)
    if episode is None:
        raise RuntimeError("A1-001 não encontrado em quality-n3.json")

    episode.update({
        "output": target.name,
        "version": VERSION,
        "profile": "N3-C-prosody-humanized",
        "speaker_cast": {"INSTRUTOR": VOICE},
        "voices": [VOICE],
        "turns": len(SEGMENTS),
        "duration_seconds": round(duration_seconds, 1),
        "word_count": word_count,
        "estimated_wpm": round(wpm, 1),
        "prosody_hotfix": {
            "semantic_segmentation": True,
            "prosodic_punctuation": True,
            "contextual_rate": True,
            "contextual_pitch": True,
            "contextual_pauses": True,
            "light_dynamic_compression": True,
            "voice_preserved": VOICE,
        },
        "intents": sorted({item["intent"] for item in SEGMENTS}),
    })
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    app = n3.APP.read_text(encoding="utf-8")
    pattern = r'(a1-001-n3\.mp3\?v=)[^"\\]+'
    app, count = re.subn(pattern, rf'\g<1>{VERSION}', app, count=1)
    if count != 1:
        raise RuntimeError("URL do A1-001 não localizada em app.js")
    n3.APP.write_text(app, encoding="utf-8")

    HOTFIX_REPORT.parent.mkdir(parents=True, exist_ok=True)
    HOTFIX_REPORT.write_text(json.dumps({
        "episode": "A1-001",
        "version": VERSION,
        "voice": VOICE,
        "word_count": word_count,
        "segments": len(SEGMENTS),
        "duration_seconds": round(duration_seconds, 1),
        "estimated_wpm": round(wpm, 1),
        "lexical_integrity": 1.0,
        "goal": "reduzir aceleração, cadência TTS e pausas artificiais",
        "content_changed": False,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    shutil.rmtree(work, ignore_errors=True)
    print(HOTFIX_REPORT.read_text(encoding="utf-8"))


if __name__ == "__main__":
    # A execução automatizada é deliberadamente isolada ao episódio 001.
    asyncio.run(main())
