from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

import edge_tts
import requests
from pydub import AudioSegment, silence

ROOT = Path(__file__).resolve().parents[2]
CANON = ROOT / 'roteiros-canonicos'
DIRECTION = ROOT / 'audio-direction'
REPORTS = ROOT / 'reports' / 'audio-n3'
CANDIDATES = ROOT / 'assets' / 'audio' / 'candidate-n3'
TMP = ROOT / '.tmp_audio_n3'
CONFIG_PATH = Path(__file__).with_name('config.json')

VOICE_MALE = 'pt-BR-AntonioNeural'
VOICE_FEMALE = 'pt-BR-FranciscaNeural'
SERIES2_DIALOGUE = {7, 8, 9}
TARGET_WPM = 125
TARGET_MIN_WORDS = 22
TARGET_MAX_WORDS = 46
ABS_MAX_WORDS = 58
EDGE_TIMEOUT = 45
MAX_CONCURRENCY = 4

AB_SELECTIONS = {
    'serie-1': ['a1-001', 'a1-008', 'a1-010'],
    'serie-2': ['a2-002', 'a2-006', 'a2-008'],
    'serie-3': ['psp-05'],
}


def normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode('utf-8')).hexdigest()


def strip_generated_label(line: str) -> str:
    return re.sub(r'^(INSTRUTOR|PROFISSIONAL):\s*', '', line.strip(), flags=re.I)


def canonical_from_txt(path: Path) -> str:
    parts = []
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts.append(strip_generated_label(line))
    text = normalize_text(' '.join(parts))
    if not text:
        raise RuntimeError(f'Texto canônico vazio: {path}')
    return text


TURN_RE = re.compile(r'^\*\*(INSTRUTOR|PROFISSIONAL):\*\*\s*(.+)$')


def series3_turns(path: Path) -> list[dict]:
    turns = []
    for raw in path.read_text(encoding='utf-8').splitlines():
        m = TURN_RE.match(raw.strip())
        if m:
            turns.append({'speaker': m.group(1).upper(), 'text': normalize_text(m.group(2))})
    if not turns:
        raise RuntimeError(f'Nenhum turno encontrado: {path}')
    return turns


def canonical_from_series3(path: Path) -> str:
    return normalize_text(' '.join(t['text'] for t in series3_turns(path)))


def write_canonical(series: str, episode: str, text: str, source: str) -> dict:
    folder = CANON / series
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f'{episode}.txt'
    target.write_text(text + '\n', encoding='utf-8')
    return {
        'series': series,
        'episode': episode,
        'source': source,
        'path': str(target.relative_to(ROOT)),
        'sha256': sha256_text(text),
        'characters': len(text),
        'words': len(text.split()),
    }


