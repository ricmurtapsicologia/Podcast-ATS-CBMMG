from __future__ import annotations

"""Ajustes de produção do N3 sem tocar na camada canônica.

Este runner refina somente:
- segmentação semântica: evita blocos longos e excesso de microcortes;
- QA de silêncio: considera como gap excessivo apenas pausas realmente longas;
- reutilização de candidatos A/B já sintetizados quando aplicável.

Nenhuma palavra do texto canônico é alterada.
"""

import asyncio
import json
import re
import subprocess
from pathlib import Path

from pydub import AudioSegment, silence

import n3_pipeline as p

MIN_WORDS = 24
MAX_WORDS = 42
HARD_MAX_WORDS = 52


def split_by_words(text: str, max_words: int = MAX_WORDS) -> list[str]:
    words = text.split()
    if len(words) <= HARD_MAX_WORDS:
        return [text.strip()]
    chunks = []
    for start in range(0, len(words), max_words):
        chunks.append(' '.join(words[start:start + max_words]))
    return chunks


def refined_atoms(text: str) -> list[str]:
    atoms: list[str] = []
    for sentence in p.split_sentences(text):
        if len(sentence.split()) <= HARD_MAX_WORDS:
            atoms.append(sentence)
            continue
        clauses = [x.strip() for x in re.split(r'(?<=[;:])\s+|(?<=,)\s+', sentence) if x.strip()]
        if len(clauses) <= 1:
            atoms.extend(split_by_words(sentence))
            continue
        for clause in clauses:
            atoms.extend(split_by_words(clause))
    return atoms


def refined_group_units(text: str) -> list[str]:
    atoms = refined_atoms(text)
    if not atoms:
        return [p.normalize_text(text)]

    out: list[str] = []
    current: list[str] = []
    words = 0

    for atom in atoms:
        n = len(atom.split())
        projected = words + n
        if current and projected > MAX_WORDS and words >= MIN_WORDS:
            out.append(p.normalize_text(' '.join(current)))
            current, words = [], 0
        current.append(atom)
        words += n
        if words >= MAX_WORDS:
            out.append(p.normalize_text(' '.join(current)))
            current, words = [], 0

    if current:
        tail = p.normalize_text(' '.join(current))
        if out and len(tail.split()) < 12 and len(out[-1].split()) + len(tail.split()) <= HARD_MAX_WORDS:
            out[-1] = p.normalize_text(out[-1] + ' ' + tail)
        else:
            out.append(tail)

    rebuilt = p.normalize_text(' '.join(out))
    expected = p.normalize_text(text)
    if rebuilt != expected:
        raise RuntimeError('Segmentação refinada alterou o texto canônico.')
    return out


def refined_probe_audio(path: Path) -> dict:
    probe = subprocess.run([
        'ffprobe', '-v', 'error', '-show_entries',
        'format=duration,bit_rate:stream=sample_rate,channels',
        '-of', 'json', str(path)
    ], capture_output=True, text=True, check=True)
    data = json.loads(probe.stdout)
    stream = data.get('streams', [{}])[0]
    fmt = data.get('format', {})
    audio = AudioSegment.from_file(path)

    # O N2 da Série 3, já validado perceptivamente, possui pausas naturais >1 s.
    # Para o gate N3, só tratamos como "gap longo" silêncios contínuos >=2,2 s.
    gaps = silence.detect_silence(audio, min_silence_len=2200, silence_thresh=-50)
    gap_ms = sum(end - start for start, end in gaps)
    lufs, peak = p.parse_ebur128(path)

    return {
        'duration_seconds': round(float(fmt.get('duration', 0.0)), 2),
        'sample_rate': int(stream.get('sample_rate', 0) or 0),
        'channels': int(stream.get('channels', 0) or 0),
        'bitrate': int(fmt.get('bit_rate', 0) or 0),
        'lufs_integrated': lufs,
        'true_peak_dbfs': peak,
        'long_silence_ratio': round(gap_ms / max(1, len(audio)), 4),
    }


_original_synth_episode_edge = p.synth_episode_edge


async def reuse_or_synthesize(direction: dict, out: Path) -> None:
    # Reutiliza apenas candidato da fase A/B já versionado. Na fase full os nomes -n3
    # ainda não existem, portanto todos os 45 episódios são sintetizados de novo.
    if out.exists() and 'candidate-n3' in out.parts:
        return
    await _original_synth_episode_edge(direction, out)


p.group_units = refined_group_units
p.probe_audio = refined_probe_audio
p.synth_episode_edge = reuse_or_synthesize
p.TARGET_MIN_WORDS = MIN_WORDS
p.TARGET_MAX_WORDS = MAX_WORDS
p.ABS_MAX_WORDS = HARD_MAX_WORDS


if __name__ == '__main__':
    asyncio.run(p.main())
