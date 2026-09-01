from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: esperado 1 match, encontrados {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    out, count = re.subn(pattern, replacement, text, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: esperado 1 match, encontrados {count}")
    return out


def patch_series1() -> None:
    path = ROOT / "scripts/remaster_series1_n3.py"
    text = path.read_text(encoding="utf-8")
    if "from n3_casting import" not in text:
        text = replace_once(
            text,
            "from n3_audio_core import breath_units, lexical_tokens, prosody, speakable\n",
            "from n3_audio_core import breath_units, lexical_tokens, prosody, speakable\nfrom n3_casting import assert_cast_gender, choose_voice, pool_ready, require_balanced_pool\n",
            "S1 import casting",
        )
    text = re.sub(r'VERSION = "n3-cast-20260901[a-z]*"', 'VERSION = "n3-cast-20260901c"', text, count=1)
    text = regex_once(
        text,
        r"async def resolve_operational_pool\(\):.*?\n\ndef voice_preferences",
        '''async def resolve_operational_pool():
    operational = []
    for name, gender in VOICE_CANDIDATES:
        if await probe_voice(name):
            operational.append({"voice": name, "gender": gender})
        if pool_ready(operational, min_male=2, min_female=2):
            break
    require_balanced_pool(operational, min_male=2, min_female=2)
    return operational


def voice_preferences''',
        "S1 balanced pool",
    )
    text = regex_once(
        text,
        r"def build_episode_cast\(turns: list\[dict\], pool: list\[dict\]\):.*?\n\n\nasync def synth",
        '''def build_episode_cast(turns: list[dict], pool: list[dict]):
    speakers = []
    info = {}
    for turn in turns:
        if turn["speaker"] not in info:
            speakers.append(turn["speaker"])
            info[turn["speaker"]] = (turn["role"], turn["gender"])

    cast: dict[str, str] = {}
    used: set[str] = set()
    non_narrators = [s for s in speakers if info[s][0] != "narrator"]
    narrators = [s for s in speakers if info[s][0] == "narrator"]

    for speaker in non_narrators:
        role, gender = info[speaker]
        cast[speaker] = choose_voice(pool, voice_preferences(role, gender), expected_gender=gender, used=used)
        used.add(cast[speaker])

    for speaker in narrators:
        cast[speaker] = choose_voice(pool, voice_preferences("narrator", None), expected_gender=None, used=used)
        used.add(cast[speaker])

    expected_gender = {speaker: info[speaker][1] for speaker in speakers}
    assert_cast_gender(cast, expected_gender, context="Série 1")
    if len(non_narrators) >= 2 and len({cast[s] for s in non_narrators}) != len(non_narrators):
        raise RuntimeError("Série 1: personagens simultâneos sem diferenciação vocal.")
    return cast


async def synth''',
        "S1 cast builder",
    )
    if '"speaker_gender"' not in text:
        text = replace_once(
            text,
            '        "speaker_cast": {s: cast[s] for s in episode_speakers},\n        "voices": unique_voices,',
            '        "speaker_cast": {s: cast[s] for s in episode_speakers},\n        "speaker_gender": {s: PREFIXES.get(s, ("narrator", None))[1] for s in episode_speakers},\n        "voices": unique_voices,',
            "S1 manifest gender",
        )
    path.write_text(text, encoding="utf-8")


def patch_series2() -> None:
    path = ROOT / "scripts/remaster_series2_n3.py"
    text = path.read_text(encoding="utf-8")
    if "from n3_casting import" not in text:
        text = replace_once(
            text,
            "from n3_audio_core import breath_units, normalize, prosody, speakable\nfrom n3_foley import apply_sound_design\n",
            "from n3_audio_core import breath_units, normalize, prosody, speakable\nfrom n3_casting import assert_cast_gender, assert_distinct_pairs, choose_voice, pool_ready, require_balanced_pool\nfrom n3_foley import apply_sound_design\n",
            "S2 import casting",
        )
    text = re.sub(r'VERSION = "n3-cast-20260901[a-z]*"', 'VERSION = "n3-cast-20260901c"', text, count=1)
    text = regex_once(
        text,
        r"async def resolve_operational_pool\(\):.*?\n\ndef resolve_cast",
        '''async def resolve_operational_pool():
    operational = []
    for name, gender in VOICE_CANDIDATES:
        if await probe_voice(name):
            operational.append({"voice": name, "gender": gender})
        if pool_ready(operational, min_male=2, min_female=2):
            break
    require_balanced_pool(operational, min_male=2, min_female=2)
    return operational


def resolve_cast''',
        "S2 balanced pool",
    )
    text = regex_once(
        text,
        r"def resolve_cast\(pool: list\[dict\]\):.*?\n\n\ndef persona_values",
        '''def resolve_cast(pool: list[dict]):
    cast: dict[str, str] = {}
    for role, gender in ROLE_GENDER.items():
        cast[role] = choose_voice(pool, ROLE_PREFERENCES[role], expected_gender=gender)

    for left, right in CONFLICT_PAIRS:
        if cast[left] == cast[right]:
            cast[right] = choose_voice(
                pool,
                ROLE_PREFERENCES[right],
                expected_gender=ROLE_GENDER[right],
                used={cast[left]},
            )

    assert_cast_gender(cast, ROLE_GENDER, context="Série 2 cast global")
    assert_distinct_pairs(cast, CONFLICT_PAIRS, context="Série 2 cast global")
    return cast


def persona_values''',
        "S2 cast resolver",
    )
    if "assert_cast_gender(episode_cast" not in text:
        text = replace_once(
            text,
            '    episode_cast = {role: cast[role] for role in episode_roles}\n    if cinematic and len(set(episode_cast.values())) < 2:',
            '    episode_cast = {role: cast[role] for role in episode_roles}\n    assert_cast_gender(episode_cast, {role: ROLE_GENDER[role] for role in episode_roles}, context=f"A2-{number:03d}")\n    if cinematic and len(set(episode_cast.values())) < 2:',
            "S2 episode gender gate",
        )
    if '"role_gender"' not in text:
        text = replace_once(
            text,
            '        "character_cast": cast,\n        "cinematic_multivoice_episodes": sorted(CINEMATIC_EPISODES),',
            '        "character_cast": cast,\n        "role_gender": ROLE_GENDER,\n        "cinematic_multivoice_episodes": sorted(CINEMATIC_EPISODES),',
            "S2 manifest gender",
        )
    path.write_text(text, encoding="utf-8")


def patch_workflow(path_str: str, series: int) -> None:
    path = ROOT / path_str
    text = path.read_text(encoding="utf-8")
    if "scripts/n3_casting.py" not in text:
        text = replace_once(
            text,
            "      - 'scripts/n3_audio_core.py'\n",
            "      - 'scripts/n3_audio_core.py'\n      - 'scripts/n3_casting.py'\n",
            f"workflow S{series} trigger",
        )
    if "sum(v['gender']=='M'" not in text:
        text = replace_once(
            text,
            "          assert len(report['operational_voice_pool'])>=2\n",
            "          assert sum(v['gender']=='M' for v in report['operational_voice_pool'])>=2\n          assert sum(v['gender']=='F' for v in report['operational_voice_pool'])>=2\n",
            f"workflow S{series} pool gate",
        )
    if series == 2 and "role_gender=report['role_gender']" not in text:
        text = replace_once(
            text,
            "          cast=report['character_cast']\n          for a,b in conflicts:\n              assert cast[a] != cast[b], (a,b,cast[a])\n",
            "          cast=report['character_cast']\n          role_gender=report['role_gender']\n          female_tokens=('Thalita','Francisca','Brenda','Giovanna')\n          for role,gender in role_gender.items():\n              if gender:\n                  voice=cast[role]\n                  actual='F' if any(x in voice for x in female_tokens) else 'M'\n                  assert actual==gender, (role,voice,gender)\n          for a,b in conflicts:\n              assert cast[a] != cast[b], (a,b,cast[a])\n",
            "workflow S2 gender gate",
        )
    path.write_text(text, encoding="utf-8")


def patch_readme() -> None:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    if "# Gate de publicação N3" in text:
        return
    marker = "# Arquitetura atual\n"
    section = (
        "# Gate de publicação N3\n\n"
        "Desde 01/09/2026, as Séries 1 e 2 usam casting N3 por gênero e identidade vocal, "
        "pool operacional mínimo de duas vozes masculinas e duas femininas, gate técnico de 35/35 masters "
        "e smoke E2E do player em Chromium. O CI valida sample rate, canais, duração, pico, integridade do texto, "
        "URLs do runtime, ausência de `speechSynthesis`, diferenciação de personagens e coerência entre gênero do papel e voz.\n\n"
        "A arquitetura de áudio fica separada em: roteiro → casting (`n3_casting.py`) → prosódia/segmentação "
        "(`n3_audio_core.py`) → síntese/remasterização → manifesto de QA → smoke E2E → publicação.\n\n---\n\n"
    )
    text = replace_once(text, marker, section + marker, "README gate N3")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_series1()
    patch_series2()
    patch_workflow(".github/workflows/remaster-series1-n3.yml", 1)
    patch_workflow(".github/workflows/remaster-series2-n3.yml", 2)
    patch_readme()
    print("Hardening N3 aplicado.")


if __name__ == "__main__":
    main()