def freeze_all() -> dict:
    manifest = {'schema': 1, 'generated_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'episodes': []}

    for path in sorted((ROOT / 'roteiros' / 'serie-1').glob('a1-*.txt')):
        episode = path.stem
        manifest['episodes'].append(write_canonical('serie-1', episode, canonical_from_txt(path), str(path.relative_to(ROOT))))

    for path in sorted((ROOT / 'roteiros' / 'serie-2').glob('a2-*.txt')):
        episode = path.stem
        manifest['episodes'].append(write_canonical('serie-2', episode, canonical_from_txt(path), str(path.relative_to(ROOT))))

    for path in sorted((ROOT / 'roteiros' / 'serie-3').glob('psp-*.md')):
        episode = path.stem
        manifest['episodes'].append(write_canonical('serie-3', episode, canonical_from_series3(path), str(path.relative_to(ROOT))))

    counts = {s: len([x for x in manifest['episodes'] if x['series'] == s]) for s in ('serie-1','serie-2','serie-3')}
    expected = {'serie-1': 21, 'serie-2': 14, 'serie-3': 10}
    if counts != expected:
        raise RuntimeError(f'Contagem canônica inesperada: {counts}; esperado {expected}')

    CANON.mkdir(parents=True, exist_ok=True)
    (CANON / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def split_sentences(text: str) -> list[str]:
    return [x.strip() for x in re.split(r'(?<=[.!?…])\s+', text) if x.strip()]


def split_long_sentence(sentence: str) -> list[str]:
    if len(sentence.split()) <= ABS_MAX_WORDS:
        return [sentence]
    clauses = [x.strip() for x in re.split(r'(?<=[;:])\s+|(?<=,)\s+', sentence) if x.strip()]
    if len(clauses) <= 1:
        return [sentence]
    return clauses


def group_units(text: str) -> list[str]:
    atoms: list[str] = []
    for sentence in split_sentences(text):
        atoms.extend(split_long_sentence(sentence))
    if not atoms:
        return [normalize_text(text)]

    out: list[str] = []
    current: list[str] = []
    words = 0
    for atom in atoms:
        n = len(atom.split())
        projected = words + n
        force_single = atom.rstrip().endswith('?')
        if force_single:
            if current:
                out.append(normalize_text(' '.join(current)))
                current, words = [], 0
            out.append(atom)
            continue
        if current and projected > TARGET_MAX_WORDS and words >= TARGET_MIN_WORDS:
            out.append(normalize_text(' '.join(current)))
            current, words = [], 0
        current.append(atom)
        words += n
        if words >= TARGET_MAX_WORDS:
            out.append(normalize_text(' '.join(current)))
            current, words = [], 0
    if current:
        if out and words < 10 and len(out[-1].split()) + words <= ABS_MAX_WORDS:
            out[-1] = normalize_text(out[-1] + ' ' + ' '.join(current))
        else:
            out.append(normalize_text(' '.join(current)))
    return out


def classify_intent(text: str, index: int, total: int) -> str:
    n = text.lower().strip()
    if text.rstrip().endswith('?'):
        return 'question'
    if index == 0:
        return 'opening'
    if index == total - 1 or n.startswith(('para concluir', 'em resumo', 'para fechar', 'por fim', 'finalmente')):
        return 'conclusion'
    if n.startswith(('guarde', 'pense', 'imagine', 'o ponto', 'lembre', 'em síntese', 'em sintese')):
        return 'synthesis'
    if n.startswith(('agora', 'depois', 'nesse contexto', 'por outro lado', 'além disso', 'alem disso', 'então', 'entao')):
        return 'transition'
    if re.search(r'\b(primeiro|segundo|terceiro|1\.|2\.|3\.)\b', n):
        return 'enumeration'
    if n.startswith(('atenção', 'atencao', 'importante', 'cuidado')):
        return 'alert'
    return 'explanation'


def semantic_prosody(speaker: str, text: str, intent: str) -> tuple[int, int]:
    base_rate = -3 if speaker == 'INSTRUTOR' else -1
    base_pitch = -1 if speaker == 'INSTRUTOR' else 1
    rate_delta = {
        'question': 1,
        'opening': 0,
        'conclusion': -2,
        'synthesis': -2,
        'transition': 0,
        'enumeration': -1,
        'alert': -1,
        'explanation': 0,
    }[intent]
    pitch_delta = {'question': 1, 'conclusion': -1, 'synthesis': -1}.get(intent, 0)
    wc = len(text.split())
    if wc < 10:
        rate_delta += 1
    elif wc > 45:
        rate_delta -= 1
    return max(-9, min(3, base_rate + rate_delta)), max(-3, min(3, base_pitch + pitch_delta))


def pause_after(intent: str, speaker: str, next_speaker: str | None) -> int:
    if next_speaker is None:
        return 0
    if next_speaker != speaker:
        return 680 if intent == 'question' else 620
    return {
        'question': 540,
        'conclusion': 520,
        'synthesis': 480,
        'transition': 390,
        'enumeration': 360,
        'alert': 430,
        'opening': 430,
        'explanation': 340,
    }.get(intent, 360)


def host_like(sentence: str) -> bool:
    n = sentence.lower().strip()
    return sentence.rstrip().endswith('?') or n.startswith((
        'programa ', 'estamos de volta', 'entrevistador', 'obrigad', 'doutor', 'dra.', 'dr. ',
        'no próximo episódio', 'no proximo episódio', 'no proximo episodio', 'até breve', 'ate breve'
    ))


def build_series2_dialogue(text: str) -> list[tuple[str, str]]:
    sentences = split_sentences(text)
    raw: list[tuple[str, str]] = []
    speaker = 'INSTRUTOR'
    buffer: list[str] = []

    def flush():
        nonlocal buffer
        if buffer:
            raw.append((speaker, normalize_text(' '.join(buffer))))
            buffer = []

    for sentence in sentences:
        if host_like(sentence):
            flush()
            raw.append(('INSTRUTOR', sentence))
            speaker = 'PROFISSIONAL' if sentence.rstrip().endswith('?') else 'INSTRUTOR'
        else:
            buffer.append(sentence)
            if len(' '.join(buffer).split()) >= TARGET_MAX_WORDS:
                flush()
    flush()

    refined: list[tuple[str, str]] = []
    for spk, block in raw:
        if block.rstrip().endswith('?'):
            refined.append((spk, block))
        else:
            refined.extend((spk, x) for x in group_units(block))
    return refined


def build_direction_for_episode(series: str, episode: str, canonical: str) -> dict:
    if series == 'serie-3':
        src = ROOT / 'roteiros' / 'serie-3' / f'{episode}.md'
        raw_turns = []
        for t in series3_turns(src):
            raw_turns.extend((t['speaker'], u) for u in group_units(t['text']))
    elif series == 'serie-2' and int(episode.split('-')[-1]) in SERIES2_DIALOGUE:
        raw_turns = build_series2_dialogue(canonical)
    else:
        raw_turns = [('INSTRUTOR', u) for u in group_units(canonical)]

    rebuilt = normalize_text(' '.join(text for _, text in raw_turns))
    if rebuilt != normalize_text(canonical):
        raise RuntimeError(f'Gate textual falhou em {series}/{episode}')

    turns = []
    for i, (speaker, text) in enumerate(raw_turns):
        intent = classify_intent(text, i, len(raw_turns))
        rate, pitch = semantic_prosody(speaker, text, intent)
        next_speaker = raw_turns[i + 1][0] if i + 1 < len(raw_turns) else None
        turns.append({
            'speaker': speaker,
            'text': text,
            'intent': intent,
            'rate_percent': rate,
            'pitch_hz': pitch,
            'pause_after_ms': pause_after(intent, speaker, next_speaker),
            'estimated_seconds': round(len(text.split()) / TARGET_WPM * 60, 1),
        })

    return {
        'schema': 1,
        'series': series,
        'episode': episode,
        'canonical_sha256': sha256_text(canonical),
        'target_wpm_reference': TARGET_WPM,
        'turns': turns,
    }


def build_all_directions(manifest: dict) -> dict[tuple[str, str], dict]:
    result = {}
    for item in manifest['episodes']:
        text = (ROOT / item['path']).read_text(encoding='utf-8').strip()
        direction = build_direction_for_episode(item['series'], item['episode'], text)
        folder = DIRECTION / item['series']
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{item['episode']}.json").write_text(json.dumps(direction, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        result[(item['series'], item['episode'])] = direction
    return result


def voice_name(speaker: str) -> str:
    return VOICE_MALE if speaker == 'INSTRUTOR' else VOICE_FEMALE


async def edge_segment(text: str, speaker: str, rate: int, pitch: int, out: Path, sem: asyncio.Semaphore):
    async with sem:
        for attempt in range(3):
            try:
                comm = edge_tts.Communicate(text=text, voice=voice_name(speaker), rate=f'{rate:+d}%', pitch=f'{pitch:+d}Hz', volume='+0%')
                await asyncio.wait_for(comm.save(str(out)), timeout=EDGE_TIMEOUT)
                return
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(0.8 * (attempt + 1))


def azure_request(ssml: str, out: Path, key: str, region: str) -> None:
    url = f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1'
    headers = {
        'Ocp-Apim-Subscription-Key': key,
        'Content-Type': 'application/ssml+xml',
        'X-Microsoft-OutputFormat': 'audio-24khz-96kbitrate-mono-mp3',
        'User-Agent': 'PodcastATS-AudioN3',
    }
    response = requests.post(url, headers=headers, data=ssml.encode('utf-8'), timeout=60)
    response.raise_for_status()
    out.write_bytes(response.content)


def azure_standard_ssml(text: str, speaker: str, rate: int, pitch: int) -> str:
    voice = voice_name(speaker)
    safe = html.escape(text)
    return (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='pt-BR'>"
        f"<voice name='{voice}'><prosody rate='{rate:+d}%' pitch='{pitch:+d}Hz'>{safe}</prosody></voice></speak>"
    )


def azure_hd_ssml(text: str, speaker: str, hd_voice_male: str, hd_voice_female: str) -> str:
    voice = hd_voice_male if speaker == 'INSTRUTOR' else hd_voice_female
    safe = html.escape(text)
    return (
        "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='pt-BR'>"
        f"<voice name='{html.escape(voice)}'><lang xml:lang='pt-BR'><s>{safe}</s></lang></voice></speak>"
    )


def combine_segments(parts: Iterable[tuple[Path, int]], out: Path) -> None:
    merged = AudioSegment.silent(duration=120)
    for path, pause_ms in parts:
        merged += AudioSegment.from_file(path)
        if pause_ms:
            merged += AudioSegment.silent(duration=pause_ms)
    merged += AudioSegment.silent(duration=220)
    tmp_wav = out.with_suffix('.pre.wav')
    merged.export(tmp_wav, format='wav')
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', str(tmp_wav),
        '-af', 'loudnorm=I=-16:LRA=7:TP=-1.5', '-ac', '1', '-ar', '44100', '-b:a', '128k', str(out)
    ]
    subprocess.run(cmd, check=True)
    tmp_wav.unlink(missing_ok=True)


async def synth_episode_edge(direction: dict, out: Path) -> None:
    work = TMP / 'edge' / direction['series'] / direction['episode']
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    tasks = []
    seq = []
    for i, turn in enumerate(direction['turns']):
        part = work / f'{i:03d}.mp3'
        seq.append((part, turn['pause_after_ms']))
        tasks.append(edge_segment(turn['text'], turn['speaker'], turn['rate_percent'], turn['pitch_hz'], part, sem))
    await asyncio.gather(*tasks)
    combine_segments(seq, out)


def synth_episode_azure(direction: dict, out: Path, engine: str, key: str, region: str, hd_male: str, hd_female: str) -> None:
    work = TMP / engine / direction['series'] / direction['episode']
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    seq = []
    for i, turn in enumerate(direction['turns']):
        part = work / f'{i:03d}.mp3'
        if engine == 'azure-neural-ssml':
            ssml = azure_standard_ssml(turn['text'], turn['speaker'], turn['rate_percent'], turn['pitch_hz'])
        else:
            ssml = azure_hd_ssml(turn['text'], turn['speaker'], hd_male, hd_female)
        azure_request(ssml, part, key, region)
        seq.append((part, turn['pause_after_ms']))
    combine_segments(seq, out)


def current_audio_path(series: str, episode: str) -> Path:
    if series == 'serie-1':
        return ROOT / 'assets' / 'audio' / series / f'{episode}-s3n2.mp3'
    if series == 'serie-2':
        return ROOT / 'assets' / 'audio' / series / f'{episode}-s3v3.mp3'
    return ROOT / 'assets' / 'audio' / series / f'{episode}.mp3'


def parse_ebur128(path: Path) -> tuple[float | None, float | None]:
    proc = subprocess.run(
        ['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-filter_complex', 'ebur128=peak=true', '-f', 'null', '-'],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    text = proc.stdout
    i_matches = re.findall(r'\bI:\s*(-?\d+(?:\.\d+)?)\s+LUFS', text)
    p_matches = re.findall(r'\bPeak:\s*(-?\d+(?:\.\d+)?)\s+dBFS', text)
    return (float(i_matches[-1]) if i_matches else None, float(p_matches[-1]) if p_matches else None)


def probe_audio(path: Path) -> dict:
    probe = subprocess.run([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration,bit_rate:stream=sample_rate,channels',
        '-of', 'json', str(path)
    ], capture_output=True, text=True, check=True)
    data = json.loads(probe.stdout)
    stream = data.get('streams', [{}])[0]
    fmt = data.get('format', {})
    audio = AudioSegment.from_file(path)
    silent = silence.detect_silence(audio, min_silence_len=1000, silence_thresh=-50)
    silent_ms = sum(end - start for start, end in silent)
    lufs, peak = parse_ebur128(path)
    return {
        'duration_seconds': round(float(fmt.get('duration', 0.0)), 2),
        'sample_rate': int(stream.get('sample_rate', 0) or 0),
        'channels': int(stream.get('channels', 0) or 0),
        'bitrate': int(fmt.get('bit_rate', 0) or 0),
        'lufs_integrated': lufs,
        'true_peak_dbfs': peak,
        'long_silence_ratio': round(silent_ms / max(1, len(audio)), 4),
    }


def qa_record(series: str, episode: str, engine: str, path: Path, direction: dict) -> dict:
    metrics = probe_audio(path)
    turn_durations = [t['estimated_seconds'] for t in direction['turns']]
    issues = []
    if not path.exists() or metrics['duration_seconds'] <= 0:
        issues.append('arquivo_ausente_ou_vazio')
    if metrics['sample_rate'] != 44100:
        issues.append('sample_rate')
    if metrics['channels'] != 1:
        issues.append('canais')
    if metrics['lufs_integrated'] is not None and not (-17.2 <= metrics['lufs_integrated'] <= -14.8):
        issues.append('loudness')
    if metrics['true_peak_dbfs'] is not None and metrics['true_peak_dbfs'] > -0.8:
        issues.append('true_peak')
    if metrics['long_silence_ratio'] > 0.12:
        issues.append('silencio_excessivo')
    canonical_path = CANON / series / f'{episode}.txt'
    canonical_hash = sha256_text(canonical_path.read_text(encoding='utf-8'))
    if canonical_hash != direction['canonical_sha256']:
        issues.append('hash_textual')
    return {
        'series': series,
        'episode': episode,
        'file': str(path.relative_to(ROOT)),
        'engine': engine,
        'version': 'N3',
        'voices': sorted(set(voice_name(t['speaker']) for t in direction['turns'])),
        'segments': len(direction['turns']),
        'mean_estimated_segment_seconds': round(sum(turn_durations) / max(1, len(turn_durations)), 2),
        'canonical_sha256': canonical_hash,
        'generated_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        **metrics,
        'status': 'pass' if not issues else 'fail',
        'issues': issues,
    }


def copy_current_for_ab(series: str, episode: str) -> Path:
    src = current_audio_path(series, episode)
    if not src.exists():
        raise RuntimeError(f'Áudio atual não encontrado: {src}')
    out = CANDIDATES / 'A-current' / series / f'{episode}.mp3'
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, out)
    return out


def final_audio_path(series: str, episode: str) -> Path:
    return ROOT / 'assets' / 'audio' / series / f'{episode}-n3.mp3'


def patch_audio_references() -> None:
    app = ROOT / 'app.js'
    content = app.read_text(encoding='utf-8')
    content = re.sub(r'assets/audio/serie-1/(a1-\d{3})(?:-s3n2|-n3)?\.mp3', r'assets/audio/serie-1/\1-n3.mp3', content)
    content = re.sub(r'assets/audio/serie-2/(a2-\d{3})(?:-s3v3|-n3)?\.mp3', r'assets/audio/serie-2/\1-n3.mp3', content)
    app.write_text(content, encoding='utf-8')

    psp = ROOT / 'psp.js'
    pcontent = psp.read_text(encoding='utf-8')
    old = '`assets/audio/serie-3/psp-${pad(index + 1)}.mp3`'
    new = '`assets/audio/serie-3/psp-${pad(index + 1)}-n3.mp3`'
    if old not in pcontent and new not in pcontent:
        raise RuntimeError('Referência de áudio da Série 3 não localizada em psp.js')
    psp.write_text(pcontent.replace(old, new), encoding='utf-8')


def assert_allowed_changes() -> None:
    allowed_prefixes = (
        'assets/audio/', 'roteiros-canonicos/', 'audio-direction/', 'scripts/audio_n3/', 'reports/audio-n3/', '.github/workflows/audio-n3.yml'
    )
    allowed_exact = {'app.js', 'psp.js'}
    proc = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True, check=True)
    bad = []
    for line in proc.stdout.splitlines():
        path = line[3:].strip().strip('"')
        if path in allowed_exact or any(path.startswith(p) for p in allowed_prefixes):
            continue
        bad.append(path)
    if bad:
        raise RuntimeError(f'Alterações fora do escopo congelado: {bad}')


