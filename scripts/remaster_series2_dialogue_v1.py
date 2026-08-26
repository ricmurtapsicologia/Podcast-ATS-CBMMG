from __future__ import annotations

"""Remasterização multivoz dos episódios dialogados A2 004–009.

Contrato:
- MP3 original e roteiro congelado permanecem fontes de verdade;
- nenhum conteúdo é reescrito, resumido ou ampliado;
- a atribuição de locutor é editorialmente explícita e determinística;
- cada personagem usa uma voz PT-BR distinta e estável;
- A2 007 e A2 008 compartilham a mesma identidade vocal de entrevistador;
- os novos arquivos são versionados e os anteriores permanecem para rollback;
- app.js só é alterado se todos os seis episódios passarem os gates automáticos.
"""

import asyncio
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import edge_tts
from pydub import AudioSegment, effects

ROOT = Path(__file__).resolve().parents[1]
ROTEIROS = ROOT / "roteiros" / "serie-2"
OUT = ROOT / "assets" / "audio" / "serie-2"
TMP = ROOT / ".tmp_a2_dialogue_v1"
APP = ROOT / "app.js"

VERSION_TAG = "dialogue-v1"
TARGET_EPISODES = (4, 5, 6, 7, 8, 9)
OPENING_SILENCE_MS = 190
ENDING_SILENCE_MS = 420
TARGET_LUFS = -18.0
TRUE_PEAK_TARGET = -1.5
MAX_CONCURRENT_SYNTH = 4
SYNTH_TIMEOUT_SECONDS = 60

SOURCE_FILES = {
    4: "A2 004 Maria e as sombras da depressao.mp3",
    5: "A2 005 Cláudio e os Ciclos do TAB.mp3",
    6: "A2 006 Fernanda na Rede da Dependência.mp3",
    7: "A2 007 Entrevista com Júlia.mp3",
    8: "A2 008 Entrevista com Dra Sara.mp3",
    9: "A2 009 Dona Lurdes e sua irmã.mp3",
}


@dataclass(frozen=True)
class VoiceProfile:
    voice_id: str
    base_rate: int
    base_pitch: int
    energy: str
    style: str


VOICE_PROFILES: dict[str, VoiceProfile] = {
    "NARRADOR": VoiceProfile("pt-BR-AntonioNeural", -6, -1, "low", "neutral-discreet"),
    "MARIA": VoiceProfile("pt-BR-ThalitaNeural", -7, 0, "low", "young-introspective"),
    "GORETTE": VoiceProfile("pt-BR-FranciscaNeural", -4, 0, "medium", "mature-warm-firm"),
    "CLAUDIO": VoiceProfile("pt-BR-DonatoNeural", 0, 1, "high", "activated-but-controlled"),
    "ANA": VoiceProfile("pt-BR-FranciscaNeural", -4, 0, "medium", "stable-regulating"),
    "GUILHERME": VoiceProfile("pt-BR-DonatoNeural", -6, -1, "low", "calm-secure-non-authoritarian"),
    "FERNANDA": VoiceProfile("pt-BR-ThalitaNeural", -2, 1, "variable", "tense-to-regulated"),
    "ENTREVISTADOR": VoiceProfile("pt-BR-AntonioNeural", -4, -1, "medium", "professional-interested"),
    "JULIA": VoiceProfile("pt-BR-ThalitaNeural", -5, 0, "medium-low", "young-reflective"),
    "SARA": VoiceProfile("pt-BR-FranciscaNeural", -3, 0, "medium", "clinical-clear-warm"),
    "LOURDES": VoiceProfile("pt-BR-FranciscaNeural", -4, 0, "medium-low", "mature-caregiver"),
    "FATIMA": VoiceProfile("pt-BR-ThalitaNeural", -3, 0, "medium", "mature-conversational"),
}

