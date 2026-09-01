from __future__ import annotations

import asyncio
import json
import re
import shutil
from pathlib import Path

import edge_tts
from pydub import AudioSegment, effects

from n3_audio_core import breath_units, normalize, prosody, speakable
from n3_foley import apply_sound_design

ROOT = Path(__file__).resolve().parents[1]
ROTEIROS = ROOT / "roteiros" / "serie-2"
OUT = ROOT / "assets" / "audio" / "serie-2"
TMP = ROOT / ".tmp_serie2_n3"
APP = ROOT / "app.js"
SOUND_DESIGN = ROOT / "sound-design" / "series-2.json"
VERSION_TAG = "n3"
VERSION = "n3-cast-20260901"
OPENING_SILENCE_MS = 160
ENDING_SILENCE_MS = 320
TARGET_DBFS = -18.0
MAX_CONCURRENT_SYNTH = 4
SYNTH_TIMEOUT_SECONDS = 70
CINEMATIC_EPISODES = {4, 5, 6, 7, 8, 9}

VOICE_CANDIDATES = [
    ("pt-BR-MacerioMultilingualNeural", "M"),
    ("pt-BR-ThalitaMultilingualNeural", "F"),
    ("pt-BR-AntonioNeural", "M"),
    ("pt-BR-FranciscaNeural", "F"),
    ("pt-BR-ThalitaNeural", "F"),
    ("pt-BR-FabioNeural", "M"),
    ("pt-BR-BrendaNeural", "F"),
    ("pt-BR-DonatoNeural", "M"),
    ("pt-BR-GiovannaNeural", "F"),
]

ROLE_GENDER = {
    "narrator": None, "gorette": "F", "maria": "F", "claudio": "M",
    "ana": "F", "guilherme": "M", "fernanda": "F", "host": "M",
    "julia": "F", "dra_sara": "F", "lourdes": "F", "fatima": "F",
}
ROLE_STYLE = {
    "narrator": "narrator", "gorette": "family", "maria": "person_in_crisis",
    "claudio": "person_in_crisis", "ana": "family", "guilherme": "professional",
    "fernanda": "person_in_crisis", "host": "host", "julia": "guest",
    "dra_sara": "professional", "lourdes": "family", "fatima": "family",
}
PERSONA_ADJUST = {
    "narrator": {"rate": 0, "pitch": -1, "label": "narrador-estavel"},
    "gorette": {"rate": -2, "pitch": -2, "label": "materna-contida"},
    "maria": {"rate": -4, "pitch": -1, "label": "fragil-hesitante"},
    "claudio": {"rate": 1, "pitch": -2, "label": "energia-oscilante"},
    "ana": {"rate": -1, "pitch": 1, "label": "proxima-preocupada"},
    "guilherme": {"rate": -2, "pitch": -1, "label": "profissional-calmo"},
    "fernanda": {"rate": -3, "pitch": 0, "label": "tensa-contida"},
    "host": {"rate": 1, "pitch": 1, "label": "apresentador-claro"},
    "julia": {"rate": -1, "pitch": 2, "label": "jovem-reflexiva"},
    "dra_sara": {"rate": -1, "pitch": -2, "label": "clinica-segura"},
    "lourdes": {"rate": -3, "pitch": -3, "label": "madura-afetiva"},
    "fatima": {"rate": -1, "pitch": 1, "label": "acolhedora-pragmatica"},
}
ROLE_PREFERENCES = {
    "narrator": ["pt-BR-MacerioMultilingualNeural", "pt-BR-AntonioNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural"],
    "gorette": ["pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-AntonioNeural"],
    "maria": ["pt-BR-ThalitaMultilingualNeural", "pt-BR-ThalitaNeural", "pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"],
    "claudio": ["pt-BR-MacerioMultilingualNeural", "pt-BR-AntonioNeural", "pt-BR-FabioNeural", "pt-BR-FranciscaNeural"],
    "ana": ["pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"],
    "guilherme": ["pt-BR-AntonioNeural", "pt-BR-MacerioMultilingualNeural", "pt-BR-FranciscaNeural"],
    "fernanda": ["pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-AntonioNeural"],
    "host": ["pt-BR-MacerioMultilingualNeural", "pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"],
    "julia": ["pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"],
    "dra_sara": ["pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-AntonioNeural"],
    "lourdes": ["pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"],
    "fatima": ["pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-AntonioNeural"],
}
CONFLICT_PAIRS = [
    ("gorette", "maria"), ("claudio", "ana"), ("guilherme", "fernanda"),
    ("host", "julia"), ("host", "dra_sara"), ("lourdes", "fatima"),
]


