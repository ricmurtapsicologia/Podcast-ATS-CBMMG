from __future__ import annotations

"""Remasteriza a Série 1 no mesmo perfil sonoro N2 da Série 3.

Princípios editoriais:
- o MP3 original continua sendo a fonte de verdade;
- a fala é transcrita sem reescrita, resumo ou ampliação;
- a transcrição congelada é exatamente o texto enviado ao sintetizador;
- episódios com evidência acústica consistente de dois interlocutores recebem duas vozes;
- episódios narrativos permanecem com uma voz, sem criação artificial de diálogo;
- ritmo, pitch, pausas, compressão e normalização espelham a Série 3;
- os novos arquivos têm nomes versionados para eliminar cache de versões antigas.
"""

import asyncio
import json
import re
from pathlib import Path

import edge_tts
import librosa
import numpy as np
from faster_whisper import WhisperModel
from pydub import AudioSegment, effects
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
ROTEIROS = ROOT / "roteiros" / "serie-1"
OUT = ROOT / "assets" / "audio" / "serie-1"
TMP = ROOT / ".tmp_serie1_n2"
APP = ROOT / "app.js"
INDEX = ROOT / "index.html"

VOICE_INSTRUTOR = "pt-BR-AntonioNeural"
VOICE_PROFISSIONAL = "pt-BR-FranciscaNeural"
BASE_RATE = {VOICE_INSTRUTOR: -4, VOICE_PROFISSIONAL: -1}
BASE_PITCH = {VOICE_INSTRUTOR: -1, VOICE_PROFISSIONAL: 1}

MODEL_NAME = "medium"
OPENING_SILENCE_MS = 130
ENDING_SILENCE_MS = 240
TARGET_DBFS = -18.0
MAX_CONCURRENT_SYNTH = 4
SYNTH_TIMEOUT_SECONDS = 45
MAX_TURN_CHARS = 560
VERSION_TAG = "s3n2"


def source_file(number: int) -> Path:
    matches = sorted(ROOT.glob(f"{number:03d}*.mp3*"))
    if len(matches) != 1:
        raise RuntimeError(f"Esperado 1 MP3 para {number:03d}; encontrados {len(matches)}: {matches}")
    return matches[0]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def transcribe(model: WhisperModel, audio: Path):
    segments, _ = model.transcribe(
        str(audio),
        language="pt",
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=True,
        word_timestamps=False,
        temperature=0.0,
    )
    rows = []
    for seg in segments:
        text = normalize_text(seg.text)
        if text:
            rows.append({
                "start": float(seg.start),
                "end": float(seg.end),
                "text": text,
            })
    if not rows:
        raise RuntimeError(f"Nenhuma fala reconhecida em {audio.name}")
    return rows


def audio_samples(audio: AudioSegment, start: float, end: float):
    clip = audio[int(start * 1000):int(end * 1000)].set_channels(1).set_frame_rate(16000)
    data = np.asarray(clip.get_array_of_samples(), dtype=np.float32)
    if not len(data):
        return np.zeros(0, dtype=np.float32)
    peak = float(1 << (8 * clip.sample_width - 1))
    return data / peak


def voice_feature(y: np.ndarray, sr: int = 16000):
    if len(y) < sr // 2:
        return None
    try:
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        zcr = librosa.feature.zero_crossing_rate(y)
        rms = librosa.feature.rms(y=y)
        f0 = librosa.yin(y, fmin=65, fmax=360, sr=sr)
        voiced = f0[np.isfinite(f0)]
        pitch = float(np.median(voiced)) if len(voiced) else 0.0
        feature = np.concatenate([
            np.mean(mfcc[1:9], axis=1),
            np.std(mfcc[1:6], axis=1),
            [float(np.mean(centroid)), float(np.mean(zcr)), float(np.mean(rms)), pitch],
        ])
        return feature.astype(np.float32), pitch
    except Exception:
        return None


