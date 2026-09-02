from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "remaster_series1_n3.py"

INSERT = '''\n\nasync def render_series(pool: list[dict], sem: asyncio.Semaphore, builder=None):\n    \"\"\"Renderiza episódios em paralelo; o semaphore continua limitando chamadas TTS.\"\"\"\n    builder = builder or build_episode\n\n    async def render(number: int):\n        print(f\"[A1-{number:03d}] render\")\n        return await builder(number, pool, sem)\n\n    results = await asyncio.gather(*(render(number) for number in range(1, 22)))\n    return sorted(results, key=lambda item: item[\"episode\"])\n'''

OLD = '''    quality = []\n    for number in range(1, 22):\n        print(f\"[A1-{number:03d}] render\")\n        quality.append(await build_episode(number, pool, sem))\n'''
NEW = '''    quality = await render_series(pool, sem)\n'''


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    changed = False

    if "async def render_series(" not in text:
        marker = "\n\nasync def main():\n"
        if marker not in text:
            raise RuntimeError("Ponto de inserção de render_series não encontrado")
        text = text.replace(marker, INSERT + marker, 1)
        changed = True

    if OLD in text:
        text = text.replace(OLD, NEW, 1)
        changed = True
    elif "quality = await render_series(pool, sem)" not in text:
        raise RuntimeError("Loop sequencial esperado não encontrado e otimização não detectada")

    TARGET.write_text(text, encoding="utf-8")
    print("CHANGED" if changed else "ALREADY_OPTIMIZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
