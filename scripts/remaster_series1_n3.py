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
ROTEIROS = ROOT / "roteiros" / "serie-1"
OUT = ROOT / "assets" / "audio" / "serie-1"
TMP = ROOT / ".tmp_serie1_n3"
APP = ROOT / "app.js"

VERSION = "n3-cast-20260901"
VERSION_TAG = "n3"
OPENING_SILENCE_MS = 160
ENDING_SILENCE_MS = 320
TARGET_DBFS = -18.0
MAX_CONCURRENT_SYNTH = 4
SYNTH_TIMEOUT_SECONDS = 70

CANONICAL_GREETING = "Olá, caros abordadores."
GREETING_RE = re.compile(r"\bol[áa]\s*,?\s+pessoal\b[.!?…]*", flags=re.I)
MULTIVOICE_EPISODES = {6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 19, 20}

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
            new = []
            for current_speaker, chunk in parts:
                if current_speaker is not None:
                    new.append((current_speaker, chunk))
                    continue
                new.extend(split_once(chunk, phrase, speaker))
            parts = new
        return parts

    if number == 7:
        marker = "qual é o seu nome? Você tem filhos? Qual o nome deles? Com quem você mora? Ou até o que você gosta de fazer?"
        return split_once(text, marker, "DEMO_M")

    if number == 16:
        text = re.sub(r"\bSena\.\s*Camila\.\s*", "Camila. ", text, flags=re.I)
        m = re.search(r"\bAbordador\.\s*", text, flags=re.I)
        if m:
            before = text[:m.start()].strip()
            after = text[m.end():].strip()
            return [(None, before), ("ABORDADOR_M", after)]
        return [(None, text)]

    if number == 19:
        parts = [(None, text)]
        for phrase in (
            "Para você, pareço ser essa pessoa.",
            "você está segurando a mochila firmemente.",
        ):
            new = []
            for current_speaker, chunk in parts:
                if current_speaker is not None:
                    new.append((current_speaker, chunk))
                    continue
                new.extend(split_once(chunk, phrase, "DEMO_M"))
            parts = new
        return parts

    if number == 20:
        parts = [(None, text)]
        phrases = [
            "Cláudia, aqui é o Júlio, Bombeiro Militar. Preciso que você me responda.",
            "Vou contar até três. Se você não responder, teremos que arrombar a porta.",
            "Cláudia, vou contar mais uma vez até três. Se você continuar em silêncio, terei que arrombar a porta. Por favor, responda.",
            "Um, dois, três.",
        ]
        for phrase in phrases:
            new = []
            for current_speaker, chunk in parts:
                if current_speaker is not None:
                    new.append((current_speaker, chunk))
                    continue
                new.extend(split_once(chunk, phrase, "ABORDADOR_M"))
            parts = new
        return parts

    return [(None, text)]


def parse_line(raw: str) -> tuple[str, str, str | None]:
    line = raw.strip()
    for prefix, (role, gender) in PREFIXES.items():
        if line.startswith(prefix + ":"):
            return prefix, role, gender
    return "INSTRUTOR", "narrator", None


def source_turns(number: int):
    path = ROTEIROS / f"a1-{number:03d}.txt"
    turns: list[dict] = []
    source_spoken: list[str] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        speaker, role, gender = parse_line(line)
        if ":" in line and line.split(":", 1)[0] in PREFIXES:
            text = line.split(":", 1)[1].strip()
        else:
            text = line
        if not text:
            continue

        if speaker == "INSTRUTOR" and number in {6, 7, 16, 19, 20}:
            segments = curated_segments(number, text)
        else:
            segments = [(speaker, text)]

        for override, chunk in segments:
            if not chunk:
                continue
            seg_speaker = override or speaker
            seg_role, seg_gender = PREFIXES.get(seg_speaker, (role, gender))
            spoken = legacy.add_prosodic_punctuation(chunk)
            for unit in breath_units(spoken):
                turns.append({
                    "speaker": seg_speaker,
                    "role": seg_role,
                    "gender": seg_gender,
                    "text": unit,
                })
            source_spoken.append(chunk)

    if not turns:
        raise RuntimeError(f"Roteiro vazio: {path}")

    source_tokens = lexical_tokens(" ".join(source_spoken))
    rebuilt_tokens = lexical_tokens(" ".join(t["text"] for t in turns))
    if source_tokens != rebuilt_tokens:
        raise RuntimeError(f"Gate lexical falhou em A1-{number:03d}")
    return turns