def detect_speakers(source: Path, rows):
    """Detecta 1 ou 2 vozes a partir do próprio MP3 original.

    A decisão é deliberadamente conservadora. Só há duas vozes quando os agrupamentos
    acústicos têm separação consistente, participação mínima de ambos e diferença de pitch.
    """
    audio = AudioSegment.from_file(source)
    indexed = []
    features = []
    pitches = []
    durations = []

    for idx, row in enumerate(rows):
        if row["end"] - row["start"] < 0.75:
            continue
        feat = voice_feature(audio_samples(audio, row["start"], row["end"]))
        if feat is None:
            continue
        vector, pitch = feat
        indexed.append(idx)
        features.append(vector)
        pitches.append(pitch)
        durations.append(max(0.1, row["end"] - row["start"]))

    default = {
        "dialogue": False,
        "labels": [0] * len(rows),
        "silhouette": 0.0,
        "pitch_difference_hz": 0.0,
        "cluster_shares": [1.0, 0.0],
    }
    if len(features) < 6:
        return default

    X = StandardScaler().fit_transform(np.vstack(features))
    labels = KMeans(n_clusters=2, random_state=17, n_init=20).fit_predict(X)
    if len(set(labels)) < 2:
        return default

    sil = float(silhouette_score(X, labels))
    cluster_durations = []
    cluster_pitches = []
    for c in (0, 1):
        ds = [durations[i] for i, lab in enumerate(labels) if lab == c]
        ps = [pitches[i] for i, lab in enumerate(labels) if lab == c and pitches[i] > 0]
        cluster_durations.append(sum(ds))
        cluster_pitches.append(float(np.median(ps)) if ps else 0.0)

    total = sum(cluster_durations) or 1.0
    shares = [d / total for d in cluster_durations]
    pitch_diff = abs(cluster_pitches[0] - cluster_pitches[1])
    counts = [int(np.sum(labels == c)) for c in (0, 1)]

    dialogue = (
        sil >= 0.24
        and min(shares) >= 0.10
        and min(counts) >= 2
        and pitch_diff >= 18.0
    )
    if not dialogue:
        return {
            **default,
            "silhouette": round(sil, 3),
            "pitch_difference_hz": round(pitch_diff, 1),
            "cluster_shares": [round(x, 3) for x in shares],
        }

    row_labels = [None] * len(rows)
    for idx, lab in zip(indexed, labels):
        row_labels[idx] = int(lab)

    # Preenche segmentos curtos/indeterminados pela vizinhança mais próxima.
    last = 0
    for i in range(len(row_labels)):
        if row_labels[i] is None:
            row_labels[i] = last
        else:
            last = row_labels[i]
    last = row_labels[-1]
    for i in range(len(row_labels) - 1, -1, -1):
        if row_labels[i] is None:
            row_labels[i] = last
        else:
            last = row_labels[i]

    # Suaviza um único segmento isolado entre dois segmentos do mesmo locutor.
    for i in range(1, len(row_labels) - 1):
        if row_labels[i - 1] == row_labels[i + 1] != row_labels[i]:
            row_labels[i] = row_labels[i - 1]

    # Cluster com pitch mais alto recebe a voz Francisca; o outro, Antonio.
    high_cluster = int(np.argmax(cluster_pitches))
    mapped = [1 if lab == high_cluster else 0 for lab in row_labels]
    return {
        "dialogue": True,
        "labels": mapped,
        "silhouette": round(sil, 3),
        "pitch_difference_hz": round(pitch_diff, 1),
        "cluster_shares": [round(x, 3) for x in shares],
    }


def build_turns(rows, speaker_info):
    turns = []
    current_voice = None
    current_text = []
    current_len = 0

    for idx, row in enumerate(rows):
        voice = VOICE_PROFISSIONAL if speaker_info["dialogue"] and speaker_info["labels"][idx] == 1 else VOICE_INSTRUTOR
        text = row["text"]
        projected = current_len + (1 if current_text else 0) + len(text)
        if current_text and (voice != current_voice or projected > MAX_TURN_CHARS):
            turns.append((current_voice, " ".join(current_text)))
            current_text = []
            current_len = 0
        current_voice = voice
        current_text.append(text)
        current_len += (1 if current_len else 0) + len(text)

    if current_text:
        turns.append((current_voice, " ".join(current_text)))

    frozen = normalize_text(" ".join(row["text"] for row in rows))
    rebuilt = normalize_text(" ".join(text for _, text in turns))
    if frozen != rebuilt:
        raise RuntimeError("Gate de integridade textual falhou ao organizar os turnos da Série 1.")
    return turns, frozen


def freeze_transcript(number: int, source: Path, rows, turns, speaker_info):
    ROTEIROS.mkdir(parents=True, exist_ok=True)
    target = ROTEIROS / f"a1-{number:03d}.txt"
    body = [
        f"# Série 1 — Episódio {number:03d}",
        f"# Fonte: {source.name}",
        "# Transcrição automática congelada do MP3 original; não houve reescrita editorial.",
        f"# Modo: {'duas vozes' if speaker_info['dialogue'] else 'narração única'}",
        "",
    ]
    for voice, text in turns:
        label = "PROFISSIONAL" if voice == VOICE_PROFISSIONAL else "INSTRUTOR"
        body.append(f"{label}: {text}")
    target.write_text("\n".join(body) + "\n", encoding="utf-8")


def prosody_for(voice: str, text: str, turn_index: int):
    # Mesma função perceptiva da Série 3.
    rate = BASE_RATE[voice]
    pitch = BASE_PITCH[voice]
    normalized = text.strip().lower()

    if text.rstrip().endswith("?"):
        rate += 2
        pitch += 2
    if normalized.startswith(("guarde", "em resumo", "pense", "imagine", "o ponto")):
        rate -= 2
    rate += (-1, 0, 1, 0)[turn_index % 4]

    if text.rstrip().endswith("?"):
        pause_ms = 560
    elif text.rstrip().endswith("!"):
        pause_ms = 500
    else:
        pause_ms = 520

    rate = max(-10, min(4, rate))
    pitch = max(-4, min(4, pitch))
    return f"{rate:+d}%", f"{pitch:+d}Hz", pause_ms


