from __future__ import annotations

import asyncio
import json
import re
import shutil
from pathlib import Path

import edge_tts
from pydub import AudioSegment, effects

from n3_audio_core import breath_units, normalize, prosody
from n3_foley import apply_sound_design

ROOT = Path(__file__).resolve().parents[1]
ROTEIROS = ROOT / 'roteiros' / 'serie-2'
OUT = ROOT / 'assets' / 'audio' / 'serie-2'
TMP = ROOT / '.tmp_serie2_n3'
APP = ROOT / 'app.js'
SOUND_DESIGN = ROOT / 'sound-design' / 'series-2.json'
VERSION_TAG = 'n3'
VERSION = 'n3-20260831'
OPENING_SILENCE_MS = 160
ENDING_SILENCE_MS = 320
TARGET_DBFS = -18.0
MAX_CONCURRENT_SYNTH = 5
SYNTH_TIMEOUT_SECONDS = 55
CINEMATIC_EPISODES = {4, 5, 6, 7, 8, 9}

PREFERRED_CAST = {
    'narrator': ['pt-BR-AntonioNeural'],
    'gorette': ['pt-BR-ElzaNeural', 'pt-BR-FranciscaNeural'],
    'maria': ['pt-BR-ThalitaNeural', 'pt-BR-GiovannaNeural', 'pt-BR-FranciscaNeural'],
    'claudio': ['pt-BR-FabioNeural', 'pt-BR-DonatoNeural', 'pt-BR-AntonioNeural'],
    'ana': ['pt-BR-BrendaNeural', 'pt-BR-FranciscaNeural'],
    'guilherme': ['pt-BR-HumbertoNeural', 'pt-BR-AntonioNeural'],
    'fernanda': ['pt-BR-LeilaNeural', 'pt-BR-FranciscaNeural'],
    'host': ['pt-BR-AntonioNeural'],
    'julia': ['pt-BR-GiovannaNeural', 'pt-BR-FranciscaNeural'],
    'dra_sara': ['pt-BR-ManuelaNeural', 'pt-BR-FranciscaNeural'],
    'lourdes': ['pt-BR-ElzaNeural', 'pt-BR-FranciscaNeural'],
    'fatima': ['pt-BR-YaraNeural', 'pt-BR-FranciscaNeural'],
}

ROLE_STYLE = {
    'narrator': 'narrator', 'gorette': 'family', 'maria': 'person_in_crisis',
    'claudio': 'person_in_crisis', 'ana': 'family', 'guilherme': 'professional',
    'fernanda': 'person_in_crisis', 'host': 'host', 'julia': 'guest',
    'dra_sara': 'professional', 'lourdes': 'family', 'fatima': 'family',
}


def read_text(number: int) -> str:
    path = ROTEIROS / f'a2-{number:03d}.txt'
    lines = [line for line in path.read_text(encoding='utf-8').splitlines() if not line.startswith('#')]
    text = normalize(' '.join(lines))
    if not text:
        raise RuntimeError(f'Roteiro vazio: {path}')
    return text


def sentence_list(text: str) -> list[str]:
    return [s.strip() for s in re.split(r'(?<=[.!?…])\s+', text) if s.strip()]


def is_stage_direction(number: int, sentence: str) -> bool:
    low = sentence.lower().strip()
    return number == 9 and low.startswith('sons de chícaras sendo colocadas na mesa')


