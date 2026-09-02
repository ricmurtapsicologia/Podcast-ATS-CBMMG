from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import remaster_series1_n3 as series1


async def main() -> int:
    active = 0
    peak = 0
    lock = asyncio.Lock()

    async def fake_builder(number, pool, sem):
        nonlocal active, peak
        async with lock:
            active += 1
            peak = max(peak, active)
        await asyncio.sleep(0.02)
        async with lock:
            active -= 1
        return {"episode": number}

    sem = asyncio.Semaphore(series1.MAX_CONCURRENT_SYNTH)
    result = await series1.render_series([], sem, builder=fake_builder)
    episodes = [item["episode"] for item in result]
    if episodes != list(range(1, 22)):
        raise RuntimeError(f"Ordem dos episódios alterada: {episodes}")
    if peak <= 1:
        raise RuntimeError("Renderização continua sequencial; concorrência real não detectada")
    if "async with sem" not in Path(series1.__file__).read_text(encoding="utf-8"):
        raise RuntimeError("Semaphore de síntese não encontrado no pipeline")
    print(f"PASS: Série 1 concorrente; peak_episode_tasks={peak}; ordem 1..21 preservada; TTS protegido por semaphore={series1.MAX_CONCURRENT_SYNTH}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