async def probe_voice(name: str) -> bool:
    TMP.mkdir(parents=True, exist_ok=True)
    probe = TMP / ("probe-" + re.sub(r"[^A-Za-z0-9_-]+", "_", name) + ".mp3")
    for attempt in range(2):
        try:
            c = edge_tts.Communicate(
                text="Teste breve de voz neural.", voice=name,
                rate="-2%", pitch="+0Hz", volume="+0%",
            )
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


def voice_preferences(speaker: str, role: str, gender: str | None) -> list[str]:
    if role == "narrator":
        return ["pt-BR-MacerioMultilingualNeural", "pt-BR-AntonioNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural"]
    if gender == "F":
        return ["pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural", "pt-BR-BrendaNeural", "pt-BR-GiovannaNeural", "pt-BR-MacerioMultilingualNeural", "pt-BR-AntonioNeural"]
    if gender == "M":
        return ["pt-BR-MacerioMultilingualNeural", "pt-BR-AntonioNeural", "pt-BR-FabioNeural", "pt-BR-DonatoNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural"]
    return ["pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-AntonioNeural", "pt-BR-MacerioMultilingualNeural"]


def build_episode_cast(turns: list[dict], pool: list[dict]) -> dict[str, str]:
    available = {x["voice"]: x for x in pool}
    speakers = []
    info = {}
    for t in turns:
        s = t["speaker"]
        if s not in info:
            speakers.append(s)
            info[s] = (t["role"], t["gender"])

    cast: dict[str, str] = {}
    used_characters: set[str] = set()
    for speaker in [s for s in speakers if info[s][0] != "narrator"]:
        role, gender = info[speaker]
        prefs = voice_preferences(speaker, role, gender)
        choice = next((v for v in prefs if v in available and v not in used_characters), None)
        if choice is None:
            choice = next((v for v in prefs if v in available), None)
        if choice is None:
            choice = next(iter(available))
        cast[speaker] = choice
        used_characters.add(choice)

    for speaker in [s for s in speakers if info[s][0] == "narrator"]:
        prefs = voice_preferences(speaker, "narrator", None)
        choice = next((v for v in prefs if v in available and v not in used_characters), None)
        if choice is None:
            choice = next((v for v in prefs if v in available), None) or next(iter(available))
        cast[speaker] = choice

    character_speakers = [s for s in speakers if info[s][0] != "narrator"]
    if len(character_speakers) >= 2:
        voices = [cast[s] for s in character_speakers]
        if len(set(voices)) < min(len(character_speakers), len(pool)):
            for i, s in enumerate(character_speakers):
                cast[s] = pool[i % len(pool)]["voice"]
    return cast


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


