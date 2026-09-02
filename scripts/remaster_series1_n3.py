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
from n3_casting import assert_cast_gender, choose_voice, pool_ready, require_balanced_pool

ROOT = Path(__file__).resolve().parents[1]
ROTEIROS = ROOT / "roteiros" / "serie-1"
OUT = ROOT / "assets" / "audio" / "serie-1"
TMP = ROOT / ".tmp_serie1_n3"
APP = ROOT / "app.js"

VERSION = "n3-ptbr-native-20260901"
VERSION_TAG = "n3"
OPENING_SILENCE_MS = 160
ENDING_SILENCE_MS = 320
TARGET_DBFS = -18.0
MAX_CONCURRENT_SYNTH = 2
SYNTH_TIMEOUT_SECONDS = 80
MAX_TTS_CHARS = 620

CANONICAL_GREETING = "Olá, caros abordadores."
GREETING_RE = re.compile(r"\bol[áa]\s*,?\s+pessoal\b[.!?…]*", flags=re.I)
MULTIVOICE_EPISODES = {6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 19, 20}

VOICE_CANDIDATES = [
    ("pt-BR-FranciscaNeural", "F"),
    ("pt-BR-AntonioNeural", "M"),
    ("pt-BR-ThalitaNeural", "F"),
    ("pt-BR-FabioNeural", "M"),
    ("pt-BR-BrendaNeural", "F"),
    ("pt-BR-DonatoNeural", "M"),
    ("pt-BR-GiovannaNeural", "F"),
    ("pt-BR-HumbertoNeural", "M"),
    ("pt-BR-JulioNeural", "M"),
    ("pt-BR-NicolauNeural", "M"),
    ("pt-BR-ValerioNeural", "M"),
    ("pt-BR-LeilaNeural", "F"),
    ("pt-BR-ManuelaNeural", "F"),
    ("pt-BR-YaraNeural", "F"),
]

PREFIXES = {
    "INSTRUTOR": ("narrator", None),
    "NARRADOR": ("narrator", None),
    "PROFISSIONAL": ("professional", None),
    "ABORDADOR_M": ("professional", "M"),
    "ABORDADOR_F": ("professional", "F"),
    "ABORDADOR": ("professional", None),
    "ABORDADORA": ("professional", "F"),
    "TENTANTE_M": ("person_in_crisis", "M"),
    "TENTANTE_F": ("person_in_crisis", "F"),
    "TENTANTE": ("person_in_crisis", None),
    "DEMO_M": ("professional", "M"),
    "DEMO_F": ("professional", "F"),
}


SPEAKER_PERSONA = {
    "INSTRUTOR": {"rate": 0, "pitch": 0, "label": "instrutor"},
    "NARRADOR": {"rate": 0, "pitch": 0, "label": "narrador"},
    "PROFISSIONAL": {"rate": 0, "pitch": 0, "label": "profissional"},
    "ABORDADOR_M": {"rate": 0, "pitch": 3, "label": "masculino-profissional"},
    "TENTANTE_M": {"rate": -3, "pitch": -5, "label": "masculino-crise-dsp"},
    "DEMO_M": {"rate": 2, "pitch": 2, "label": "masculino-demo"},
    "ABORDADOR_F": {"rate": 0, "pitch": 1, "label": "feminino-profissional"},
    "TENTANTE_F": {"rate": -2, "pitch": -2, "label": "feminino-crise"},
    "DEMO_F": {"rate": 1, "pitch": 2, "label": "feminino-demo"},
    "ABORDADOR": {"rate": 0, "pitch": 0, "label": "abordador"},
    "ABORDADORA": {"rate": 0, "pitch": 1, "label": "abordadora"},
    "TENTANTE": {"rate": -2, "pitch": -1, "label": "tentante"},
}


def persona_for(speaker: str) -> dict:
    return SPEAKER_PERSONA.get(speaker, {"rate": 0, "pitch": 0, "label": speaker.lower()})


def apply_speaker_persona(rate: str, pitch: str, speaker: str) -> tuple[str, str]:
    cfg = persona_for(speaker)
    r = int(rate.rstrip("%")) + int(cfg["rate"])
    p = int(pitch.replace("Hz", "")) + int(cfg["pitch"])
    return f"{max(-16, min(8, r)):+d}%", f"{max(-7, min(7, p)):+d}Hz"