def read_text(number: int) -> str:
    path = ROTEIROS / f"a2-{number:03d}.txt"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("#")]
    text = normalize(" ".join(lines))
    if not text:
        raise RuntimeError(f"Roteiro vazio: {path}")
    return text


def sentence_list(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text) if s.strip()]


def is_stage_direction(number: int, sentence: str) -> bool:
    return number == 9 and sentence.lower().strip().startswith("sons de chícaras sendo colocadas na mesa")


def speaker_for(number: int, sentence: str) -> str:
    low = sentence.lower().strip()
    if number == 4:
        if low.startswith("gorette ") or low.startswith("minha filha"):
            return "gorette"
        if low.startswith("maria ") or low.startswith(("não, mãe", "é difícil", "é isso que", "não, tem noites", "não sinto", "já pensei", "obrigada, mãe")):
            return "maria"
        return "narrator"
    if number == 5:
        if low.startswith("cláudio ") or low.startswith(("vocês precisam", "você é a pessoa", "ana, você", "mas sabe")):
            return "claudio"
        if low.startswith("ana "):
            return "ana"
        return "narrator"
    if number == 6:
        if low.startswith(("oi, eu sou guilherme", "importa, sim", "o que você", "posso te ajudar", "entendo que", "parece que", "desde quando", "isso deve ser", "fernanda, antes", "e antes de começar", "sua mãe ainda", "eu entendo que", "vamos sair daqui")):
            return "guilherme"
        if low.startswith(("fernanda.", "mas isso", "nada mais", "eu não sei", "minha vida", "minha mãe", "eu só", "sim, mas", "desde que", "sim, usei", "trabalhava num salão", "eu gostava", "ela diz", "eu não consigo", "eu queria")):
            return "fernanda"
        return "narrator"
    if number == 7:
        if low.startswith(("programa em foco", "entrevistador", "boa noite", "vamos começar", "e foi nesse", "e como esse", "como o transtorno", "hoje você", "julia, sua história", "no próximo bloco")) or sentence.endswith("?"):
            return "host"
        return "julia"
    if number == 8:
        if low.startswith(("programa infoco", "estamos de volta", "no bloco anterior", "agora, para", "dr. sara", "o que são", "como eles", "e qual a relação", "pode explicar", "e como é", "entrevistador")) or sentence.endswith("?"):
            return "host"
        return "dra_sara"
    if number == 9:
        if low.startswith(("bem-vindos", "hoje trazemos", "ao longo", "vamos ouvir", "essa foi a conversa", "a esquizofrenia", "buscar ajuda", "no próximo episódio")):
            return "narrator"
        if low.startswith(("lourdes, você", "ela ainda ouve", "e você está cuidando", "e ela ainda tem sonhos")):
            return "fatima"
        if low.startswith(("ah, fatima", "sim, às vezes", "sim, as vezes", "fatima, ela já", "fatima, como você reage", "estou tentando, fatima", "sim, quer")):
            return "lourdes"
        if low.startswith(("já. durante", "eu respiro fundo")):
            return "fatima"
        return "lourdes"
    return "narrator"


def build_turns(number: int, text: str):
    turns, stage_directions, spoken_source = [], [], []
    for sentence in sentence_list(text):
        if is_stage_direction(number, sentence):
            stage_directions.append(sentence)
            continue
        spoken_source.append(sentence)
        role = speaker_for(number, sentence)
        for unit in breath_units(sentence):
            turns.append((role, unit))
    if not turns:
        raise RuntimeError(f"Nenhum turno em A2-{number:03d}")
    source_tokens = re.findall(r"[\wÀ-ÿ]+", " ".join(spoken_source).lower())
    rebuilt_tokens = re.findall(r"[\wÀ-ÿ]+", " ".join(t for _, t in turns).lower())
    if source_tokens != rebuilt_tokens:
        raise RuntimeError(f"Gate lexical falhou em A2-{number:03d}")
    return turns, stage_directions