def speaker_for(number: int, sentence: str) -> str:
    low = sentence.lower().strip()
    if number == 4:
        if low.startswith('gorette ') or low.startswith('minha filha'):
            return 'gorette'
        if low.startswith('maria ') or low.startswith(('não, mãe', 'é difícil', 'é isso que', 'não, tem noites', 'não sinto', 'já pensei', 'obrigada, mãe')):
            return 'maria'
        return 'narrator'
    if number == 5:
        if low.startswith('cláudio ') or low.startswith(('vocês precisam', 'você é a pessoa', 'ana, você', 'mas sabe')):
            return 'claudio'
        if low.startswith('ana '):
            return 'ana'
        return 'narrator'
    if number == 6:
        if low.startswith(('oi, eu sou guilherme', 'importa, sim', 'o que você', 'posso te ajudar', 'entendo que',
                           'parece que', 'desde quando', 'isso deve ser', 'fernanda, antes', 'e antes de começar',
                           'sua mãe ainda', 'eu entendo que', 'vamos sair daqui')):
            return 'guilherme'
        if low.startswith(('fernanda.', 'mas isso', 'nada mais', 'eu não sei', 'minha vida', 'minha mãe', 'eu só',
                           'sim, mas', 'desde que', 'sim, usei', 'trabalhava num salão', 'eu gostava', 'ela diz',
                           'eu não consigo', 'eu queria')):
            return 'fernanda'
        return 'narrator'
    if number == 7:
        if low.startswith(('programa em foco', 'entrevistador', 'boa noite', 'vamos começar', 'e foi nesse', 'e como esse',
                           'como o transtorno', 'hoje você', 'julia, sua história', 'no próximo bloco')) or sentence.endswith('?'):
            return 'host'
        return 'julia'
    if number == 8:
        if low.startswith(('programa infoco', 'estamos de volta', 'no bloco anterior', 'agora, para', 'dr. sara', 'o que são',
                           'como eles', 'e qual a relação', 'pode explicar', 'e como é', 'entrevistador')) or sentence.endswith('?'):
            return 'host'
        return 'dra_sara'
    if number == 9:
        if low.startswith(('bem-vindos', 'hoje trazemos', 'ao longo', 'vamos ouvir', 'essa foi a conversa', 'a esquizofrenia',
                           'buscar ajuda', 'no próximo episódio')):
            return 'narrator'
        if low.startswith(('lourdes, você', 'ela ainda ouve', 'e você está cuidando', 'e ela ainda tem sonhos')):
            return 'fatima'
        if low.startswith(('ah, fatima', 'sim, às vezes', 'sim, as vezes', 'fatima, ela já', 'fatima, como você reage',
                           'estou tentando, fatima', 'sim, quer')):
            return 'lourdes'
        if low.startswith(('já. durante', 'eu respiro fundo')):
            return 'fatima'
        return 'lourdes'
    return 'narrator'


async def resolve_cast() -> tuple[dict[str, str], list[str]]:
    try:
        voices = await edge_tts.list_voices()
        available = {str(v.get('ShortName')) for v in voices}
    except Exception:
        available = {'pt-BR-AntonioNeural', 'pt-BR-FranciscaNeural'}
    cast: dict[str, str] = {}
    fallbacks: list[str] = []
    for role, preferences in PREFERRED_CAST.items():
        chosen = next((v for v in preferences if v in available), None)
        if not chosen:
            chosen = 'pt-BR-FranciscaNeural' if role in {'gorette','maria','ana','fernanda','julia','dra_sara','lourdes','fatima'} else 'pt-BR-AntonioNeural'
            fallbacks.append(role)
        cast[role] = chosen
    return cast, fallbacks


def build_turns(number: int, text: str) -> tuple[list[tuple[str, str]], list[str]]:
    turns: list[tuple[str, str]] = []
    stage_directions: list[str] = []
    spoken_source: list[str] = []
    for sentence in sentence_list(text):
        if is_stage_direction(number, sentence):
            stage_directions.append(sentence)
            continue
        spoken_source.append(sentence)
        role = speaker_for(number, sentence)
        for unit in breath_units(sentence):
            turns.append((role, unit))
    if not turns:
        raise RuntimeError(f'Nenhum turno gerado para A2-{number:03d}')
    source_tokens = re.findall(r'[\wÀ-ÿ]+', ' '.join(spoken_source).lower())
    rebuilt_tokens = re.findall(r'[\wÀ-ÿ]+', ' '.join(text for _, text in turns).lower())
    if source_tokens != rebuilt_tokens:
        raise RuntimeError(f'Gate lexical N3 falhou em A2-{number:03d}')
    return turns, stage_directions


async def synth(text: str, voice: str, rate: str, pitch: str, path: Path, sem: asyncio.Semaphore):
    async with sem:
        for attempt in range(1, 4):
            try:
                c = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch, volume='+0%')
                await asyncio.wait_for(c.save(str(path)), timeout=SYNTH_TIMEOUT_SECONDS)
                return
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(0.9 * attempt)


def sound_design_for(number: int, data: dict) -> tuple[str, list[dict]]:
    entry = data.get('episodes', {}).get(f'{number:03d}', {})
    return str(entry.get('scene', 'none')), list(entry.get('events', []))


