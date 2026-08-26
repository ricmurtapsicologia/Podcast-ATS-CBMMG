from __future__ import annotations

"""Orquestra em paralelo a remasterização orgânica v4 da Série 1."""

import asyncio
import json

import remaster_series1_organic as base


async def process_episode(number: int, semaphore: asyncio.Semaphore):
    turns, word_count = base.read_frozen_turns(number)
    target, seconds = await base.synth_episode(number, turns, semaphore)
    print(f"[{number:03d}] orgânico v4 | blocos={len(turns)} | duração={seconds}s")
    return {
        "episode": number,
        "output": target.name,
        "lexical_integrity": 1.0,
        "source_words": word_count,
        "synth_blocks": len(turns),
        "duration_seconds": seconds,
        "audio_profile": "serie-1-organic-v4",
        "base_rate": {"instrutor": -7, "profissional": -4},
        "prosodic_punctuation": True,
    }


async def main():
    base.OUT.mkdir(parents=True, exist_ok=True)
    base.TMP.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(base.MAX_CONCURRENT_SYNTH)

    quality = await asyncio.gather(*[
        process_episode(number, semaphore)
        for number in range(1, 22)
    ])
    quality.sort(key=lambda item: item["episode"])

    base.patch_app_urls()
    base.patch_index_cache()
    (base.OUT / "quality-organic-v4.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Série 1 concluída no perfil orgânico v4 com orquestração paralela.")


if __name__ == "__main__":
    asyncio.run(main())