async def probe_voice(name: str) -> bool:
    TMP.mkdir(parents=True, exist_ok=True)
    probe = TMP / ("probe-" + re.sub(r"[^A-Za-z0-9_-]+", "_", name) + ".mp3")
    for attempt in range(2):
        try:
            c = edge_tts.Communicate(text="Teste breve de voz neural.", voice=name, rate="-2%", pitch="+0Hz", volume="+0%")
            await asyncio.wait_for(c.save(str(probe)), timeout=35)
            ok = probe.exists() and probe.stat().st_size > 500
            probe.unlink(missing_ok=True)
            if ok:
                print(f"[VOICE OK] {name}")
                return True
        except Exception as exc:
            probe.unlink(missing_ok=True)
            print(f"[VOICE FAIL] {name}: {type(exc).__name__}")
            if attempt == 0:
                await asyncio.sleep(0.8)
    return False


async def resolve_operational_pool():
    operational = []
    for name, gender in VOICE_CANDIDATES[:4]:
        if await probe_voice(name):
            operational.append({"voice": name, "gender": gender})
    if len(operational) < 3:
        for name, gender in VOICE_CANDIDATES[4:]:
            if await probe_voice(name):
                operational.append({"voice": name, "gender": gender})
            if len(operational) >= 4:
                break
    if len(operational) < 2:
        raise RuntimeError("Menos de duas vozes neurais realmente operacionais.")
    return operational


def resolve_cast(pool: list[dict]) -> dict[str, str]:
    available = {x["voice"] for x in pool}
    cast = {}
    for role in ROLE_GENDER:
        cast[role] = next((v for v in ROLE_PREFERENCES[role] if v in available), pool[0]["voice"])
    for left, right in CONFLICT_PAIRS:
        if cast[left] != cast[right]:
            continue
        alternative = next((v for v in ROLE_PREFERENCES[right] if v in available and v != cast[left]), None)
        if alternative is None:
            alternative = next((x["voice"] for x in pool if x["voice"] != cast[left]), None)
        if alternative is None:
            raise RuntimeError(f"Não há segunda voz para {left}/{right}")
        cast[right] = alternative
    return cast


def persona_values(rate: str, pitch: str, role: str):
    cfg = PERSONA_ADJUST.get(role, {"rate": 0, "pitch": 0})
    r = int(rate.rstrip("%")) + int(cfg.get("rate", 0))
    p = int(pitch.replace("Hz", "")) + int(cfg.get("pitch", 0))
    return f"{max(-16, min(6, r)):+d}%", f"{max(-7, min(7, p)):+d}Hz"


async def synth(text, voice, rate, pitch, path, sem):
    async with sem:
        for attempt in range(1, 6):
            try:
                c = edge_tts.Communicate(text=speakable(text), voice=voice, rate=rate, pitch=pitch, volume="+0%")
                await asyncio.wait_for(c.save(str(path)), timeout=SYNTH_TIMEOUT_SECONDS)
                if path.exists() and path.stat().st_size > 500:
                    return
                raise RuntimeError("arquivo TTS vazio")
            except Exception:
                path.unlink(missing_ok=True)
                if attempt == 5:
                    raise
                await asyncio.sleep(1.0 * attempt)


def sound_design_for(number: int, data: dict):
    entry = data.get("episodes", {}).get(f"{number:03d}", {})
    return str(entry.get("scene", "none")), list(entry.get("events", []))