CHARACTER_DSP = {
    "TENTANTE_M": {"pitch_shift_semitones": -2.2, "high_pass_hz": 80, "low_pass_hz": 4200},
}


def character_dsp_profile(speaker: str) -> dict:
    return CHARACTER_DSP.get(speaker, {"pitch_shift_semitones": 0.0})


def apply_character_dsp(segment: AudioSegment, speaker: str) -> AudioSegment:
    cfg = CHARACTER_DSP.get(speaker)
    if not cfg:
        return segment
    semitones = float(cfg["pitch_shift_semitones"])
    factor = 2.0 ** (semitones / 12.0)
    shifted_rate = max(8000, int(segment.frame_rate * factor))
    segment = segment._spawn(segment.raw_data, overrides={"frame_rate": shifted_rate}).set_frame_rate(segment.frame_rate)
    segment = segment.high_pass_filter(int(cfg["high_pass_hz"]))
    segment = segment.low_pass_filter(int(cfg["low_pass_hz"]))
    return segment

def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def persist_canonical_greeting() -> int:
    changed = 0
    for path in sorted(ROTEIROS.glob("a1-*.txt")):
        original = path.read_text(encoding="utf-8")
        updated = GREETING_RE.sub(CANONICAL_GREETING, original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def split_once(text: str, phrase: str, speaker: str):
    idx = text.lower().find(phrase.lower())
    if idx < 0:
        return [(None, text)]
    before = text[:idx].strip(" ,")
    spoken = text[idx:idx + len(phrase)].strip()
    after = text[idx + len(phrase):].strip(" ,")
    out = []
    if before:
        out.append((None, before))
    if spoken:
        out.append((speaker, spoken))
    if after:
        out.append((None, after))
    return out


def curated_segments(number: int, text: str) -> list[tuple[str | None, str]]:
    text = normalize_space(text)
    if number == 6:
        parts: list[tuple[str | None, str]] = [(None, text)]
        phrases = [
            ("Oi, meu nome é Thais, sou bombeira militar e estou aqui para te ouvir.", "DEMO_F"),
            ("Estou aqui para ajudar", "DEMO_M"),
            ("Bom dia", "DEMO_F"),
            ("Como você está", "DEMO_M"),
        ]
        for phrase, speaker in phrases:
            newer = []
            for current_speaker, chunk in parts:
                if current_speaker is not None:
                    newer.append((current_speaker, chunk))
                else:
                    newer.extend(split_once(chunk, phrase, speaker))
            parts = newer
        return parts

    if number == 7:
        marker = "qual é o seu nome? Você tem filhos? Qual o nome deles? Com quem você mora? Ou até o que você gosta de fazer?"
        return split_once(text, marker, "DEMO_M")

    if number == 16:
        text = re.sub(r"\bSena\.\s*Camila\.\s*", "Camila. ", text, flags=re.I)
        m = re.search(r"\bAbordador\.\s*", text, flags=re.I)
        if m:
            return [(None, text[:m.start()].strip()), ("ABORDADOR_M", text[m.end():].strip())]

    if number == 19:
        parts: list[tuple[str | None, str]] = [(None, text)]
        for phrase in ("Para você, pareço ser essa pessoa.", "você está segurando a mochila firmemente."):
            newer = []
            for current_speaker, chunk in parts:
                if current_speaker is not None:
                    newer.append((current_speaker, chunk))
                else:
                    newer.extend(split_once(chunk, phrase, "DEMO_M"))
            parts = newer
        return parts

    if number == 20:
        parts: list[tuple[str | None, str]] = [(None, text)]
        phrases = [
            "Cláudia, aqui é o Júlio, Bombeiro Militar. Preciso que você me responda.",
            "Vou contar até três. Se você não responder, teremos que arrombar a porta.",
            "Cláudia, vou contar mais uma vez até três. Se você continuar em silêncio, terei que arrombar a porta. Por favor, responda.",
            "Um, dois, três.",
        ]
        for phrase in phrases:
            newer = []
            for current_speaker, chunk in parts:
                if current_speaker is not None:
                    newer.append((current_speaker, chunk))
                else:
                    newer.extend(split_once(chunk, phrase, "ABORDADOR_M"))
            parts = newer
        return parts

    return [(None, text)]


def parse_line(line: str):
    for prefix, (role, gender) in PREFIXES.items():
        if line.startswith(prefix + ":"):
            return prefix, role, gender, line.split(":", 1)[1].strip()
    return "INSTRUTOR", "narrator", None, line


def raw_turns(number: int):
    path = ROTEIROS / f"a1-{number:03d}.txt"
    turns = []
    source_spoken = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        speaker, role, gender, text = parse_line(line)
        if not text:
            continue
        segments = curated_segments(number, text) if speaker == "INSTRUTOR" and number in {6, 7, 16, 19, 20} else [(speaker, text)]
        for override, chunk in segments:
            if not chunk:
                continue
            seg_speaker = override or speaker
            seg_role, seg_gender = PREFIXES.get(seg_speaker, (role, gender))
            spoken = legacy.add_prosodic_punctuation(chunk)
            for unit in breath_units(spoken):
                turns.append({"speaker": seg_speaker, "role": seg_role, "gender": seg_gender, "text": unit})
            source_spoken.append(chunk)
    if not turns:
        raise RuntimeError(f"Roteiro vazio: {path}")
    if lexical_tokens(" ".join(source_spoken)) != lexical_tokens(" ".join(x["text"] for x in turns)):
        raise RuntimeError(f"Gate lexical falhou em A1-{number:03d}")
    return turns


def compact_turns(turns: list[dict]) -> list[dict]:
    """Agrupa unidades consecutivas do mesmo locutor para reduzir chamadas ao TTS sem fundir personagens."""
    out: list[dict] = []
    for turn in turns:
        if out and out[-1]["speaker"] == turn["speaker"] and len(out[-1]["text"]) + 1 + len(turn["text"]) <= MAX_TTS_CHARS:
            out[-1]["text"] = normalize_space(out[-1]["text"] + " " + turn["text"])
        else:
            out.append(dict(turn))
    return out


async def probe_voice(name: str) -> bool:
    TMP.mkdir(parents=True, exist_ok=True)
    path = TMP / ("probe-" + re.sub(r"[^A-Za-z0-9_-]+", "_", name) + ".mp3")
    for attempt in range(1, 4):
        try:
            c = edge_tts.Communicate(text="Teste breve de voz neural.", voice=name, rate="-2%", pitch="+0Hz", volume="+0%")
            await asyncio.wait_for(c.save(str(path)), timeout=40)
            ok = path.exists() and path.stat().st_size > 500
            path.unlink(missing_ok=True)
            if ok:
                print(f"[VOICE OK] {name}")
                return True
        except Exception as exc:
            path.unlink(missing_ok=True)
            print(f"[VOICE PROBE {attempt}/3] {name}: {type(exc).__name__}")
            await asyncio.sleep(1.2 * attempt)
    return False


async def resolve_operational_pool():
    operational = []
    for name, gender in VOICE_CANDIDATES:
        if await probe_voice(name):
            operational.append({"voice": name, "gender": gender})
        if pool_ready(operational, min_male=1, min_female=1):
            break
    require_balanced_pool(operational, min_male=1, min_female=1)
    return operational


def voice_preferences(role: str, gender: str | None):
    female = [
        "pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural", "pt-BR-BrendaNeural",
        "pt-BR-GiovannaNeural", "pt-BR-LeilaNeural", "pt-BR-ManuelaNeural", "pt-BR-YaraNeural",
    ]
    male = [
        "pt-BR-AntonioNeural", "pt-BR-FabioNeural", "pt-BR-DonatoNeural",
        "pt-BR-HumbertoNeural", "pt-BR-JulioNeural", "pt-BR-NicolauNeural", "pt-BR-ValerioNeural",
    ]
    if role == "narrator":
        return female + male
    if gender == "F":
        return female
    if gender == "M":
        return male
    return female + male

def build_episode_cast(turns: list[dict], pool: list[dict]):
    speakers = []
    info = {}
    for turn in turns:
        if turn["speaker"] not in info:
            speakers.append(turn["speaker"])
            info[turn["speaker"]] = (turn["role"], turn["gender"])

    cast: dict[str, str] = {}
    used: set[str] = set()
    non_narrators = [s for s in speakers if info[s][0] != "narrator"]
    narrators = [s for s in speakers if info[s][0] == "narrator"]

    for speaker in non_narrators:
        role, gender = info[speaker]
        cast[speaker] = choose_voice(pool, voice_preferences(role, gender), expected_gender=gender, used=used)
        used.add(cast[speaker])

    for speaker in narrators:
        cast[speaker] = choose_voice(pool, voice_preferences("narrator", None), expected_gender=None, used=used)
        used.add(cast[speaker])

    expected_gender = {speaker: info[speaker][1] for speaker in speakers}
    assert_cast_gender(cast, expected_gender, context="Série 1")
    if any("Multilingual" in voice for voice in cast.values()):
        raise RuntimeError(f"Série 1: voz multilíngue proibida no casting: {cast}")
    if any(not voice.startswith("pt-BR-") for voice in cast.values()):
        raise RuntimeError(f"Série 1: voz fora de pt-BR no casting: {cast}")
    return cast


async def synth(text, voice, rate, pitch, path, sem):
    async with sem:
        last_exc = None
        for attempt in range(1, 9):
            try:
                await asyncio.sleep(0.18)
                c = edge_tts.Communicate(text=speakable(text), voice=voice, rate=rate, pitch=pitch, volume="+0%")
                await asyncio.wait_for(c.save(str(path)), timeout=SYNTH_TIMEOUT_SECONDS)
                if path.exists() and path.stat().st_size > 500:
                    return
                raise RuntimeError("arquivo TTS vazio")
            except Exception as exc:
                last_exc = exc
                path.unlink(missing_ok=True)
                excerpt = normalize_space(text)[:80]
                print(f"[TTS RETRY {attempt}/8] {voice} | {type(exc).__name__} | {excerpt}")
                if attempt < 8:
                    await asyncio.sleep(min(12.0, 1.6 * attempt))
        raise RuntimeError(f"Falha TTS persistente | voz={voice} | trecho={normalize_space(text)[:120]}") from last_exc


async def build_episode(number: int, pool: list[dict], sem: asyncio.Semaphore):
    turns = compact_turns(raw_turns(number))
    cast = build_episode_cast(turns, pool)
    work = TMP / f"a1-{number:03d}"
    work.mkdir(parents=True, exist_ok=True)
    sequence = []
    roles = []
    speakers = []
    intents = []

    for idx, turn in enumerate(turns):
        role = turn["role"]
        p = prosody(turn["text"], profile="dialogue" if number in MULTIVOICE_EPISODES else "clinical", role=role)
        rate, pitch, pause = p.rate, p.pitch, p.pause_ms
        if CANONICAL_GREETING.lower().rstrip(".") in turn["text"].lower():
            rate, pitch, pause = "-1%", "+0Hz", 420
        if role == "person_in_crisis":
            rate = f"{max(-14, int(rate.rstrip('%')) - 2):+d}%"
        rate, pitch = apply_speaker_persona(rate, pitch, turn["speaker"])
        part = work / f"{idx:03d}.mp3"
        voice = cast[turn["speaker"]]
        await synth(turn["text"], voice, rate, pitch, part, sem)
        sequence.append((part, 0 if idx == len(turns)-1 else pause, turn["speaker"]))
        roles.append(role)
        speakers.append(turn["speaker"])
        intents.append(p.intent)

    audio = AudioSegment.silent(duration=OPENING_SILENCE_MS)
    for part, pause, speaker in sequence:
        rendered = AudioSegment.from_file(part, format="mp3")
        audio += apply_character_dsp(rendered, speaker)
        if pause:
            audio += AudioSegment.silent(duration=pause)
    audio += AudioSegment.silent(duration=ENDING_SILENCE_MS)
    audio = effects.compress_dynamic_range(audio, threshold=-20.0, ratio=2.0, attack=8.0, release=70.0)
    if audio.dBFS != float("-inf"):
        audio = audio.apply_gain(TARGET_DBFS - audio.dBFS)
    if audio.max_dBFS > -1.2:
        audio = audio.apply_gain(-1.2 - audio.max_dBFS)

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"a1-{number:03d}-{VERSION_TAG}.mp3"
    audio.export(target, format="mp3", bitrate="128k", parameters=["-ac", "1", "-ar", "44100"])

    episode_speakers = list(dict.fromkeys(speakers))
    unique_voices = sorted({cast[s] for s in episode_speakers})
    non_narrators = [s for s in episode_speakers if PREFIXES.get(s, ("narrator", None))[0] != "narrator"]
    voice_identity = {s: f"{cast[s]}::{persona_for(s)['label']}" for s in episode_speakers}
    if number in MULTIVOICE_EPISODES and len(set(voice_identity.values())) < 2:
        raise RuntimeError(f"A1-{number:03d} não ficou multivoz por identidade perceptual.")
    if len(non_narrators) >= 2 and len({voice_identity[s] for s in non_narrators}) != len(non_narrators):
        raise RuntimeError(f"A1-{number:03d}: personagens simultâneos sem personas distintas.")

    return {
        "episode": number,
        "output": target.name,
        "version": VERSION,
        "greeting": CANONICAL_GREETING,
        "profile": "N3-C-dialogue" if number in MULTIVOICE_EPISODES else "N3-C",
        "speakers": episode_speakers,
        "speaker_cast": {s: cast[s] for s in episode_speakers},
        "speaker_gender": {s: PREFIXES.get(s, ("narrator", None))[1] for s in episode_speakers},
        "speaker_persona": {s: persona_for(s) for s in episode_speakers},
        "speaker_dsp": {s: character_dsp_profile(s) for s in episode_speakers},
        "voice_identity": voice_identity,
        "voices": unique_voices,
        "multivoice_required": number in MULTIVOICE_EPISODES,
        "pronunciation_dictionary": True,
        "native_ptbr_only": True,
        "intents": sorted(set(intents)),
        "turns": len(turns),
        "duration_seconds": round(len(audio) / 1000, 1),
    }


def patch_app_urls():
    content = APP.read_text(encoding="utf-8")
    match = re.search(r"const AUDIOS=\{1:\[(.*?)\],2:\[", content, re.S)
    if not match:
        raise RuntimeError("Bloco Série 1 não localizado em app.js")
    block = match.group(1)
    entries = list(re.finditer(r'\{title:"([^"]+)",url:"([^"]+)"\}', block))
    if len(entries) != 21:
        raise RuntimeError(f"Esperados 21 episódios; encontrados {len(entries)}")
    new_block = block
    for idx, item in reversed(list(enumerate(entries, start=1))):
        title = item.group(1)
        repl = f'{{title:"{title}",url:"assets/audio/serie-1/a1-{idx:03d}-{VERSION_TAG}.mp3?v={VERSION}"}}'
        new_block = new_block[:item.start()] + repl + new_block[item.end():]
    content = content[:match.start(1)] + new_block + content[match.end(1):]
    APP.write_text(content, encoding="utf-8")


async def render_series(pool: list[dict], sem: asyncio.Semaphore, builder=None):
    """Renderiza episódios em paralelo; o semaphore continua limitando chamadas TTS."""
    builder = builder or build_episode

    async def render(number: int):
        print(f"[A1-{number:03d}] render")
        return await builder(number, pool, sem)

    results = await asyncio.gather(*(render(number) for number in range(1, 22)))
    return sorted(results, key=lambda item: item["episode"])


async def main():
    changed_sources = persist_canonical_greeting()
    TMP.mkdir(parents=True, exist_ok=True)
    pool = await resolve_operational_pool()
    print("[POOL]", json.dumps(pool, ensure_ascii=False))
    sem = asyncio.Semaphore(MAX_CONCURRENT_SYNTH)
    quality = await render_series(pool, sem)
    patch_app_urls()
    report = {
        "version": VERSION,
        "canonical_greeting": CANONICAL_GREETING,
        "source_files_rewritten": changed_sources,
        "operational_voice_pool": pool,
        "native_ptbr_only": True,
        "multivoice_episodes": sorted(MULTIVOICE_EPISODES),
        "episodes": quality,
    }
    (OUT / "quality-n3.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(TMP, ignore_errors=True)
    print("Série 1 N3 casting concluída.")


if __name__ == "__main__":
    asyncio.run(main())
