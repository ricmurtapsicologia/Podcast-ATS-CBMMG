from __future__ import annotations

"""Ajustes de produção do N3 sem tocar na camada canônica.

Refina somente:
- segmentação semântica: evita blocos longos e excesso de microcortes;
- QA de silêncio: considera como gap excessivo apenas pausas realmente longas;
- concorrência de síntese na fase full, sem mudar texto/prosódia/pós-produção.

Nenhuma palavra do texto canônico é alterada.
"""

import asyncio
import json
import re
import shutil
import subprocess
from pathlib import Path

from pydub import AudioSegment, silence

import n3_pipeline as p

MIN_WORDS = 24
MAX_WORDS = 42
HARD_MAX_WORDS = 52
FULL_VOICE_CONCURRENCY = 8
FULL_EPISODE_CONCURRENCY = 4


def split_by_words(text: str, max_words: int = MAX_WORDS) -> list[str]:
    words = text.split()
    if len(words) <= HARD_MAX_WORDS:
        return [text.strip()]
    return [' '.join(words[start:start + max_words]) for start in range(0, len(words), max_words)]


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

    # A Série 3 N2 validada pelo usuário contém pausas naturais superiores a 1 s.
    # O gate N3 só contabiliza como gap longo silêncios contínuos >= 2,2 s.
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


async def synth_full_episode(direction: dict, out: Path, voice_sem: asyncio.Semaphore) -> None:
    work = p.TMP / 'edge-full-parallel' / direction['series'] / direction['episode']
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    tasks = []
    sequence = []
    for i, turn in enumerate(direction['turns']):
        part = work / f'{i:03d}.mp3'
        sequence.append((part, turn['pause_after_ms']))
        tasks.append(p.edge_segment(
            turn['text'], turn['speaker'], turn['rate_percent'], turn['pitch_hz'], part, voice_sem
        ))
    await asyncio.gather(*tasks)
    p.combine_segments(sequence, out)


async def parallel_run_full(manifest: dict, directions: dict[tuple[str, str], dict], cfg: dict) -> None:
    engine = cfg.get('selected_engine', 'N3-edge-semantic')
    if engine != 'N3-edge-semantic':
        raise RuntimeError('A promoção automática só é permitida para N3-edge-semantic até existir aprovação auditiva explícita de outro motor.')

    voice_sem = asyncio.Semaphore(FULL_VOICE_CONCURRENCY)
    episode_sem = asyncio.Semaphore(FULL_EPISODE_CONCURRENCY)

    async def process(item: dict) -> dict:
        series, episode = item['series'], item['episode']
        direction = directions[(series, episode)]
        out = p.final_audio_path(series, episode)
        async with episode_sem:
            await synth_full_episode(direction, out, voice_sem)
            rec = p.qa_record(series, episode, engine, out, direction)
        if rec['status'] != 'pass':
            raise RuntimeError(f'QA falhou em {series}/{episode}: {rec["issues"]}')
        return rec

    qa = await asyncio.gather(*(process(item) for item in manifest['episodes']))
    p.patch_audio_references()
    p.REPORTS.mkdir(parents=True, exist_ok=True)
    summary = {
        'phase': 'full',
        'engine': engine,
        'parallel_voice_concurrency': FULL_VOICE_CONCURRENCY,
        'parallel_episode_concurrency': FULL_EPISODE_CONCURRENCY,
        'episodes': len(qa),
        'series_counts': {s: len([r for r in qa if r['series'] == s]) for s in ('serie-1','serie-2','serie-3')},
        'all_pass': all(r['status'] == 'pass' for r in qa),
        'qa': qa,
    }
    (p.REPORTS / 'full-qa-report.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )


p.group_units = refined_group_units
p.probe_audio = refined_probe_audio
p.run_full = parallel_run_full
p.TARGET_MIN_WORDS = MIN_WORDS
p.TARGET_MAX_WORDS = MAX_WORDS
p.ABS_MAX_WORDS = HARD_MAX_WORDS


if __name__ == '__main__':
    asyncio.run(p.main())