async def build_episode(number: int, cast: dict[str, str], sound_design: dict, sem):
    text = read_text(number)
    turns, stage_directions = build_turns(number, text)
    work = TMP / f"a2-{number:03d}"
    work.mkdir(parents=True, exist_ok=True)
    tasks, sequence, intents, roles, voices = [], [], [], [], []
    profile = "dialogue" if number in CINEMATIC_EPISODES else "narrative"

    for idx, (role, turn) in enumerate(turns):
        p = prosody(turn, profile=profile, role=ROLE_STYLE.get(role, "narrator"))
        rate, pitch = persona_values(p.rate, p.pitch, role)
        part = work / f"{idx:03d}.mp3"
        pause = 0 if idx == len(turns)-1 else p.pause_ms
        voice = cast[role]
        tasks.append(synth(turn, voice, rate, pitch, part, sem))
        sequence.append((part, pause))
        intents.append(p.intent); roles.append(role); voices.append(voice)
    await asyncio.gather(*tasks)

    merged = AudioSegment.silent(duration=OPENING_SILENCE_MS)
    for part, pause in sequence:
        merged += AudioSegment.from_file(part, format="mp3")
        if pause:
            merged += AudioSegment.silent(duration=pause)
    merged += AudioSegment.silent(duration=ENDING_SILENCE_MS)
    merged = effects.compress_dynamic_range(merged, threshold=-20.0, ratio=2.0, attack=8.0, release=70.0)
    if merged.dBFS != float("-inf"):
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
    target = OUT / f"a2-{number:03d}-{VERSION_TAG}.mp3"
    bitrate = "192k" if cinematic else "128k"
    channels = 2 if cinematic else 1
    merged.export(target, format="mp3", bitrate=bitrate, parameters=["-ac", str(channels), "-ar", "44100"])

    episode_roles = list(dict.fromkeys(roles))
    episode_cast = {r: cast[r] for r in episode_roles}
    if cinematic and len(set(episode_cast.values())) < 2:
        raise RuntimeError(f"A2-{number:03d} não ficou multivoz.")
    return {
        "episode": number, "output": target.name, "version": VERSION,
        "profile": "N3-D" if cinematic else "N3-C", "scene": scene,
        "events": events, "stage_directions_replaced_by_sound": stage_directions,
        "text_integrity_spoken_content": 1.0, "roles": episode_roles,
        "role_cast": episode_cast, "voices": sorted(set(episode_cast.values())),
        "persona_profiles": {r: PERSONA_ADJUST[r] for r in episode_roles},
        "intents": sorted(set(intents)), "turns": len(turns),
        "duration_seconds": round(len(merged)/1000, 1), "channels": channels,
        "sample_rate": 44100, "bitrate": bitrate,
    }


def patch_app_urls():
    content = APP.read_text(encoding="utf-8")
    m = re.search(r",2:\[(.*?)\],3:\[\]", content, re.S)
    if not m:
        raise RuntimeError("Bloco Série 2 não localizado em app.js")
    block = m.group(1)
    entries = list(re.finditer(r'\{title:"([^"]+)",url:"([^"]+)"\}', block))
    if len(entries) != 14:
        raise RuntimeError(f"Esperados 14 episódios; encontrados {len(entries)}")
    new_block = block
    for idx, match in reversed(list(enumerate(entries))):
        title = match.group(1)
        repl = f'{{title:"{title}",url:"assets/audio/serie-2/a2-{idx:03d}-{VERSION_TAG}.mp3?v={VERSION}"}}'
        new_block = new_block[:match.start()] + repl + new_block[match.end():]
    content = content[:m.start(1)] + new_block + content[m.end(1):]
    APP.write_text(content, encoding="utf-8")


async def main():
    sound_design = json.loads(SOUND_DESIGN.read_text(encoding="utf-8"))
    TMP.mkdir(parents=True, exist_ok=True)
    pool = await resolve_operational_pool()
    cast = resolve_cast(pool)
    print("[POOL]", json.dumps(pool, ensure_ascii=False))
    print("[CAST]", json.dumps(cast, ensure_ascii=False))
    sem = asyncio.Semaphore(MAX_CONCURRENT_SYNTH)
    quality = []
    for number in range(14):
        print(f"[A2-{number:03d}] render")
        quality.append(await build_episode(number, cast, sound_design, sem))
    patch_app_urls()
    report = {
        "version": VERSION, "operational_voice_pool": pool,
        "character_cast": cast,
        "cinematic_multivoice_episodes": sorted(CINEMATIC_EPISODES),
        "episodes": quality,
    }
    (OUT / "quality-n3.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(TMP, ignore_errors=True)
    print("Série 2 N3 casting concluída.")


if __name__ == "__main__":
    asyncio.run(main())
