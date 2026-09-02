from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.js"
S1 = ROOT / "assets" / "audio" / "serie-1" / "quality-n3.json"
S2 = ROOT / "assets" / "audio" / "serie-2" / "quality-n3.json"
OUT = ROOT / "reports" / "n3-perceptual-audit-latest.json"
VERSION = "n3-cast-20260901c"

PRIORITY_MAX = {
    "A1-008", "A1-013", "A1-015",
    "A2-004", "A2-005", "A2-006", "A2-007", "A2-008", "A2-009",
}
PRIORITY_HIGH = {
    "A1-006", "A1-007", "A1-009", "A1-010", "A1-011", "A1-014",
    "A1-016", "A1-019", "A1-020",
}

FIELDS = [
    "naturalidade", "pronuncia", "ritmo", "pausas", "prosodia", "inteligibilidade",
    "emocao", "casting", "diferenciacao_personagens", "volume", "ruido_artefato",
    "sound_design",
]


def titles_from_app() -> dict[str, str]:
    text = APP.read_text(encoding="utf-8")
    rows = re.findall(r'\{title:"([^"]+)",url:"assets/audio/serie-([12])/a([12])-(\d{3})-n3\.mp3\?v=([^\"]+)"\}', text)
    result = {}
    for title, series, a_series, number, version in rows:
        assert series == a_series
        assert version == VERSION, (title, version)
        code = f"A{series}-{number}"
        result[code] = title
    if len(result) != 35:
        raise RuntimeError(f"Esperados 35 títulos N3; encontrados {len(result)}")
    return result


def manifest_rows(path: Path, series: int) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for ep in data["episodes"]:
        number = int(ep["episode"])
        code = f"A{series}-{number:03d}"
        rows.append({
            "code": code,
            "duration_seconds": ep.get("duration_seconds"),
            "profile": ep.get("profile"),
        })
    return rows


def priority(code: str) -> str:
    if code in PRIORITY_MAX:
        return "MAXIMA"
    if code in PRIORITY_HIGH:
        return "ALTA"
    return "NORMAL"


def main() -> int:
    titles = titles_from_app()
    rows = manifest_rows(S1, 1) + manifest_rows(S2, 2)
    if len(rows) != 35:
        raise RuntimeError(f"Esperados 35 episódios; encontrados {len(rows)}")

    episodes = []
    for row in rows:
        code = row["code"]
        item = {
            "code": code,
            "title": titles[code],
            "duration_seconds": row["duration_seconds"],
            "profile": row["profile"],
            "priority": priority(code),
        }
        for field in FIELDS:
            item[field] = None
        item["observacoes"] = "Aguardando escuta perceptual humana real. Gates automatizados não preenchem este campo."
        item["decision"] = "PENDING_HUMAN"
        episodes.append(item)

    report = {
        "version": VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "standard": "AUDIO_N3_STANDARD.md",
        "automated_gate_is_not_perceptual_review": True,
        "allowed_final_decisions_after_listening": ["PASS", "AJUSTAR", "REFAZER"],
        "current_summary": {
            "PASS": 0,
            "AJUSTAR": 0,
            "REFAZER": 0,
            "PENDING_HUMAN": 35,
        },
        "priority_maxima": sorted(PRIORITY_MAX),
        "priority_alta": sorted(PRIORITY_HIGH),
        "episodes": episodes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS: matriz perceptual inicializada; 35/35 = PENDING_HUMAN; nenhum episódio falsamente aprovado por automação.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