async def synthesize(text: str, voice: str, rate: str, pitch: str, output: Path, semaphore: asyncio.Semaphore):
    async with semaphore:
        for attempt in range(1, 4):
            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                    volume="+0%",
                )
                await asyncio.wait_for(communicate.save(str(output)), timeout=SYNTH_TIMEOUT_SECONDS)
                return
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(0.8 * attempt)


async def synth_episode(number: int, turns, semaphore: asyncio.Semaphore):
    work = TMP / f"a1-{number:03d}"
    work.mkdir(parents=True, exist_ok=True)
    tasks = []
    sequence = []

    for idx, (voice, text) in enumerate(turns):
        rate, pitch, pause_ms = prosody_for(voice, text, idx)
        part = work / f"{idx:03d}.mp3"
        sequence.append((part, 0 if idx == len(turns) - 1 else pause_ms))
        tasks.append(synthesize(text, voice, rate, pitch, part, semaphore))

    await asyncio.gather(*tasks)

    merged = AudioSegment.silent(duration=OPENING_SILENCE_MS)
    for part, pause_ms in sequence:
        merged += AudioSegment.from_file(part, format="mp3")
        if pause_ms:
            merged += AudioSegment.silent(duration=pause_ms)
    merged += AudioSegment.silent(duration=ENDING_SILENCE_MS)

    merged = effects.compress_dynamic_range(
        merged,
        threshold=-20.0,
        ratio=2.0,
        attack=8.0,
        release=70.0,
    )
    if merged.dBFS != float("-inf"):
        merged = merged.apply_gain(TARGET_DBFS - merged.dBFS)
    if merged.max_dBFS > -1.2:
        merged = merged.apply_gain(-1.2 - merged.max_dBFS)

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"a1-{number:03d}-{VERSION_TAG}.mp3"
    merged.export(target, format="mp3", bitrate="128k", parameters=["-ac", "1", "-ar", "44100"])
    return target, round(len(merged) / 1000, 1)


def patch_app_urls():
    content = APP.read_text(encoding="utf-8")
    block_match = re.search(r"const AUDIOS=\{1:\[(.*?)\],2:\[", content, re.S)
    if not block_match:
        raise RuntimeError("Bloco da Série 1 não localizado em app.js")
    block = block_match.group(1)
    entries = list(re.finditer(r'\{title:"([^"]+)",url:"([^"]+)"\}', block))
    if len(entries) != 21:
        raise RuntimeError(f"Esperados 21 episódios na Série 1; encontrados {len(entries)}")

    new_block = block
    for idx, match in reversed(list(enumerate(entries, start=1))):
        title = match.group(1)
        replacement = f'{{title:"{title}",url:"assets/audio/serie-1/a1-{idx:03d}-{VERSION_TAG}.mp3"}}'
        new_block = new_block[:match.start()] + replacement + new_block[match.end():]

    content = content[:block_match.start(1)] + new_block + content[block_match.end(1):]
    APP.write_text(content, encoding="utf-8")


def patch_index_cache():
    content = INDEX.read_text(encoding="utf-8")
    content = re.sub(r'app\.js(?:\?v=[^"\']+)?', f'app.js?v=20260808-s1-{VERSION_TAG}', content, count=1)
    INDEX.write_text(content, encoding="utf-8")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ROTEIROS.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)

    print(f"Carregando Whisper {MODEL_NAME} em CPU/int8...")
    model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SYNTH)
    quality = []

    for number in range(1, 22):
        source = source_file(number)
        print(f"[{number:03d}] transcrevendo {source.name}")
        rows = transcribe(model, source)
        speaker_info = detect_speakers(source, rows)
        turns, frozen = build_turns(rows, speaker_info)
        freeze_transcript(number, source, rows, turns, speaker_info)
        print(
            f"[{number:03d}] {'duas vozes' if speaker_info['dialogue'] else 'uma voz'} | "
            f"turnos={len(turns)} | sil={speaker_info['silhouette']} | "
            f"pitchΔ={speaker_info['pitch_difference_hz']}Hz"
        )
        target, seconds = await synth_episode(number, turns, semaphore)
        quality.append({
            "episode": number,
            "source": source.name,
            "output": target.name,
            "text_integrity": 1.0,
            "frozen_characters": len(frozen),
            "turns": len(turns),
            "dialogue_detected": speaker_info["dialogue"],
            "voices": sorted(set(voice for voice, _ in turns)),
            "silhouette": speaker_info["silhouette"],
            "pitch_difference_hz": speaker_info["pitch_difference_hz"],
            "cluster_shares": speaker_info["cluster_shares"],
            "duration_seconds": seconds,
            "audio_profile": "serie-3-n2",
        })

    patch_app_urls()
    patch_index_cache()
    (OUT / "quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Série 1 concluída no padrão N2 da Série 3.")


if __name__ == "__main__":
    asyncio.run(main())
