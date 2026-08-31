from __future__ import annotations

import asyncio
import json
import re
import shutil
from pathlib import Path

import edge_tts
from pydub import AudioSegment, effects

import remaster_series1_organic as legacy
from n3_audio_core import breath_units, lexical_tokens, normalize, prosody

ROOT = Path(__file__).resolve().parents[1]
ROTEIROS = ROOT / 'roteiros' / 'serie-1'
OUT = ROOT / 'assets' / 'audio' / 'serie-1'
TMP = ROOT / '.tmp_serie1_n3'
APP = ROOT / 'app.js'
VERSION = 'n3-20260831'
VERSION_TAG = 'n3'
VOICE_INSTRUTOR = 'pt-BR-AntonioNeural'
VOICE_PROFISSIONAL = 'pt-BR-FranciscaNeural'
OPENING_SILENCE_MS = 180
ENDING_SILENCE_MS = 340
TARGET_DBFS = -18.0


def read_turns(number: int):
    path = ROTEIROS / f'a1-{number:03d}.txt'
    source_tokens=[]; spoken_tokens=[]; turns=[]
    for raw in path.read_text(encoding='utf-8').splitlines():
        line=raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('PROFISSIONAL:'):
            voice=VOICE_PROFISSIONAL; role='professional'; text=line.split(':',1)[1].strip()
        elif line.startswith('INSTRUTOR:'):
            voice=VOICE_INSTRUTOR; role='narrator'; text=line.split(':',1)[1].strip()
        else:
            voice=VOICE_INSTRUTOR; role='narrator'; text=line
        if not text:
            continue
        spoken=legacy.add_prosodic_punctuation(text)
        # Corrige apenas pontuação da saudação, preservando palavras.
        spoken=re.sub(r'\bolá\s*,?\s+pessoal\b[.!?…]*','Olá, pessoal.',spoken,flags=re.I)
        source_tokens.extend(lexical_tokens(text))
        for unit in breath_units(spoken):
            turns.append((voice,role,unit))
            spoken_tokens.extend(lexical_tokens(unit))
    if not turns or source_tokens!=spoken_tokens:
        raise RuntimeError(f'Gate lexical N3 falhou em A1-{number:03d}')
    return turns, len(source_tokens)


async def synth(text, voice, rate, pitch, path, sem):
    async with sem:
        for attempt in range(1,4):
            try:
                c=edge_tts.Communicate(text=text,voice=voice,rate=rate,pitch=pitch,volume='+0%')
                await asyncio.wait_for(c.save(str(path)),timeout=55)
                return
            except Exception:
                if attempt==3: raise
                await asyncio.sleep(.9*attempt)


async def build_episode(number:int,sem:asyncio.Semaphore):
    turns,word_count=read_turns(number)
    work=TMP/f'a1-{number:03d}';work.mkdir(parents=True,exist_ok=True)
    tasks=[];seq=[];intents=[];voices=[]
    for i,(voice,role,text) in enumerate(turns):
        p=prosody(text,profile='clinical',role=role)
        rate,pitch,pause=p.rate,p.pitch,p.pause_ms
        if lexical_tokens(text)==['olá','pessoal']:
            rate='-10%';pitch='+0Hz';pause=720
        part=work/f'{i:03d}.mp3'
        seq.append((part,0 if i==len(turns)-1 else pause))
        tasks.append(synth(text,voice,rate,pitch,part,sem))
        intents.append(p.intent);voices.append(voice)
    await asyncio.gather(*tasks)
    audio=AudioSegment.silent(duration=OPENING_SILENCE_MS)
    for part,pause in seq:
        audio+=AudioSegment.from_file(part,format='mp3')
        if pause:audio+=AudioSegment.silent(duration=pause)
    audio+=AudioSegment.silent(duration=ENDING_SILENCE_MS)
    audio=effects.compress_dynamic_range(audio,threshold=-20.0,ratio=2.0,attack=8.0,release=70.0)
    if audio.dBFS!=float('-inf'):audio=audio.apply_gain(TARGET_DBFS-audio.dBFS)
    if audio.max_dBFS>-1.2:audio=audio.apply_gain(-1.2-audio.max_dBFS)
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/f'a1-{number:03d}-{VERSION_TAG}.mp3'
    audio.export(target,format='mp3',bitrate='128k',parameters=['-ac','1','-ar','44100'])
    return {'episode':number,'output':target.name,'version':VERSION,'profile':'N3-C','lexical_integrity':1.0,
            'source_words':word_count,'turns':len(turns),'voices':sorted(set(voices)),'intents':sorted(set(intents)),
            'duration_seconds':round(len(audio)/1000,1)}


def patch_app_urls():
    content=APP.read_text(encoding='utf-8')
    block_match=re.search(r'const AUDIOS=\{1:\[(.*?)\],2:\[',content,re.S)
    if not block_match:raise RuntimeError('Bloco da Série 1 não localizado')
    block=block_match.group(1)
    entries=list(re.finditer(r'\{title:"([^"]+)",url:"([^"]+)"\}',block))
    if len(entries)!=21:raise RuntimeError(f'Esperados 21 episódios; encontrados {len(entries)}')
    new_block=block
    for idx,match in reversed(list(enumerate(entries,start=1))):
        title=match.group(1)
        replacement=f'{{title:"{title}",url:"assets/audio/serie-1/a1-{idx:03d}-{VERSION_TAG}.mp3"}}'
        new_block=new_block[:match.start()]+replacement+new_block[match.end():]
    content=content[:block_match.start(1)]+new_block+content[block_match.end(1):]
    APP.write_text(content,encoding='utf-8')


async def main():
    TMP.mkdir(parents=True,exist_ok=True)
    sem=asyncio.Semaphore(6)
    quality=[]
    for number in range(1,22):
        print(f'[A1-{number:03d}] N3 Natural')
        quality.append(await build_episode(number,sem))
    patch_app_urls()
    (OUT/'quality-n3.json').write_text(json.dumps({'version':VERSION,'episodes':quality},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.rmtree(TMP,ignore_errors=True)
    print('Série 1 N3 concluída.')

if __name__=='__main__':asyncio.run(main())