EPISODE_SPEAKERS = {
    4: ("NARRADOR", "MARIA", "GORETTE"),
    5: ("NARRADOR", "CLAUDIO", "ANA"),
    6: ("NARRADOR", "GUILHERME", "FERNANDA"),
    7: ("ENTREVISTADOR", "JULIA"),
    8: ("ENTREVISTADOR", "SARA"),
    9: ("NARRADOR", "LOURDES", "FATIMA"),
}

# Cada marcador inicia um novo turno e é procurado sequencialmente.
# O gate de integridade recompõe o texto integral do roteiro congelado.
TURN_STARTS: dict[int, list[tuple[str, str]]] = {
    4: [
        ("NARRADOR", "Maria e sua mãe Gorette conversa sobre o transtorno depressivo maior."),
        ("GORETTE", "Maria, você está aqui nesse canto a horas?"),
        ("NARRADOR", "Maria responde,"),
        ("MARIA", "não, mãe, não consegui."),
        ("NARRADOR", "Gorette diz,"),
        ("GORETTE", "minha filha, eu percebo que você anda muito desanimada ultimamente,"),
        ("NARRADOR", "Maria explica,"),
        ("MARIA", "é difícil explicar, não é só tristeza,"),
        ("NARRADOR", "Gorette tenta consolar,"),
        ("GORETTE", "mas Maria, você sempre foi tão esforçada,"),
        ("NARRADOR", "Maria confessa,"),
        ("MARIA", "é isso que me machuca mais, mãe,"),
        ("NARRADOR", "Gorette pergunta preocupada,"),
        ("GORETTE", "e o sono, você tem conseguido dormir direito?"),
        ("NARRADOR", "Maria responde,"),
        ("MARIA", "não, tem noites que ficam rolando na cama"),
        ("NARRADOR", "Gorette continua,"),
        ("GORETTE", "e você tem sentido fome?"),
        ("NARRADOR", "Maria explica,"),
        ("MARIA", "não sinto vontade de comer."),
        ("NARRADOR", "Gorette diz com preocupação,"),
        ("GORETTE", "Maria, isso está me preocupando."),
        ("NARRADOR", "Maria responde exitante,"),
        ("MARIA", "já pensei, mas fico com medo de não melhorar,"),
        ("NARRADOR", "Gorette se aproxima e segura as mãos de Maria dizendo com firmeza."),
        ("GORETTE", "Minha filha, você não está sozinha."),
        ("NARRADOR", "Maria emocionada responde."),
        ("MARIA", "Obrigada, mãe."),
        ("NARRADOR", "Maria demonstra sintomas característicos"),
    ],
    5: [
        ("NARRADOR", "Cláudio enfermeiro com transtorno afetivo bipolar tipo 1,"),
        ("CLAUDIO", "vocês precisam vir dançar comigo,"),
        ("NARRADOR", "enquanto falava, Cláudio de repente se aproxima"),
        ("CLAUDIO", "Você é a pessoa mais bonita que já vi,"),
        ("NARRADOR", "A mulher surpresa rissa em jeito,"),
        ("ANA", "Cláudio, você está falando rápido demais"),
        ("NARRADOR", "Cláudio ri, mas sua energia não diminui."),
        ("CLAUDIO", "Ana, você está me chamando de distraído?"),
        ("NARRADOR", "Mas tarde, ao tentar se desculpar"),
        ("CLAUDIO", "Mas sabe, às vezes, depois de noites assim,"),
        ("NARRADOR", "Cláudio exibe sintomas claros"),
    ],
    6: [
        ("NARRADOR", "Fernanda, uma dependente química de cocaína em crise suicida."),
        ("GUILHERME", "Oi, eu sou Guilherme, bombeiro militar."),
        ("FERNANDA", "Fernanda. Mas isso não importa."),
        ("GUILHERME", "Importa, sim, Fernanda."),
        ("FERNANDA", "Eu não sei. Minha vida está uma bagunça."),
        ("GUILHERME", "Entendo que você se sinta assim?"),
        ("FERNANDA", "Sim, mas ela está cansada."),
        ("GUILHERME", "Parece que você está carregando muita culpa, Fernanda."),
        ("FERNANDA", "Desde que comecei com essa porcaria, cocaína,"),
        ("GUILHERME", "Isso deve ser muito difícil."),
        ("FERNANDA", "Sim, usei muito."),
        ("GUILHERME", "Fernanda, antes de tudo isso, você trabalhava."),
        ("FERNANDA", "Trabalhava num salão de beleza,"),
        ("GUILHERME", "E antes de começar a usar a droga,"),
        ("FERNANDA", "Eu gostava de ouvir música,"),
        ("GUILHERME", "Sua mãe ainda se preocupa com você, não é?"),
        ("FERNANDA", "Ela diz que sim,"),
        ("GUILHERME", "Eu entendo que você esteja se sentindo sobrecarregada agora, Fernanda."),
        ("NARRADOR", "Nesse diálogo, Fernanda mostra os impactos"),
    ],
    7: [
        ("ENTREVISTADOR", "Programa em foco saúde mental, o tema de hoje, transtornos de personalidade."),
        ("JULIA", "Eu que agradeço."),
        ("ENTREVISTADOR", "Vamos começar com sua história."),
        ("JULIA", "Desde adolescência, eu já sentia"),
        ("ENTREVISTADOR", "E foi nesse período que você começou a buscar ajuda profissional?"),
        ("JULIA", "Não imediatamente."),
        ("ENTREVISTADOR", "E como esse diagnóstico impactou sua vida?"),
        ("JULIA", "De certa forma, foi um alívio."),
        ("ENTREVISTADOR", "Como o transtorno afetava seu dia a dia?"),
        ("JULIA", "Impactava tudo."),
        ("ENTREVISTADOR", "Hoje você busca tratamento."),
        ("JULIA", "No início, foi difícil aceitar"),
        ("ENTREVISTADOR", "Julia, sua história é muito importante"),
    ],
    8: [
        ("ENTREVISTADOR", "Programa Infoco Saúde Mental bloco 2 entrevista"),
        ("SARA", "Eu que agradeço."),
        ("ENTREVISTADOR", "O que são exatamente os transtornos de personalidade."),
        ("SARA", "São padrões duradouros e inflexíveis"),
        ("ENTREVISTADOR", "Como eles influenciam as decisões do dia a dia?"),
        ("SARA", "Por exemplo, por exemplo,"),
        ("ENTREVISTADOR", "E qual a relação dos transtornos de personalidade com o comportamento suicida?"),
        ("SARA", "Dratarsara. É uma relação preocupante."),
        ("ENTREVISTADOR", "Pode explicar os diferentes tipos de transtornos de personalidade?"),
        ("SARA", "Sara, claro."),
        ("ENTREVISTADOR", "E como é o tratamento?"),
        ("SARA", "A parsara, a base é a psicoterapia,"),
        ("ENTREVISTADOR", "Entrevistador, do Corsara, obrigada"),
    ],
    9: [
        ("NARRADOR", "Dona Lourdes e sua irmã conversam?"),
        ("FATIMA", "Lourdes, você parece um pouco mais tranquila hoje."),
        ("LOURDES", "Ah, Fatima está mais estável com o novo tratamento,"),
        ("FATIMA", "Ela ainda ouve vozes?"),
        ("LOURDES", "Sim, às vezes."),
        ("FATIMA", "Fatima, ela já falou sobre pensamentos ruins?"),
        ("LOURDES", "Já. Durante as crises."),
        ("FATIMA", "Fatima, como você reage nesses momentos?"),
        ("LOURDES", "Eu respiro fundo e tento manter a calma."),
        ("FATIMA", "E você está cuidando de si mesma?"),
        ("LOURDES", "Estou tentando, Fatima."),
        ("FATIMA", "E ela ainda tem sonhos?"),
        ("LOURDES", "Sim, quer voltar a estudar"),
        ("NARRADOR", "Essa foi a conversa entre Dona Lourdes e Fatima."),
    ],
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def read_frozen_text(number: int) -> str:
    path = ROTEIROS / f"a2-{number:03d}.txt"
    if not path.exists():
        raise RuntimeError(f"Roteiro congelado ausente: {path}")
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("#")]
    text = normalize_text(" ".join(lines))
    if not text:
        raise RuntimeError(f"Roteiro vazio: {path}")
    return text


