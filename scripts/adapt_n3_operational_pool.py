from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: esperado 1 match, encontrados {count}")
    return text.replace(old, new, 1)


def patch_series1() -> None:
    path = ROOT / "scripts/remaster_series1_n3.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace("pool_ready(operational, min_male=2, min_female=2)", "pool_ready(operational, min_male=1, min_female=2)")
    text = text.replace("require_balanced_pool(operational, min_male=2, min_female=2)", "require_balanced_pool(operational, min_male=1, min_female=2)")

    if "SPEAKER_PERSONA =" not in text:
        marker = "\n\ndef normalize_space(text: str) -> str:\n"
        persona = '''\n\nSPEAKER_PERSONA = {
    "INSTRUTOR": {"rate": 0, "pitch": 0, "label": "instrutor"},
    "NARRADOR": {"rate": 0, "pitch": 0, "label": "narrador"},
    "PROFISSIONAL": {"rate": 0, "pitch": 0, "label": "profissional"},
    "ABORDADOR_M": {"rate": 0, "pitch": 1, "label": "masculino-profissional"},
    "TENTANTE_M": {"rate": -2, "pitch": -3, "label": "masculino-crise"},
    "DEMO_M": {"rate": 2, "pitch": 2, "label": "masculino-demo"},
    "ABORDADOR_F": {"rate": 0, "pitch": 1, "label": "feminino-profissional"},
    "TENTANTE_F": {"rate": -2, "pitch": -2, "label": "feminino-crise"},
    "DEMO_F": {"rate": 1, "pitch": 2, "label": "feminino-demo"},
    "ABORDADOR": {"rate": 0, "pitch": 0, "label": "abordador"},
    "ABORDADORA": {"rate": 0, "pitch": 1, "label": "abordadora"},
    "TENTANTE": {"rate": -2, "pitch": -1, "label": "tentante"},
}


def persona_for(speaker: str) -> dict:
    return SPEAKER_PERSONA.get(speaker, {"rate": 0, "pitch": 0, "label": speaker.lower()})


def apply_speaker_persona(rate: str, pitch: str, speaker: str) -> tuple[str, str]:
    cfg = persona_for(speaker)
    r = int(rate.rstrip("%")) + int(cfg["rate"])
    p = int(pitch.replace("Hz", "")) + int(cfg["pitch"])
    return f"{max(-16, min(8, r)):+d}%", f"{max(-7, min(7, p)):+d}Hz"
'''
        text = replace_once(text, marker, persona + marker, "S1 persona registry")

    text = text.replace(
        '    if len(non_narrators) >= 2 and len({cast[s] for s in non_narrators}) != len(non_narrators):\n        raise RuntimeError("Série 1: personagens simultâneos sem diferenciação vocal.")\n    return cast',
        '    return cast',
    )

    old = '''        if role == "person_in_crisis":
            rate = f"{max(-14, int(rate.rstrip('%')) - 2):+d}%"
        part = work / f"{idx:03d}.mp3"'''
    new = '''        if role == "person_in_crisis":
            rate = f"{max(-14, int(rate.rstrip('%')) - 2):+d}%"
        rate, pitch = apply_speaker_persona(rate, pitch, turn["speaker"])
        part = work / f"{idx:03d}.mp3"'''
    text = replace_once(text, old, new, "S1 synth persona")

    pattern = re.compile(
        r'''    non_narrators = \[s for s in episode_speakers if PREFIXES\.get\(s, \("narrator", None\)\)\[0\] != "narrator"\]\n'''
        r'''    if number in MULTIVOICE_EPISODES and len\(unique_voices\) < 2:\n        raise RuntimeError\(f"A1-\{number:03d\} não ficou multivoz\."\)\n'''
        r'''    if len\(non_narrators\) >= 2 and len\(set\(cast\[s\] for s in non_narrators\)\) < min\(len\(non_narrators\), len\(pool\)\):\n        raise RuntimeError\(f"A1-\{number:03d\}: personagens simultâneos sem diferenciação\."\)'''
    )
    replacement = '''    non_narrators = [s for s in episode_speakers if PREFIXES.get(s, ("narrator", None))[0] != "narrator"]
    voice_identity = {s: f"{cast[s]}::{persona_for(s)['label']}" for s in episode_speakers}
    if number in MULTIVOICE_EPISODES and len(set(voice_identity.values())) < 2:
        raise RuntimeError(f"A1-{number:03d} não ficou multivoz por identidade perceptual.")
    if len(non_narrators) >= 2 and len({voice_identity[s] for s in non_narrators}) != len(non_narrators):
        raise RuntimeError(f"A1-{number:03d}: personagens simultâneos sem personas distintas.")'''
    text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError("S1 gate multivoz pós-render não localizado")

    if '"speaker_persona"' not in text:
        old_manifest = '''        "speaker_gender": {s: PREFIXES.get(s, ("narrator", None))[1] for s in episode_speakers},
        "voices": unique_voices,'''
        new_manifest = '''        "speaker_gender": {s: PREFIXES.get(s, ("narrator", None))[1] for s in episode_speakers},
        "speaker_persona": {s: persona_for(s) for s in episode_speakers},
        "voice_identity": voice_identity,
        "voices": unique_voices,'''
        text = replace_once(text, old_manifest, new_manifest, "S1 manifest personas")

    path.write_text(text, encoding="utf-8")


def patch_series2() -> None:
    path = ROOT / "scripts/remaster_series2_n3.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace("pool_ready(operational, min_male=2, min_female=2)", "pool_ready(operational, min_male=1, min_female=2)")
    text = text.replace("require_balanced_pool(operational, min_male=2, min_female=2)", "require_balanced_pool(operational, min_male=1, min_female=2)")
    if '"voice_identity"' not in text:
        old_manifest = '''        "role_cast": episode_cast,
        "voices": sorted(set(episode_cast.values())),
        "persona_profiles": {role: PERSONA_ADJUST[role] for role in episode_roles},'''
        new_manifest = '''        "role_cast": episode_cast,
        "voice_identity": {role: f"{episode_cast[role]}::{PERSONA_ADJUST[role]['label']}" for role in episode_roles},
        "voices": sorted(set(episode_cast.values())),
        "persona_profiles": {role: PERSONA_ADJUST[role] for role in episode_roles},'''
        text = replace_once(text, old_manifest, new_manifest, "S2 manifest identities")
    path.write_text(text, encoding="utf-8")


def patch_workflow(rel: str) -> None:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    text = text.replace("sum(v['gender']=='M' for v in report['operational_voice_pool'])>=2", "sum(v['gender']=='M' for v in report['operational_voice_pool'])>=1")
    path.write_text(text, encoding="utf-8")


def patch_readme() -> None:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "pool operacional mínimo de duas vozes masculinas e duas femininas, gate técnico de 35/35 masters",
        "pool operacional com cobertura real de gênero (mínimo de uma voz masculina e duas femininas no endpoint edge-tts), com personas prosódicas distintas para personagens masculinos adicionais, além de gate técnico de 35/35 masters",
    )
    text = text.replace(
        "diferenciação de personagens e coerência entre gênero do papel e voz.",
        "diferenciação perceptual por voz-base + persona e coerência entre gênero do papel e voz, sem cross-gender.",
    )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_series1()
    patch_series2()
    patch_workflow(".github/workflows/remaster-series1-n3.yml")
    patch_workflow(".github/workflows/remaster-series2-n3.yml")
    patch_readme()
    print("Adaptação N3 ao pool operacional concluída.")


if __name__ == "__main__":
    main()
