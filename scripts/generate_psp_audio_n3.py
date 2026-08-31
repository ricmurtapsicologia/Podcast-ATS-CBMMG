from __future__ import annotations

import asyncio
import json
import re
import shutil
from pathlib import Path

import edge_tts
from pydub import AudioSegment, effects

from n3_audio_core import breath_units, lexical_tokens, prosody

ROOT=Path(__file__).resolve().parents[1]
ROTEIROS=ROOT/'roteiros'/'serie-3'
OUT=ROOT/'assets'/'audio'/'serie-3'
TMP=ROOT/'.tmp_psp_n3'
PSP_JS=ROOT/'psp.js'
VOICE_INSTRUTOR='pt-BR-AntonioNeural'
VOICE_PROFISSIONAL='pt-BR-FranciscaNeural'
VERSION='n3-20260831'
PATTERN=re.compile(r'^\*\*(INSTRUTOR|PROFISSIONAL):\*\*\s*(.+)$')


def read_turns(path:Path):
    turns=[];source=[];spoken=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        m=PATTERN.match(line.strip())
        if not m:continue
        speaker,text=m.group(1),m.group(2).strip()
        source.extend(lexical_tokens(text))
        for unit in breath_units(text):
            turns.append((speaker,unit));spoken.extend(lexical_tokens(unit))
    if not turns or source!=spoken:raise RuntimeError(f'Gate lexical N3 falhou em {path.name}')
    return turns


async def synth(text,voice,rate,pitch,path,sem):
    async with sem:
        for attempt in range(1,4):
            try:
                c=edge_tts.Communicate(text=text,voice=voice,rate=rate,pitch=pitch,volume='+0%')
                await asyncio.wait_for(c.save(str(path)),timeout=55);return
            except Exception:
                if attempt==3:raise
                await asyncio.sleep(.9*attempt)


async def build(number:int,sem):
    turns=read_turns(ROTEIROS/f'psp-{number:02d}.md')
    work=TMP/f'psp-{number:02d}';work.mkdir(parents=True,exist_ok=True)
    tasks=[];seq=[];intents=[]
    for i,(speaker,text) in enumerate(turns):
        voice=VOICE_INSTRUTOR if speaker=='INSTRUTOR' else VOICE_PROFISSIONAL
        role='narrator' if speaker=='INSTRUTOR' else 'professional'
        p=prosody(text,profile='clinical',role=role)
        part=work/f'{i:03d}.mp3';seq.append((part,0 if i==len(turns)-1 else p.pause_ms))
        tasks.append(synth(text,voice,p.rate,p.pitch,part,sem));intents.append(p.intent)
    await asyncio.gather(*tasks)
    audio=AudioSegment.silent(duration=150)
    for part,pause in seq:
        audio+=AudioSegment.from_file(part,format='mp3')
        if pause:audio+=AudioSegment.silent(duration=pause)
    audio+=AudioSegment.silent(duration=280)
    audio=effects.compress_dynamic_range(audio,threshold=-20.0,ratio=2.0,attack=8.0,release=70.0)
    if audio.dBFS!=float('-inf'):audio=audio.apply_gain(-18.0-audio.dBFS)
    if audio.max_dBFS>-1.2:audio=audio.apply_gain(-1.2-audio.max_dBFS)
    target=OUT/f'psp-{number:02d}-n3.mp3';OUT.mkdir(parents=True,exist_ok=True)
    audio.export(target,format='mp3',bitrate='128k',parameters=['-ac','1','-ar','44100'])
    seconds=round(len(audio)/1000,1)
    if not 95<=seconds<=330:raise RuntimeError(f'Duração atípica em {target.name}: {seconds}s')
    return {'card':number,'output':target.name,'version':VERSION,'profile':'N3-C','turns':len(turns),'intents':sorted(set(intents)),'duration_seconds':seconds}


def patch_runtime():
    s=PSP_JS.read_text(encoding='utf-8')
    s=re.sub(r'`assets/audio/serie-3/psp-\$\{pad\(index \+ 1\)\}\.mp3`',r'`assets/audio/serie-3/psp-${pad(index + 1)}-n3.mp3`',s)
    s=s.replace('padrão N2','padrão N3 Natural').replace('Áudio N2','Áudio N3').replace('10 microaulas N2','10 microaulas N3')
    PSP_JS.write_text(s,encoding='utf-8')


async def main():
    TMP.mkdir(parents=True,exist_ok=True);sem=asyncio.Semaphore(5);rows=[]
    for n in range(1,11):rows.append(await build(n,sem))
    patch_runtime()
    (OUT/'quality-psp-n3.json').write_text(json.dumps({'version':VERSION,'cards':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.rmtree(TMP,ignore_errors=True)
    print('PSP N3 concluído: 10/10 microaulas.')

if __name__=='__main__':asyncio.run(main())
