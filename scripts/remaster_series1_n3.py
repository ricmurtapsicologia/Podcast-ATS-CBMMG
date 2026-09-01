from __future__ import annotations

import asyncio
import json
import re
import shutil
from pathlib import Path

import edge_tts
from pydub import AudioSegment, effects

import remaster_series1_organic as legacy
from n3_audio_core import breath_units, lexical_tokens, prosody, speakable

ROOT = Path(__file__).resolve().parents[1]
ROTEIROS = ROOT / 'roteiros' / 'serie-1'
OUT = ROOT / 'assets' / 'audio' / 'serie-1'
TMP = ROOT / '.tmp_serie1_n3'
APP = ROOT / 'app.js'
VERSION = 'n3-20260831b'
VERSION_TAG = 'n3'

VOICE_NARRATOR = 'pt-BR-AntonioNeural'
VOICE_PROFISSIONAL = 'pt-BR-FranciscaNeural'
VOICE_ABORDADOR_M = 'pt-BR-AntonioNeural'
VOICE_TENTANTE_M = 'pt-BR-FabioNeural'
VOICE_ABORDADOR_F = 'pt-BR-FranciscaNeural'
VOICE_TENTANTE_F = 'pt-BR-BrendaNeural'

OPENING_SILENCE_MS = 180
ENDING_SILENCE_MS = 340
TARGET_DBFS = -18.0
DIALOGUE_EPISODES = {8, 9, 10, 11, 13, 14, 15}

SPEAKER_PREFIXES = (
    ('ABORDADOR_M:', VOICE_ABORDADOR_M, 'professional'),
    ('ABORDADOR_F:', VOICE_ABORDADOR_F, 'professional'),
    ('TENTANTE_M:', VOICE_TENTANTE_M, 'person_in_crisis'),
    ('TENTANTE_F:', VOICE_TENTANTE_F, 'person_in_crisis'),
    ('PROFISSIONAL:', VOICE_PROFISSIONAL, 'professional'),
    ('INSTRUTOR:', VOICE_NARRATOR, 'narrator'),
)

GREETING_RE = re.compile(r'\bol[áa]\s*,?\s+pessoal\b[.!?…]*', flags=re.I)


def approved_editorial_transform(text: str) -> str:
    return GREETING_RE.sub('Olá, caros abordadores.', text)


def isolate_greeting(text: str) -> str:
    return re.sub(
        r'(?<!^)(?<![.!?…])\s+(Olá, caros abordadores\.)',
        r'. \1',
        text,
        flags=re.I,
    )


def read_turns(number: int):
    path = ROTEIROS / f'a1-{number:03d}.txt'
    source_tokens = []
    spoken_tokens = []
    turns = []
    speaker_roles = []

    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue

        voice = VOICE_NARRATOR
        role = 'narrator'
        text = line
        for prefix, mapped_voice, mapped_role in SPEAKER_PREFIXES:
            if line.startswith(prefix):
                voice = mapped_voice
                role = mapped_role
                text = line.split(':', 1)[1].strip()
                break

        if not text:
            continue

        text = approved_editorial_transform(text)
        source_tokens.extend(lexical_tokens(text))

        spoken = legacy.add_prosodic_punctuation(text)
        spoken = isolate_greeting(spoken)

        for unit in breath_units(spoken):
            turns.append((voice, role, unit))
            spoken_tokens.extend(lexical_tokens(unit))
            speaker_roles.append(role)

    if not turns or source_tokens != spoken_tokens:
        raise RuntimeError(f'Gate lexical N3 falhou em A1-{number:03d}')

    return turns, len(source_tokens), speaker_roles


async def synth(text, voice, rate, pitch, path, sem):
    async with sem:
        for attempt in range(1, 4):
            try:
                c = edge_tts.Communicate(
                    text=speakable(text),
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                    volume='+0%',
                )
                await asyncio.wait_for(c.save(str(path)), timeout=55)
                return
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(.9 * attempt)