async def build_episode(number: int, pool: list[dict], sem: asyncio.Semaphore):
    turns = source_turns(number)
    cast = build_episode_cast(turns, pool)
    work = TMP / f"a1-{number:03d}"
    work.mkdir(parents=True, exist_ok=True)
    tasks, sequence, roles, speakers, intents = [], [], [], [], []

    for idx, turn in enumerate(turns):
        role = turn["role"]
        profile = "dialogue" if number in MULTIVOICE_EPISODES else "clinical"
        p = prosody(turn["text"], profile=profile, role=role)
        rate, pitch, pause = p.rate, p.pitch, p.pause_ms
        if lexical_tokens(turn["text"]) == ["olá", "caros", "abordadores"]:
            rate, pitch, pause = "-1%", "+0Hz", 420
        if role == "person_in_crisis":
            rate_i = max(-14, int(rate.rstrip("%")) - 2)
            pitch_i = int(pitch.replace("Hz", ""))
            rate, pitch = f"{rate_i:+d}%", f"{pitch_i:+d}Hz"

        part = work / f"{idx:03d}.mp3"
        voice = cast[turn["speaker"]]
        tasks.append(synth(turn["text"], voice, rate, pitch, part, sem))
        sequence.append((part, 0 if idx == len(turns)-1 else pause))
        roles.append(role); speakers.append(turn["speaker"]); intents.append(p.intent)

    await asyncio.gather(*tasks)
    audio = AudioSegment.silent(duration=OPENING_SILENCE_MS)
    for part, pause in sequence:
        audio += AudioSegment.from_file(part, format="mp3")
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
    if number in MULTIVOICE_EPISODES and len(unique_voices) < 2:
        raise RuntimeError(f"A1-{number:03d} não ficou multivoz.")
    if len(non_narrators) >= 2:
        char_voices = [cast[s] for s in non_narrators]
        if len(set(char_voices)) < min(len(non_narrators), len(pool)):
            raise RuntimeError(f"A1-{number:03d}: personagens simultâneos sem diferenciação.")

    return {
        "episode": number, "output": target.name, "version": VERSION,
        "greeting": CANONICAL_GREETING,
        "profile": "N3-C-dialogue" if number in MULTIVOICE_EPISODES else "N3-C",
        "speakers": episode_speakers,
        "speaker_cast": {s: cast[s] for s in episode_speakers},
        "voices": unique_voices,
        "multivoice_required": number in MULTIVOICE_EPISODES,
        "pronunciation_dictionary": True,
        "intents": sorted(set(intents)), "turns": len(turns),
        "duration_seconds": round(len(audio)/1000, 1),
    }


def patch_app_urls():
    content = APP.read_text(encoding="utf-8")
    m = re.search(r"const AUDIOS=\{1:\[(.*?)\],2:\[", content, re.S)
    if not m:
        raise RuntimeError("Bloco Série 1 não localizado em app.js")
    block = m.group(1)
    entries = list(re.finditer(r'\{title:"([^"]+)",url:"([^"]+)"\}', block))
    if len(entries) != 21:
        raise RuntimeError(f"Esperados 21 episódios; encontrados {len(entries)}")
    new_block = block
    for idx, match in reversed(list(enumerate(entries, start=1))):
        title = match.group(1)
        repl = f'{{title:"{title}",url:"assets/audio/serie-1/a1-{idx:03d}-{VERSION_TAG}.mp3?v={VERSION}"}}'
        new_block = new_block[:match.start()] + repl + new_block[match.end():]
    content = content[:m.start(1)] + new_block + content[m.end(1):]
    APP.write_text(content, encoding="utf-8")


async def main():
    changed_sources = persist_canonical_greeting()
    TMP.mkdir(parents=True, exist_ok=True)
    pool = await resolve_operational_pool()
    print("[POOL]", json.dumps(pool, ensure_ascii=False))
    sem = asyncio.Semaphore(MAX_CONCURRENT_SYNTH)
    quality = []
    for number in range(1, 22):
        print(f"[A1-{number:03d}] render")
        quality.append(await build_episode(number, pool, sem))
    patch_app_urls()
    report = {
        "version": VERSION, "canonical_greeting": CANONICAL_GREETING,
        "source_files_rewritten": changed_sources,
        "operational_voice_pool": pool,
        "multivoice_episodes": sorted(MULTIVOICE_EPISODES),
        "episodes": quality,
    }
    (OUT / "quality-n3.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(TMP, ignore_errors=True)
    print("Série 1 N3 casting concluída.")


if __name__ == "__main__":
    asyncio.run(main())