def build_explicit_turns(number: int, text: str) -> list[tuple[str, str]]:
    specs = TURN_STARTS[number]
    found: list[tuple[str, int]] = []
    cursor = 0
    for idx, (speaker, marker) in enumerate(specs):
        pos = text.find(marker, cursor)
        if pos < 0:
            raise RuntimeError(f"A2 {number:03d}: marcador ausente para {speaker}: {marker!r}")
        if idx == 0 and pos != 0:
            raise RuntimeError(f"A2 {number:03d}: primeiro marcador não inicia o roteiro.")
        found.append((speaker, pos))
        cursor = pos + len(marker)

    turns: list[tuple[str, str]] = []
    for idx, (speaker, pos) in enumerate(found):
        end = found[idx + 1][1] if idx + 1 < len(found) else len(text)
        chunk = text[pos:end].strip()
        if not chunk:
            raise RuntimeError(f"A2 {number:03d}: turno vazio para {speaker}.")
        turns.append((speaker, chunk))

    rebuilt = normalize_text(" ".join(chunk for _, chunk in turns))
    if rebuilt != normalize_text(text):
        raise RuntimeError(f"A2 {number:03d}: gate de integridade textual falhou.")
    return turns


async def verify_voice_catalog() -> None:
    catalog = await edge_tts.list_voices()
    available = {item["ShortName"] for item in catalog}
    required = {VOICE_PROFILES[s].voice_id for speakers in EPISODE_SPEAKERS.values() for s in speakers}
    missing = sorted(required - available)
    if missing:
        raise RuntimeError(f"Vozes PT-BR indisponíveis no catálogo Edge TTS: {missing}")