async def build_episode(number: int, cast: dict[str, str], sound_design: dict, sem: asyncio.Semaphore) -> dict:
    text = read_text(number)
    turns, stage_directions = build_turns(number, text)
    work = TMP / f'a2-{number:03d}'
    work.mkdir(parents=True, exist_ok=True)
    sequence = []
    tasks = []
    intents = []
    roles = []
    voices = []
    profile = 'dialogue' if number in CINEMATIC_EPISODES else 'narrative'
    for idx, (role, turn) in enumerate(turns):
        p = prosody(turn, profile=profile, role=ROLE_STYLE.get(role, 'narrator'))
        part = work / f'{idx:03d}.mp3'
        pause = 0 if idx == len(turns) - 1 else p.pause_ms
        voice = cast[role]
        sequence.append((part, pause))
        tasks.append(synth(turn, voice, p.rate, p.pitch, part, sem))
        intents.append(p.intent); roles.append(role); voices.append(voice)
    await asyncio.gather(*tasks)

    merged = AudioSegment.silent(duration=OPENING_SILENCE_MS)
    for part, pause in sequence:
        merged += AudioSegment.from_file(part, format='mp3')
        if pause:
            merged += AudioSegment.silent(duration=pause)
    merged += AudioSegment.silent(duration=ENDING_SILENCE_MS)
    merged = effects.compress_dynamic_range(merged, threshold=-20.0, ratio=2.0, attack=8.0, release=70.0)
    if merged.dBFS != float('-inf'):
        merged = merged.apply_gain(TARGET_DBFS - merged.dBFS)

    scene, events = sound_design_for(number, sound_design)
    cinematic = number in CINEMATIC_EPISODES
    if cinematic:
        merged = apply_sound_design(merged, scene, events)
        if merged.max_dBFS > -1.2:
            merged = merged.apply_gain(-1.2 - merged.max_dBFS)
    else:
        merged = merged.set_channels(1)
        if merged.max_dBFS > -1.2:
            merged = merged.apply_gain(-1.2 - merged.max_dBFS)

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f'a2-{number:03d}-{VERSION_TAG}.mp3'
    bitrate = '192k' if cinematic else '128k'
    channels = 2 if cinematic else 1
    merged.export(target, format='mp3', bitrate=bitrate, parameters=['-ac', str(channels), '-ar', '44100'])
    return {
        'episode': number,
        'output': target.name,
        'version': VERSION,
        'profile': 'N3-D' if cinematic else 'N3-C',
        'scene': scene,
        'events': events,
        'stage_directions_replaced_by_sound': stage_directions,
        'text_integrity_spoken_content': 1.0,
        'roles': sorted(set(roles)),
        'voices': sorted(set(voices)),
        'intents': sorted(set(intents)),
        'turns': len(turns),
        'duration_seconds': round(len(merged) / 1000, 1),
        'channels': channels,
        'sample_rate': 44100,
        'bitrate': bitrate,
    }


def patch_app_urls():
    content = APP.read_text(encoding='utf-8')
    block_match = re.search(r',2:\[(.*?)\],3:\[\]', content, re.S)
    if not block_match:
        raise RuntimeError('Bloco da Série 2 não localizado em app.js')
    block = block_match.group(1)
    entries = list(re.finditer(r'\{title:"([^"]+)",url:"([^"]+)"\}', block))
    if len(entries) != 14:
        raise RuntimeError(f'Esperados 14 episódios; encontrados {len(entries)}')
    new_block = block
    for idx, match in reversed(list(enumerate(entries))):
        title = match.group(1)
        replacement = f'{{title:"{title}",url:"assets/audio/serie-2/a2-{idx:03d}-{VERSION_TAG}.mp3"}}'
        new_block = new_block[:match.start()] + replacement + new_block[match.end():]
    content = content[:block_match.start(1)] + new_block + content[block_match.end(1):]
    APP.write_text(content, encoding='utf-8')


async def main():
    sound_design = json.loads(SOUND_DESIGN.read_text(encoding='utf-8'))
    cast, fallbacks = await resolve_cast()
    TMP.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(MAX_CONCURRENT_SYNTH)
    quality = []
    for number in range(14):
        print(f'[A2-{number:03d}] N3 Natural')
        quality.append(await build_episode(number, cast, sound_design, sem))
    patch_app_urls()
    report = {
        'version': VERSION,
        'cast': cast,
        'cast_fallback_roles': fallbacks,
        'episodes': quality,
    }
    (OUT / 'quality-n3.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.rmtree(TMP, ignore_errors=True)
    print('Série 2 N3 concluída.')


if __name__ == '__main__':
    asyncio.run(main())