async def build_episode(number: int, sem: asyncio.Semaphore):
    turns, word_count, speaker_roles = read_turns(number)
    work = TMP / f'a1-{number:03d}'
    work.mkdir(parents=True, exist_ok=True)

    tasks = []
    seq = []
    intents = []
    voices = []

    for i, (voice, role, text) in enumerate(turns):
        profile = 'dialogue' if role in {'professional', 'person_in_crisis'} else 'clinical'
        p = prosody(text, profile=profile, role=role)
        rate, pitch, pause = p.rate, p.pitch, p.pause_ms

        if lexical_tokens(text) == ['olá', 'caros', 'abordadores']:
            rate = '-2%'
            pitch = '+0Hz'
            pause = 460

        part = work / f'{i:03d}.mp3'
        seq.append((part, 0 if i == len(turns) - 1 else pause))
        tasks.append(synth(text, voice, rate, pitch, part, sem))
        intents.append(p.intent)
        voices.append(voice)

    await asyncio.gather(*tasks)

    audio = AudioSegment.silent(duration=OPENING_SILENCE_MS)
    for part, pause in seq:
        audio += AudioSegment.from_file(part, format='mp3')
        if pause:
            audio += AudioSegment.silent(duration=pause)

    audio += AudioSegment.silent(duration=ENDING_SILENCE_MS)
    audio = effects.compress_dynamic_range(
        audio, threshold=-20.0, ratio=2.0, attack=8.0, release=70.0
    )
    if audio.dBFS != float('-inf'):
        audio = audio.apply_gain(TARGET_DBFS - audio.dBFS)
    if audio.max_dBFS > -1.2:
        audio = audio.apply_gain(-1.2 - audio.max_dBFS)

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f'a1-{number:03d}-{VERSION_TAG}.mp3'
    audio.export(
        target,
        format='mp3',
        bitrate='128k',
        parameters=['-ac', '1', '-ar', '44100'],
    )

    distinct_voices = sorted(set(voices))
    is_dialogue = number in DIALOGUE_EPISODES
    if is_dialogue and len(distinct_voices) < 2:
        raise RuntimeError(
            f'Gate multivoz falhou em A1-{number:03d}: {len(distinct_voices)} voz(es)'
        )

    return {
        'episode': number,
        'output': target.name,
        'version': VERSION,
        'profile': 'N3-C-dialogue' if is_dialogue else 'N3-C',
        'lexical_integrity': 1.0,
        'approved_greeting_substitution': True,
        'greeting': 'Olá, caros abordadores.',
        'pronunciation_dictionary': True,
        'source_words': word_count,
        'turns': len(turns),
        'voices': distinct_voices,
        'speaker_roles': sorted(set(speaker_roles)),
        'dialogue_multivoice': is_dialogue,
        'intents': sorted(set(intents)),
        'duration_seconds': round(len(audio) / 1000, 1),
    }


def patch_app_urls():
    content = APP.read_text(encoding='utf-8')
    block_match = re.search(r'const AUDIOS=\{1:\[(.*?)\],2:\[', content, re.S)
    if not block_match:
        raise RuntimeError('Bloco da Série 1 não localizado')

    block = block_match.group(1)
    entries = list(re.finditer(r'\{title:"([^"]+)",url:"([^"]+)"\}', block))
    if len(entries) != 21:
        raise RuntimeError(f'Esperados 21 episódios; encontrados {len(entries)}')

    new_block = block
    for idx, match in reversed(list(enumerate(entries, start=1))):
        title = match.group(1)
        replacement = (
            f'{{title:"{title}",url:"assets/audio/serie-1/a1-{idx:03d}-{VERSION_TAG}.mp3"}}'
        )
        new_block = new_block[:match.start()] + replacement + new_block[match.end():]

    content = content[:block_match.start(1)] + new_block + content[block_match.end(1):]
    APP.write_text(content, encoding='utf-8')


async def main():
    TMP.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(6)
    quality = []

    for number in range(1, 22):
        print(f'[A1-{number:03d}] N3 Natural')
        quality.append(await build_episode(number, sem))

    patch_app_urls()

    report = {
        'version': VERSION,
        'approved_greeting_substitution': {
            'from': 'Olá, pessoal.',
            'to': 'Olá, caros abordadores.',
        },
        'dialogue_episodes': sorted(DIALOGUE_EPISODES),
        'pronunciation_dictionary': True,
        'episodes': quality,
    }
    (OUT / 'quality-n3.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    shutil.rmtree(TMP, ignore_errors=True)
    print('Série 1 N3 concluída.')


if __name__ == '__main__':
    asyncio.run(main())
