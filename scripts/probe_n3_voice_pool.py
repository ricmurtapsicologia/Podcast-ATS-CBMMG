from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from n3_casting import VOICE_GENDER

CANDIDATES = [
    "pt-BR-ThalitaMultilingualNeural",
    "pt-BR-AntonioNeural",
    "pt-BR-FranciscaNeural",
    "pt-BR-MacerioMultilingualNeural",
    "pt-BR-ThalitaNeural",
    "pt-BR-FabioNeural",
    "pt-BR-BrendaNeural",
    "pt-BR-DonatoNeural",
    "pt-BR-GiovannaNeural",
    "pt-BR-HumbertoNeural",
    "pt-BR-JulioNeural",
    "pt-BR-NicolauNeural",
    "pt-BR-ValerioNeural",
    "pt-BR-LeilaNeural",
    "pt-BR-ManuelaNeural",
    "pt-BR-YaraNeural",
]


async def probe(voice: str, workdir: Path, timeout: int) -> dict:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", voice)
    path = workdir / f"{safe}.mp3"
    result = {
        "voice": voice,
        "gender": VOICE_GENDER.get(voice),
        "operational": False,
        "bytes": 0,
        "error": None,
    }
    try:
        communicator = edge_tts.Communicate(
            text="Teste breve de disponibilidade da voz neural em português do Brasil.",
            voice=voice,
            rate="-2%",
            pitch="+0Hz",
            volume="+0%",
        )
        await asyncio.wait_for(communicator.save(str(path)), timeout=timeout)
        size = path.stat().st_size if path.exists() else 0
        result["bytes"] = size
        result["operational"] = size > 500
        if not result["operational"]:
            result["error"] = "arquivo vazio ou insuficiente"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        path.unlink(missing_ok=True)
    return result


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/n3-voice-probe-latest.json")
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    workdir = ROOT / ".tmp_n3_voice_probe"
    workdir.mkdir(parents=True, exist_ok=True)

    results = []
    for voice in CANDIDATES:
        item = await probe(voice, workdir, args.timeout)
        results.append(item)
        status = "OK" if item["operational"] else "FAIL"
        print(f"[{status}] {voice} ({item['gender']}) {item['error'] or ''}")

    operational = [item for item in results if item["operational"]]
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "edge-tts",
        "probe_is_availability_only": True,
        "candidates_tested": len(results),
        "operational_count": len(operational),
        "operational_male": [x["voice"] for x in operational if x["gender"] == "M"],
        "operational_female": [x["voice"] for x in operational if x["gender"] == "F"],
        "results": results,
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "tested": report["candidates_tested"],
        "operational": report["operational_count"],
        "male": report["operational_male"],
        "female": report["operational_female"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