def prosody_for(number: int, speaker: str, text: str, turn_index: int, total_turns: int) -> tuple[str, str]:
    p = VOICE_PROFILES[speaker]
    rate = p.base_rate
    pitch = p.base_pitch
    progress = turn_index / max(1, total_turns - 1)
    lower = text.lower()

    rate += (-1, 0, 1, 0)[turn_index % 4]

    if speaker == "CLAUDIO":
        rate += 2 if progress < 0.70 else -3
        if "mas sabe, às vezes" in lower:
            rate -= 3
            pitch -= 1
    elif speaker == "FERNANDA":
        if progress < 0.35:
            rate += 2
        elif progress > 0.72:
            rate -= 2
    elif speaker == "GUILHERME":
        rate -= 1
    elif speaker == "MARIA":
        if any(k in lower for k in ("não estar aqui", "não consigo", "vazio", "inútil")):
            rate -= 1
    elif speaker == "GORETTE":
        if "você não está sozinha" in lower:
            rate -= 1
    elif speaker == "SARA":
        if len(text) > 300:
            rate -= 1

    if text.rstrip().endswith("?"):
        pitch += 1
        rate += 1

    rate = max(-10, min(4, rate))
    pitch = max(-3, min(3, pitch))
    return f"{rate:+d}%", f"{pitch:+d}Hz"


def pause_after(number: int, speaker: str, text: str, next_speaker: str | None) -> int:
    lower = text.lower()
    if next_speaker is None:
        return 0
    if next_speaker == speaker:
        return 260

    if speaker in {"NARRADOR", "ENTREVISTADOR"} and next_speaker not in {"NARRADOR", "ENTREVISTADOR"}:
        base = 560
    elif next_speaker == "NARRADOR":
        base = 900
    else:
        base = 390

    if text.rstrip().endswith("?"):
        base += 100
    if any(k in lower for k in ("não estar aqui", "queria desaparecer", "não está sozinha", "pensamentos ruins")):
        base = max(base, 720)
    if number == 6 and speaker == "FERNANDA" and "queria desaparecer" in lower:
        base = 820
    return min(1100, base)