async def run_ab(manifest: dict, directions: dict[tuple[str, str], dict], cfg: dict) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    availability = {
        'A-current': True,
        'N3-edge-semantic': True,
        'B-azure-neural-ssml': bool(os.getenv('AZURE_SPEECH_KEY')),
        'C-azure-hd-contextual': bool(os.getenv('AZURE_SPEECH_KEY')),
    }
    azure_errors = []
    qa = []
    key = os.getenv('AZURE_SPEECH_KEY', '')
    region = os.getenv('AZURE_SPEECH_REGION', 'brazilsouth')
    hd_male = os.getenv('AZURE_HD_VOICE_MALE', 'en-US-Andrew:DragonHDOmniLatestNeural')
    hd_female = os.getenv('AZURE_HD_VOICE_FEMALE', 'en-US-Ava:DragonHDOmniLatestNeural')

    for series, episodes in AB_SELECTIONS.items():
        for episode in episodes:
            direction = directions[(series, episode)]
            current = copy_current_for_ab(series, episode)
            qa.append(qa_record(series, episode, 'A-current', current, direction))

            edge_out = CANDIDATES / 'N3-edge-semantic' / series / f'{episode}.mp3'
            await synth_episode_edge(direction, edge_out)
            qa.append(qa_record(series, episode, 'N3-edge-semantic', edge_out, direction))

            if key:
                for engine, folder in [('azure-neural-ssml','B-azure-neural-ssml'), ('azure-hd-contextual','C-azure-hd-contextual')]:
                    out = CANDIDATES / folder / series / f'{episode}.mp3'
                    try:
                        synth_episode_azure(direction, out, engine, key, region, hd_male, hd_female)
                        qa.append(qa_record(series, episode, folder, out, direction))
                    except Exception as exc:
                        availability[folder] = False
                        azure_errors.append({'engine': folder, 'series': series, 'episode': episode, 'error': str(exc)[:400]})
                        break

    report = {
        'phase': 'ab',
        'reference': 'Série 3 N2 previamente validada pelo usuário',
        'availability': availability,
        'azure_errors': azure_errors,
        'selection': {
            'provisional_engine': 'N3-edge-semantic',
            'reason': 'mantém a identidade vocal já validada na Série 3 e aplica segmentação/prosódia semânticas; Azure só pode ser promovido após teste auditivo quando credenciais estiverem disponíveis',
        },
        'qa': qa,
    }
    (REPORTS / 'ab-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load_config() -> dict:
    cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    if cfg.get('phase') not in {'ab', 'full'}:
        raise RuntimeError('config.phase deve ser ab ou full')
    return cfg


async def run_full(manifest: dict, directions: dict[tuple[str, str], dict], cfg: dict) -> None:
    engine = cfg.get('selected_engine', 'N3-edge-semantic')
    if engine != 'N3-edge-semantic':
        raise RuntimeError('A promoção automática só é permitida para N3-edge-semantic até existir aprovação auditiva explícita de outro motor.')
    qa = []
    for item in manifest['episodes']:
        series, episode = item['series'], item['episode']
        direction = directions[(series, episode)]
        out = final_audio_path(series, episode)
        await synth_episode_edge(direction, out)
        rec = qa_record(series, episode, engine, out, direction)
        qa.append(rec)
        if rec['status'] != 'pass':
            raise RuntimeError(f'QA falhou em {series}/{episode}: {rec["issues"]}')

    patch_audio_references()
    REPORTS.mkdir(parents=True, exist_ok=True)
    summary = {
        'phase': 'full',
        'engine': engine,
        'episodes': len(qa),
        'series_counts': {s: len([r for r in qa if r['series'] == s]) for s in ('serie-1','serie-2','serie-3')},
        'all_pass': all(r['status'] == 'pass' for r in qa),
        'qa': qa,
    }
    (REPORTS / 'full-qa-report.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['ab','full'])
    args = parser.parse_args()
    cfg = load_config()
    if args.phase:
        cfg['phase'] = args.phase

    manifest = freeze_all()
    directions = build_all_directions(manifest)
    (DIRECTION / 'pronunciation.json').parent.mkdir(parents=True, exist_ok=True)
    if not (DIRECTION / 'pronunciation.json').exists():
        (DIRECTION / 'pronunciation.json').write_text(json.dumps({
            'schema': 1,
            'policy': 'Camada separada; não altera o texto canônico. Usar somente em motores que suportem alias/lexicon.',
            'entries': [
                {'token': 'CBMMG', 'alias': 'C B M M G'},
                {'token': 'ATS', 'alias': 'A T S'},
                {'token': 'PSP', 'alias': 'P S P'},
            ],
        }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if cfg['phase'] == 'ab':
        await run_ab(manifest, directions, cfg)
    else:
        await run_full(manifest, directions, cfg)
    assert_allowed_changes()


if __name__ == '__main__':
    asyncio.run(main())
