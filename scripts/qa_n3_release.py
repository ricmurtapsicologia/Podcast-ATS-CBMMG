from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from n3_casting import assert_cast_gender, gender_counts

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")


def ffprobe(path: Path) -> dict:
    raw = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=channels,sample_rate,duration,bit_rate",
            "-of", "json", str(path),
        ],
        text=True,
    )
    return json.loads(raw)["streams"][0]


def max_volume(path: Path) -> float:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=True,
    )
    match = re.search(r"max_volume:\s*(-?[0-9.]+) dB", proc.stderr)
    if not match:
        raise AssertionError(f"max_volume não identificado: {path}")
    return float(match.group(1))


def check_series1() -> None:
    report = json.loads((ROOT / "assets/audio/serie-1/quality-n3.json").read_text(encoding="utf-8"))
    counts = gender_counts(report["operational_voice_pool"])
    assert counts["M"] >= 2 and counts["F"] >= 2, counts
    expected_multi = {6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 19, 20}
    assert set(report["multivoice_episodes"]) == expected_multi
    assert len(report["episodes"]) == 21
    for e in report["episodes"]:
        path = ROOT / "assets/audio/serie-1" / e["output"]
        assert path.exists() and path.stat().st_size > 1000, path
        info = ffprobe(path)
        assert int(info["channels"]) == 1
        assert int(info["sample_rate"]) == 44100
        assert float(info["duration"]) > 0
        peak = max_volume(path)
        assert peak <= -1.0, (path, peak)
        speaker_gender = e.get("speaker_gender", {})
        assert_cast_gender(e["speaker_cast"], speaker_gender, context=f"A1-{e['episode']:03d}")
        if e["episode"] in expected_multi:
            assert e["multivoice_required"] is True
            assert len(e["voices"]) >= 2
            non_narrators = [s for s in e["speakers"] if s != "INSTRUTOR"]
            if len(non_narrators) >= 2:
                assert len({e["speaker_cast"][s] for s in non_narrators}) == len(non_narrators), e
        token = f"assets/audio/serie-1/{e['output']}?v={report['version']}"
        assert token in APP, token


def check_series2() -> None:
    report = json.loads((ROOT / "assets/audio/serie-2/quality-n3.json").read_text(encoding="utf-8"))
    counts = gender_counts(report["operational_voice_pool"])
    assert counts["M"] >= 2 and counts["F"] >= 2, counts
    expected_multi = {4, 5, 6, 7, 8, 9}
    assert set(report["cinematic_multivoice_episodes"]) == expected_multi
    assert len(report["episodes"]) == 14
    role_gender = report["role_gender"]
    assert_cast_gender(report["character_cast"], role_gender, context="Série 2 cast global")
    conflicts = [("gorette", "maria"), ("claudio", "ana"), ("guilherme", "fernanda"), ("host", "julia"), ("host", "dra_sara"), ("lourdes", "fatima")]
    for left, right in conflicts:
        assert report["character_cast"][left] != report["character_cast"][right]
    for e in report["episodes"]:
        path = ROOT / "assets/audio/serie-2" / e["output"]
        assert path.exists() and path.stat().st_size > 1000, path
        info = ffprobe(path)
        assert int(info["sample_rate"]) == 44100
        assert float(info["duration"]) > 0
        expected_channels = 2 if e["profile"] == "N3-D" else 1
        assert int(info["channels"]) == expected_channels
        peak = max_volume(path)
        assert peak <= -1.0, (path, peak)
        assert e["text_integrity_spoken_content"] == 1.0
        assert_cast_gender(e["role_cast"], {r: role_gender[r] for r in e["roles"]}, context=f"A2-{e['episode']:03d}")
        if e["episode"] in expected_multi:
            assert len(e["voices"]) >= 2
        token = f"assets/audio/serie-2/{e['output']}?v={report['version']}"
        assert token in APP, token


assert "speechSynthesis" not in APP
check_series1()
check_series2()
print("PASS: N3 release gate 35/35; casting por gênero; multivoz; ffprobe; pico; URLs.")
