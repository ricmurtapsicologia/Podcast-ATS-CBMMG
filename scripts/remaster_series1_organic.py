from __future__ import annotations

"""Ajuste perceptivo da Série 1 para fala mais orgânica e respirada.

Reaproveita integralmente o pipeline validado de remasterização da Série 1,
sem alterar conteúdo textual, detecção de interlocutores ou pós-processamento.
A mudança é restrita à segmentação, cadência e pausas entre unidades de fala.
"""

import asyncio
import re

import remaster_series1_n2 as base

# Perfil perceptivo: discretamente mais lento que o N2 original, sem arrastar.
base.BASE_RATE = {
    base.VOICE_INSTRUTOR: -7,
    base.VOICE_PROFISSIONAL: -4,
}
base.OPENING_SILENCE_MS = 180
base.ENDING_SILENCE_MS = 320
base.VERSION_TAG = "organic-v1"

MAX_UNIT_CHARS = 300


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _sentence_units(text: str) -> list[str]:
    """Quebra em frases reais; só subdivide frases longas em limites de oração."""
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
        if len(sentence) <= MAX_UNIT_CHARS:
            units.append(sentence)
            continue

        # Primeiro tenta preservar unidades semânticas fortes.
        clauses = [
            part.strip()
            for part in re.split(r"(?<=[;:])\s+", sentence)
            if part.strip()
        ]
        if len(clauses) == 1:
            clauses = [
                part.strip()
                for part in re.split(r"(?<=,)\s+", sentence)
                if part.strip()
            ]

        current: list[str] = []
        current_len = 0
        for clause in clauses:
            projected = current_len + (1 if current else 0) + len(clause)
            if current and projected > MAX_UNIT_CHARS:
                units.append(" ".join(current))
                current = [clause]
                current_len = len(clause)
            else:
                current.append(clause)
                current_len = projected
        if current:
            units.append(" ".join(current))

    return units


def build_turns(rows, speaker_info):
    """Cria uma unidade sintetizada por frase, mantendo locutor e integridade textual."""
    turns = []

    for idx, row in enumerate(rows):
        voice = (
            base.VOICE_PROFISSIONAL
            if speaker_info["dialogue"] and speaker_info["labels"][idx] == 1
            else base.VOICE_INSTRUTOR
        )
        units = _sentence_units(row["text"])
        if not units:
            continue
        turns.extend((voice, unit) for unit in units)

    frozen = base.normalize_text(" ".join(row["text"] for row in rows))
    rebuilt = base.normalize_text(" ".join(text for _, text in turns))
    if frozen != rebuilt:
        raise RuntimeError(
            "Gate de integridade textual falhou ao organizar a Série 1 no perfil orgânico."
        )
    return turns, frozen


def prosody_for(voice: str, text: str, turn_index: int):
    """Prosódia com variação mínima e pausas perceptíveis entre frases."""
    rate = base.BASE_RATE[voice]
    pitch = base.BASE_PITCH[voice]
    normalized = text.strip().lower()
    stripped = text.rstrip()

    # Variação pequena evita cadência robótica sem criar aceleração perceptível.
    rate += (-1, 0, 0, 1, 0)[turn_index % 5]

    if stripped.endswith("?"):
        rate -= 1
        pitch += 2
        pause_ms = 720
    elif stripped.endswith("…"):
        rate -= 2
        pause_ms = 820
    elif stripped.endswith("!"):
        pause_ms = 650
    elif stripped.endswith("."):
        pause_ms = 580
    elif stripped.endswith(":"):
        pause_ms = 460
    elif stripped.endswith(";"):
        pause_ms = 410
    elif stripped.endswith(","):
        pause_ms = 300
    else:
        pause_ms = 500

    # Frases reflexivas recebem um pouco mais de espaço e menor velocidade.
    if normalized.startswith((
        "guarde",
        "em resumo",
        "pense",
        "imagine",
        "o ponto",
        "observe",
        "lembre",
        "repare",
    )):
        rate -= 2
        pause_ms += 80

    rate = max(-12, min(1, rate))
    pitch = max(-4, min(4, pitch))
    return f"{rate:+d}%", f"{pitch:+d}Hz", pause_ms


# Monkeypatch deliberado: todo o restante do pipeline permanece idêntico.
base.build_turns = build_turns
base.prosody_for = prosody_for


if __name__ == "__main__":
    asyncio.run(base.main())
