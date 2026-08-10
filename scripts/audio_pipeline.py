#!/usr/bin/env python3
"""Non-destructive media QA pipeline for Podcast ATS.

Audit mode never changes source media. Normalize mode always writes to a distinct
output directory and refuses to overwrite source files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

MEDIA_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
IGNORED_DIRS = {".git", "node_modules", "artifacts", "audio-web", "processed"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ffprobe(path: Path) -> dict[str, Any]:
    if not shutil.which("ffprobe"):
        return {"probeAvailable": False}
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "format=duration,bit_rate:stream=codec_name,sample_rate,channels,bit_rate",
        "-of", "json", str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return {"probeAvailable": True, "probeError": proc.stderr.strip()}
    data = json.loads(proc.stdout or "{}")
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    stream = streams[0] if streams else {}
    return {
        "probeAvailable": True,
        "durationSeconds": round(float(fmt.get("duration", 0) or 0), 3),
        "codec": stream.get("codec_name"),
        "sampleRate": int(stream.get("sample_rate", 0) or 0),
        "channels": stream.get("channels"),
        "bitRate": int(stream.get("bit_rate") or fmt.get("bit_rate") or 0),
    }


def iter_media(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in MEDIA_EXTENSIONS:
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        yield path


def audit(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    rows = []
    hashes: dict[str, list[str]] = {}
    errors: list[str] = []
    warnings: list[str] = []

    for path in sorted(iter_media(root)):
        rel = path.relative_to(root).as_posix()
        digest = sha256(path)
        info = {
            "path": rel,
            "sizeBytes": path.stat().st_size,
            "sha256": digest,
            **ffprobe(path),
        }
        rows.append(info)
        hashes.setdefault(digest, []).append(rel)
        if info.get("probeError"):
            errors.append(f"unreadable media: {rel}")
        if info.get("durationSeconds") == 0 and info.get("probeAvailable"):
            warnings.append(f"zero/unknown duration: {rel}")
        if path.stat().st_size == 0:
            errors.append(f"empty media file: {rel}")

    duplicates = [paths for paths in hashes.values() if len(paths) > 1]
    payload = {
        "schemaVersion": 1,
        "mode": "read-only-audit",
        "mediaCount": len(rows),
        "totalBytes": sum(r["sizeBytes"] for r in rows),
        "duplicatesByHash": duplicates,
        "errors": errors,
        "warnings": warnings,
        "media": rows,
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"audited {len(rows)} media files; inventory: {out}")
    if duplicates:
        print(f"note: {len(duplicates)} duplicate hash group(s) detected")
    return 1 if errors else 0


def normalize(args: argparse.Namespace) -> int:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required for normalize mode")
    source = Path(args.source).resolve()
    output_root = Path(args.output_dir).resolve()
    if not source.exists() or source.suffix.casefold() not in MEDIA_EXTENSIONS:
        raise SystemExit("source must be an existing supported audio file")
    if output_root == source.parent or output_root in source.parents:
        raise SystemExit("output directory must be distinct from the source location")
    output_root.mkdir(parents=True, exist_ok=True)
    target = output_root / (source.stem + ".mp3")
    if target.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing output: {target}")
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y" if args.force else "-n",
        "-i", str(source),
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar", "48000", "-codec:a", "libmp3lame", "-b:a", "160k", str(target),
    ]
    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        return proc.returncode
    print(f"normalized derivative created at {target}; original preserved")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Podcast ATS media pipeline")
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("audit")
    a.add_argument("--root", default=".")
    a.add_argument("--output", default="artifacts/audio-inventory.json")
    a.set_defaults(func=audit)
    n = sub.add_parser("normalize")
    n.add_argument("--source", required=True)
    n.add_argument("--output-dir", default="audio-web")
    n.add_argument("--force", action="store_true")
    n.set_defaults(func=normalize)
    return p


def main() -> int:
    args = parser().parse_args()
    return int(args.func(args))

if __name__ == "__main__":
    sys.exit(main())