async def synthesize(text: str, profile: VoiceProfile, rate: str, pitch: str, output: Path, semaphore: asyncio.Semaphore) -> None:
    async with semaphore:
        for attempt in range(1, 4):
            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=profile.voice_id,
                    rate=rate,
                    pitch=pitch,
                    volume="+0%",
                )
                await asyncio.wait_for(communicate.save(str(output)), timeout=SYNTH_TIMEOUT_SECONDS)
                if not output.exists() or output.stat().st_size < 1024:
                    raise RuntimeError(f"Segmento TTS inválido: {output}")
                return
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(1.0 * attempt)


def ffprobe_duration(path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        text=True,
        capture_output=True,
    )
    return float(proc.stdout.strip())


def loudnorm_master(wav_path: Path, target: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(wav_path),
            "-af", f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK_TARGET}:LRA=11",
            "-ar", "44100", "-ac", "1", "-b:a", "128k",
            str(target),
        ],
        check=True,
    )


def loudness_metrics(path: Path) -> tuple[float, float]:
    proc = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-i", str(path),
            "-af", f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK_TARGET}:LRA=11:print_format=json",
            "-f", "null", "-",
        ],
        text=True,
        capture_output=True,
    )
    matches = re.findall(r'\{\s*"input_i".*?\}', proc.stderr, flags=re.S)
    if not matches:
        raise RuntimeError(f"Não foi possível medir LUFS/true peak de {path.name}")
    data = json.loads(matches[-1])
    return float(data["input_i"]), float(data["input_tp"])


def patch_app_urls() -> None:
    content = APP.read_text(encoding="utf-8")
    for number in TARGET_EPISODES:
        pattern = rf'(assets/audio/serie-2/a2-{number:03d}-)[^"]+(\.mp3)'
        replacement = rf'\1{VERSION_TAG}\2'
        content, count = re.subn(pattern, replacement, content, count=1)
        if count != 1:
            raise RuntimeError(f"URL do A2 {number:03d} não localizada exatamente uma vez em app.js")
    APP.write_text(content, encoding="utf-8")


