from __future__ import annotations

"""Remasterização perceptiva da Série 1 com fala orgânica e respirada.

Usa os roteiros congelados já existentes como fonte textual. Nenhuma palavra é
reescrita, resumida ou ampliada. A correção atua apenas em segmentação de fala,
cadência, prosódia, pausas e pós-processamento já validado no pipeline N2.
"""

import asyncio
import json
import re

import remaster_series1_n2 as base

# A Série 1 original ficou perceptivelmente mais rápida que as demais.
# O ajuste é deliberadamente moderado: mais espaço sem produzir fala arrastada.
base.BASE_RATE = {
    base.VOICE_INSTRUTOR: -8,
    base.VOICE_PROFISSIONAL: -5,
}
base.OPENING_SILENCE_MS = 180
base.ENDING_SILENCE_MS = 340
base.VERSION_TAG = "organic-v2"

MIN_BREATH_WORDS = 9
TARGET_BREATH_WORDS = 14
MAX_BREATH_WORDS = 19

SOFT_BREAK_BEFORE = {
    "mas", "porém", "porem", "contudo", "entretanto", "porque", "quando",
    "enquanto", "então", "entao", "assim", "agora", "portanto", "se",
    "como", "além", "alem", "ainda", "inclusive", "depois", "antes",
}

QUESTION_STARTS = (
    "o que ", "mas o que ", "como ", "por que ", "qual ", "quais ",
    "quem ", "onde ", "quando ", "será ", "sera ", "sabe o que ",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean_word(word: str) -> str:
    return re.sub(r"^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$", "", word.lower())


def _chunk_unpunctuated(text: str) -> list[str]:
    """Cria grupos de respiração sem mudar nenhuma palavra do roteiro."""
    words = text.split()
    if len(words) <= MAX_BREATH_WORDS:
        return [text]

    units: list[str] = []
    start = 0
    total = len(words)

    while total - start > MAX_BREATH_WORDS:
        low = start + MIN_BREATH_WORDS
        high = min(start + MAX_BREATH_WORDS, total)
        target = min(start + TARGET_BREATH_WORDS, high)

        candidates = []
        for idx in range(low, high):
            token = _clean_word(words[idx])
            if token in SOFT_BREAK_BEFORE:
                candidates.append(idx)

        if candidates:
            # Prefere o conector mais próximo da duração-alvo da respiração.
            cut = min(candidates, key=lambda idx: abs(idx - target))
        else:
            cut = target

        # Evita deixar cauda excessivamente curta no fim do trecho.
        if total - cut < 6:
            cut = max(low, total - 7)

        units.append(" ".join(words[start:cut]))
        start = cut

    if start < total:
        units.append(" ".join(words[start:]))

    return [unit for unit in units if unit]


def _breath_units(text: str) -> list[str]:
    """Respeita pontuação quando existe e cria respirações quando ela inexiste."""
    text = _normalize(text)
    if not text:
        return []

    sentences = [
        part.strip()
        for part in re.split(r"(?<=[.!?…])\s+", text)
        if part.strip()
    ]

    units: list[str] = []
    for sentence in sentences:
        words = sentence.split()
        if len(words) <= MAX_BREATH_WORDS:
            units.append(sentence)
            continue

        # Em textos pontuados, tenta primeiro limites de oração explícitos.
        clauses = [
            part.strip()
            for part in re.split(r"(?<=[;:,])\s+", sentence)
            if part.strip()
        ]
        if len(clauses) > 1:
            for clause in clauses:
                units.extend(_chunk_unpunctuated(clause))
        else:
            units.extend(_chunk_unpunctuated(sentence))

    return units


def _read_frozen_turns(number: int):
    """Lê o roteiro congelado e preserva o locutor previamente identificado."""
    path = base.ROTEIROS / f"a1-{number:03d}.txt"
    if not path.exists():
        raise RuntimeError(f"Roteiro congelado ausente: {path}")

    turns = []
    frozen_parts = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("PROFISSIONAL:"):
            voice = base.VOICE_PROFISSIONAL
            text = line.split(":", 1)[1].strip()
        elif line.startswith("INSTRUTOR:"):
            voice = base.VOICE_INSTRUTOR
            text = line.split(":", 1)[1].strip()
        else:
            # Compatibilidade defensiva para eventuais roteiros legados sem marcador.
            voice = base.VOICE_INSTRUTOR
            text = line

        if not text:
            continue
        frozen_parts.append(text)
        turns.extend((voice, unit) for unit in _breath_units(text))

    frozen = base.normalize_text(" ".join(frozen_parts))
    rebuilt = base.normalize_text(" ".join(text for _, text in turns))
    if not frozen or frozen != rebuilt:
        raise RuntimeError(
            f"Gate de integridade textual falhou no episódio {number:03d}."
        )
    return turns, frozen


def prosody_for(voice: str, text: str, turn_index: int):
    """Cadência variável mínima e pausas compatíveis com respiração humana."""
    rate = base.BASE_RATE[voice]
    pitch = base.BASE_PITCH[voice]
    normalized = text.strip().lower()
    stripped = text.rstrip()

    # Microvariação reduz sensação de metrônomo sem acelerar o discurso.
    rate += (-1, 0, 0, 1, 0, 0)[turn_index % 6]

    inferred_question = normalized.startswith(QUESTION_STARTS)
    if stripped.endswith("?") or inferred_question:
        rate -= 1
        pitch += 2
        pause_ms = 700
    elif stripped.endswith("…"):
        rate -= 2
        pause_ms = 820
    elif stripped.endswith("!"):
        pause_ms = 640
    elif stripped.endswith("."):
        pause_ms = 570
    elif stripped.endswith(":"):
        pause_ms = 450
    elif stripped.endswith(";"):
        pause_ms = 400
    elif stripped.endswith(","):
        pause_ms = 310
    else:
        # Caso predominante na Série 1: transcrição sem pontuação.
        pause_ms = 390

    if normalized.startswith((
        "guarde", "em resumo", "pense", "imagine", "o ponto", "observe",
        "lembre", "repare", "atenção", "atencao",
    )):
        rate -= 2
        pause_ms += 90

    rate = max(-13, min(0, rate))
    pitch = max(-4, min(4, pitch))
    return f"{rate:+d}%", f"{pitch:+d}Hz", pause_ms


base.prosody_for = prosody_for


async def main():
    """Ressintetiza os 21 episódios sem retranscrever os MP3s originais."""
    base.OUT.mkdir(parents=True, exist_ok=True)
    base.TMP.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(base.MAX_CONCURRENT_SYNTH)
    quality = []

    for number in range(1, 22):
        turns, frozen = _read_frozen_turns(number)
        target, seconds = await base.synth_episode(number, turns, semaphore)
        quality.append({
            "episode": number,
            "output": target.name,
            "text_integrity": 1.0,
            "frozen_characters": len(frozen),
            "turns": len(turns),
            "voices": sorted(set(voice for voice, _ in turns)),
            "duration_seconds": seconds,
            "audio_profile": "serie-1-organic-v2",
            "breath_pause_ms": 390,
            "base_rate": {
                "instrutor": base.BASE_RATE[base.VOICE_INSTRUTOR],
                "profissional": base.BASE_RATE[base.VOICE_PROFISSIONAL],
            },
        })
        print(
            f"[{number:03d}] orgânico | turnos={len(turns)} | "
            f"duração={seconds}s | {target.name}"
        )

    base.patch_app_urls()
    base.patch_index_cache()
    (base.OUT / "quality-organic-v2.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Série 1 concluída no perfil orgânico v2.")


if __name__ == "__main__":
    asyncio.run(main())
