from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "remaster_series1_n3.py"
ROTEIROS = ROOT / "roteiros" / "serie-1"
VERSION = "n3-ptbr-native-20260901"

NATIVE_CANDIDATES = [
    ("pt-BR-FranciscaNeural", "F"),
    ("pt-BR-AntonioNeural", "M"),
    ("pt-BR-ThalitaNeural", "F"),
    ("pt-BR-FabioNeural", "M"),
    ("pt-BR-BrendaNeural", "F"),
    ("pt-BR-DonatoNeural", "M"),
    ("pt-BR-GiovannaNeural", "F"),
    ("pt-BR-HumbertoNeural", "M"),
    ("pt-BR-JulioNeural", "M"),
    ("pt-BR-NicolauNeural", "M"),
    ("pt-BR-ValerioNeural", "M"),
    ("pt-BR-LeilaNeural", "F"),
    ("pt-BR-ManuelaNeural", "F"),
    ("pt-BR-YaraNeural", "F"),
]


def normalize_sources() -> int:
    changed = 0
    substitutions = [
        (re.compile(r"\bhobbies\b", re.I), "passatempos"),
        (re.compile(r"\bhobby\b", re.I), "passatempo"),
    ]
    for path in sorted(ROTEIROS.glob("a1-*.txt")):
        original = path.read_text(encoding="utf-8")
        updated = original
        for pattern, replacement in substitutions:
            updated = pattern.sub(replacement, updated)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return changed


def patch_renderer() -> None:
    text = TARGET.read_text(encoding="utf-8")

    text, n = re.subn(
        r'^VERSION = "[^"]+"$',
        f'VERSION = "{VERSION}"',
        text,
        count=1,
        flags=re.M,
    )
    if n != 1:
        raise RuntimeError("VERSION da Série 1 não localizada.")

    candidates = "VOICE_CANDIDATES = [\n" + "\n".join(
        f'    ("{voice}", "{gender}"),' for voice, gender in NATIVE_CANDIDATES
    ) + "\n]"
    text, n = re.subn(
        r'VOICE_CANDIDATES = \[.*?\n\]',
        candidates,
        text,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise RuntimeError("VOICE_CANDIDATES não localizado.")

    text = re.sub(
        r'pool_ready\(operational, min_male=\d+, min_female=\d+\)',
        'pool_ready(operational, min_male=1, min_female=2)',
        text,
    )
    text = re.sub(
        r'require_balanced_pool\(operational, min_male=\d+, min_female=\d+\)',
        'require_balanced_pool(operational, min_male=1, min_female=2)',
        text,
    )

    safe_preferences = '''def voice_preferences(role: str, gender: str | None):
    female = [
        "pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural", "pt-BR-BrendaNeural",
        "pt-BR-GiovannaNeural", "pt-BR-LeilaNeural", "pt-BR-ManuelaNeural", "pt-BR-YaraNeural",
    ]
    male = [
        "pt-BR-AntonioNeural", "pt-BR-FabioNeural", "pt-BR-DonatoNeural",
        "pt-BR-HumbertoNeural", "pt-BR-JulioNeural", "pt-BR-NicolauNeural", "pt-BR-ValerioNeural",
    ]
    if role == "narrator":
        return female + male
    if gender == "F":
        return female
    if gender == "M":
        return male
    return female + male
'''
    text, n = re.subn(
        r'def voice_preferences\(role: str, gender: str \| None\):.*?(?=\n\ndef build_episode_cast)',
        safe_preferences.rstrip(),
        text,
        count=1,
        flags=re.S,
    )
    if n != 1:
        raise RuntimeError("voice_preferences não localizado.")

    old_guard = '''    expected_gender = {speaker: info[speaker][1] for speaker in speakers}
    assert_cast_gender(cast, expected_gender, context="Série 1")
    return cast'''
    new_guard = '''    expected_gender = {speaker: info[speaker][1] for speaker in speakers}
    assert_cast_gender(cast, expected_gender, context="Série 1")
    if any("Multilingual" in voice for voice in cast.values()):
        raise RuntimeError(f"Série 1: voz multilíngue proibida no casting: {cast}")
    if any(not voice.startswith("pt-BR-") for voice in cast.values()):
        raise RuntimeError(f"Série 1: voz fora de pt-BR no casting: {cast}")
    if "ABORDADOR_F" in cast and "TENTANTE_F" in cast and cast["ABORDADOR_F"] == cast["TENTANTE_F"]:
        raise RuntimeError(
            f"Série 1: ABORDADOR_F e TENTANTE_F exigem vozes-base femininas distintas; casting={cast}"
        )
    return cast'''
    if old_guard in text:
        text = text.replace(old_guard, new_guard, 1)
    else:
        if 'voz multilíngue proibida no casting' not in text:
            raise RuntimeError("Ponto do language guard não localizado.")
        if 'ABORDADOR_F e TENTANTE_F exigem vozes-base femininas distintas' not in text:
            anchor = '''    if any(not voice.startswith("pt-BR-") for voice in cast.values()):
        raise RuntimeError(f"Série 1: voz fora de pt-BR no casting: {cast}")
    return cast'''
            replacement = '''    if any(not voice.startswith("pt-BR-") for voice in cast.values()):
        raise RuntimeError(f"Série 1: voz fora de pt-BR no casting: {cast}")
    if "ABORDADOR_F" in cast and "TENTANTE_F" in cast and cast["ABORDADOR_F"] == cast["TENTANTE_F"]:
        raise RuntimeError(
            f"Série 1: ABORDADOR_F e TENTANTE_F exigem vozes-base femininas distintas; casting={cast}"
        )
    return cast'''
            if anchor not in text:
                raise RuntimeError("Ponto do guard de vozes femininas distintas não localizado.")
            text = text.replace(anchor, replacement, 1)

    if '"native_ptbr_only": True,' not in text:
        episode_marker = '        "pronunciation_dictionary": True,\n'
        if episode_marker not in text:
            raise RuntimeError("Ponto de metadado por episódio não localizado.")
        text = text.replace(
            episode_marker,
            episode_marker + '        "native_ptbr_only": True,\n',
            1,
        )

        report_marker = '        "operational_voice_pool": pool,\n'
        if report_marker not in text:
            raise RuntimeError("Ponto de metadado do relatório não localizado.")
        text = text.replace(
            report_marker,
            report_marker + '        "native_ptbr_only": True,\n',
            1,
        )

    forbidden = [
        "pt-BR-ThalitaMultilingualNeural",
        "pt-BR-MacerioMultilingualNeural",
    ]
    for voice in forbidden:
        if voice in text:
            raise RuntimeError(f"Voz multilíngue ainda presente no renderizador: {voice}")

    if 'min_male=1, min_female=2' not in text:
        raise RuntimeError("Pool nativo 1M/2F não foi aplicado.")
    if 'ABORDADOR_F e TENTANTE_F exigem vozes-base femininas distintas' not in text:
        raise RuntimeError("Gate de vozes femininas distintas não foi aplicado.")
    if f'VERSION = "{VERSION}"' not in text:
        raise RuntimeError("Versão pt-BR nativa não foi aplicada.")
    if 'native_ptbr_only' not in text:
        raise RuntimeError("Metadado native_ptbr_only ausente.")

    TARGET.write_text(text, encoding="utf-8")


def main() -> int:
    normalized = normalize_sources()
    patch_renderer()
    print(
        f"PASS: Série 1 blindada para pt-BR nativo; pool mínimo=1M/2F; "
        f"personagens femininas distintas; roteiros normalizados={normalized}; version={VERSION}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