async def build_episode(number: int, semaphore: asyncio.Semaphore) -> dict:
    frozen = read_frozen_text(number)
    turns = build_explicit_turns(number, frozen)
    source = ROOT / SOURCE_FILES[number]
    if not source.exists():
        raise RuntimeError(f"MP3-fonte ausente: {source.name}")

    work = TMP / f"a2-{number:03d}"
    work.mkdir(parents=True, exist_ok=True)
    tasks = []
    sequence: list[tuple[Path, int, str, str]] = []
    total_turns = len(turns)

    for idx, (speaker, text) in enumerate(turns):
        profile = VOICE_PROFILES[speaker]
        rate, pitch = prosody_for(number, speaker, text, idx, total_turns)
        part = work / f"{idx:03d}-{speaker.lower()}.mp3"
        next_speaker = turns[idx + 1][0] if idx + 1 < total_turns else None
        pause_ms = pause_after(number, speaker, text, next_speaker)
        tasks.append(synthesize(text, profile, rate, pitch, part, semaphore))
        sequence.append((part, pause_ms, speaker, text))

    await asyncio.gather(*tasks)

    merged = AudioSegment.silent(duration=OPENING_SILENCE_MS)
    segment_durations = []
    for part, pause_ms, speaker, text in sequence:
        audio = AudioSegment.from_file(part, format="mp3")
        if len(audio) < 250:
            raise RuntimeError(f"A2 {number:03d}: segmento anormalmente curto ({speaker}).")
        audio = audio.fade_in(6).fade_out(10)
        segment_durations.append(round(len(audio) / 1000, 3))
        merged += audio
        if pause_ms:
            merged += AudioSegment.silent(duration=pause_ms)
    merged += AudioSegment.silent(duration=ENDING_SILENCE_MS)

    merged = merged.high_pass_filter(70).low_pass_filter(14500)
    merged = effects.compress_dynamic_range(
        merged,
        threshold=-20.0,
        ratio=2.0,
        attack=8.0,
        release=75.0,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    pre_master = work / "premaster.wav"
    target = OUT / f"a2-{number:03d}-{VERSION_TAG}.mp3"
    merged.export(pre_master, format="wav")
    loudnorm_master(pre_master, target)

    final = AudioSegment.from_file(target, format="mp3")
    loudness_lufs, true_peak_db = loudness_metrics(target)
    sample_peak_dbfs = float(final.max_dBFS)
    source_duration = ffprobe_duration(source)
    final_duration = ffprobe_duration(target)

    speakers = EPISODE_SPEAKERS[number]
    voice_map = {speaker: VOICE_PROFILES[speaker].voice_id for speaker in speakers}
    distinct_voices = len(set(voice_map.values()))
    required_distinct = 2 if number in (7, 8) else 3

    gates = {
        "text_integrity": normalize_text(" ".join(t for _, t in turns)) == frozen,
        "explicit_speaker_map": set(s for s, _ in turns).issubset(set(speakers)),
        "voice_consistency": all(voice_map[s] == VOICE_PROFILES[s].voice_id for s in speakers),
        "distinct_voice_models": distinct_voices >= required_distinct,
        "duration_valid": final_duration >= 30.0 and all(d >= 0.25 for d in segment_durations),
        "loudness_valid": -19.5 <= loudness_lufs <= -16.5,
        "peak_valid": true_peak_db <= -0.5 and sample_peak_dbfs <= -0.5,
        "no_clipping": sample_peak_dbfs < -0.1,
    }
    status = "PASS" if all(gates.values()) else "FAIL"

    return {
        "episode": number,
        "source": source.name,
        "output": target.name,
        "characters": list(speakers),
        "voice_ids": voice_map,
        "turns": len(turns),
        "source_duration_seconds": round(source_duration, 2),
        "final_duration_seconds": round(final_duration, 2),
        "text_integrity": 1.0 if gates["text_integrity"] else 0.0,
        "documented_transcription_corrections": 0,
        "loudness_lufs": round(loudness_lufs, 2),
        "true_peak_db": round(true_peak_db, 2),
        "sample_peak_dbfs": round(sample_peak_dbfs, 2),
        "clipping": not gates["no_clipping"],
        "segment_durations_seconds": segment_durations,
        "gates": gates,
        "status": status,
    }


async def main() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    await verify_voice_catalog()

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SYNTH)
    results = []
    for number in TARGET_EPISODES:
        print(f"[A2 {number:03d}] remasterização multivoz {VERSION_TAG}")
        results.append(await build_episode(number, semaphore))

    all_pass = all(row["status"] == "PASS" for row in results)

    report = {
        "profile": "A2 dialogue organic multivoice v1",
        "target_episodes": list(TARGET_EPISODES),
        "all_automated_gates_pass": all_pass,
        "perceptual_review": {
            "status": "REQUIRED_BEFORE_MAIN_MERGE",
            "samples": "Ouvir abertura, trecho central com alternância e fechamento de cada episódio.",
        },
        "episodes": results,
    }
    (OUT / "qa-dialogue-v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUT / "cast-dialogue-v1.json").write_text(
        json.dumps(
            {
                speaker: asdict(profile)
                for speaker, profile in VOICE_PROFILES.items()
                if any(speaker in EPISODE_SPEAKERS[n] for n in TARGET_EPISODES)
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    if not all_pass:
        failed = [row["episode"] for row in results if row["status"] != "PASS"]
        raise RuntimeError(f"Gates automáticos falharam: {failed}")

    patch_app_urls()
    print("A2 004–009: seis episódios passaram nos gates automáticos; app.js atualizado na branch de revisão.")


if __name__ == "__main__":
    asyncio.run(main())
