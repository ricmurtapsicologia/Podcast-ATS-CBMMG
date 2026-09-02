from __future__ import annotations

import asyncio
import json
import re
import shutil
from pathlib import Path

import remaster_series1_n3 as n3
from n3_casting import voice_gender

EPISODE = 8
HOTFIX_VERSION = "n3-cast-20260901d"
REPORT = n3.OUT / "quality-n3.json"
HOTFIX_REPORT = n3.ROOT / "reports" / "a1-008-hotfix-casting-ptbr.json"
ROTEIRO = n3.ROTEIROS / "a1-008.txt"
CORE = n3.ROOT / "scripts" / "n3_audio_core.py"
REMASTER = n3.ROOT / "scripts" / "remaster_series1_n3.py"
APP = n3.APP

NARRATOR_CANDIDATES = [
    "pt-BR-FranciscaNeural",
    "pt-BR-ThalitaNeural",
    "pt-BR-BrendaNeural",
    "pt-BR-GiovannaNeural",
    "pt-BR-LeilaNeural",
    "pt-BR-ManuelaNeural",
    "pt-BR-YaraNeural",
]
MALE_CANDIDATES = [
    "pt-BR-AntonioNeural",
    "pt-BR-FabioNeural",
    "pt-BR-DonatoNeural",
    "pt-BR-HumbertoNeural",
    "pt-BR-JulioNeural",
    "pt-BR-NicolauNeural",
    "pt-BR-ValerioNeural",
]


def patch_roteiro() -> None:
    text = ROTEIRO.read_text(encoding="utf-8")
    updated = re.sub(r"\bhobby\b", "passatempo", text, flags=re.IGNORECASE)
    if "hobby" in updated.lower():
        raise RuntimeError("Normalizacao de 'hobby' falhou no A1-008.")
    if "passatempo" not in updated.lower():
        raise RuntimeError("Termo 'passatempo' nao encontrado no A1-008 apos normalizacao.")
    ROTEIRO.write_text(updated, encoding="utf-8")


def patch_pronunciation_dictionary() -> None:
    text = CORE.read_text(encoding="utf-8")
    if "r'\\bMPB\\b': 'eme pê bê'" not in text:
        needle = "    r'\\bOMS\\b': 'O M S',"
        if needle not in text:
            raise RuntimeError("Ponto de insercao do dicionario MPB nao encontrado.")
        text = text.replace(needle, "    r'\\bMPB\\b': 'eme pê bê',\n" + needle, 1)
        CORE.write_text(text, encoding="utf-8")


def patch_renderer_defaults() -> None:
    text = REMASTER.read_text(encoding="utf-8")
    text = text.replace('VERSION = "n3-cast-20260901c"', f'VERSION = "{HOTFIX_VERSION}"')
    text = text.replace(
        "if pool_ready(operational, min_male=1, min_female=2):",
        "if pool_ready(operational, min_male=3, min_female=2):",
    )
    text = text.replace(
        "require_balanced_pool(operational, min_male=1, min_female=2)",
        "require_balanced_pool(operational, min_male=3, min_female=2)",
    )

    old_common = '        return ["pt-BR-AntonioNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural"]'
    narrator_new = (
        '        return ["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", "pt-BR-ThalitaNeural", '
        '"pt-BR-BrendaNeural", "pt-BR-GiovannaNeural", "pt-BR-ThalitaMultilingualNeural"]'
    )
    male_new = (
        '        return ["pt-BR-AntonioNeural", "pt-BR-FabioNeural", "pt-BR-DonatoNeural", '
        '"pt-BR-HumbertoNeural", "pt-BR-JulioNeural", "pt-BR-NicolauNeural", '
        '"pt-BR-ValerioNeural", "pt-BR-MacerioMultilingualNeural"]'
    )

    if old_common in text:
        text = text.replace(old_common, narrator_new, 1)
    if old_common in text:
        text = text.replace(old_common, male_new, 1)

    required_markers = [
        'min_male=3, min_female=2',
        '"pt-BR-FabioNeural", "pt-BR-DonatoNeural"',
        'return ["pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"',
        f'VERSION = "{HOTFIX_VERSION}"',
    ]
    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        raise RuntimeError(f"Blindagem permanente do casting incompleta: {missing}")
    REMASTER.write_text(text, encoding="utf-8")


def patch_app_cache_buster() -> None:
    text = APP.read_text(encoding="utf-8")
    pattern = r'(assets/audio/serie-1/a1-008-n3\.mp3\?v=)[^"}]+"
    replacement = rf'\g<1>{HOTFIX_VERSION}"'
    updated, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise RuntimeError("URL do A1-008 nao localizada em app.js.")
    APP.write_text(updated, encoding="utf-8")


async def first_available(candidates: list[str], *, gender: str) -> str:
    for voice in candidates:
        if voice_gender(voice) != gender:
            raise RuntimeError(f"Candidato com genero inesperado: {voice}")
        if "Multilingual" in voice:
            continue
        if await n3.probe_voice(voice):
            return voice
    raise RuntimeError(f"Nenhuma voz {gender} PT-BR nao-multilingual disponivel.")


async def two_distinct_males() -> tuple[str, str]:
    operational: list[str] = []
    for voice in MALE_CANDIDATES:
        if "Multilingual" in voice:
            continue
        if await n3.probe_voice(voice):
            operational.append(voice)
        if len(operational) >= 2:
            break
    if len(operational) < 2:
        raise RuntimeError(f"Casting masculino insuficiente: {operational}")
    return operational[0], operational[1]


def forced_cast_factory(narrator: str, abordador: str, tentante: str):
    def force_cast(turns: list[dict], pool: list[dict]) -> dict[str, str]:
        speakers = {turn["speaker"] for turn in turns}
        expected = {"INSTRUTOR", "ABORDADOR_M", "TENTANTE_M"}
        if speakers != expected:
            raise RuntimeError(f"Locutores inesperados no A1-008: {sorted(speakers)}")
        cast = {
            "INSTRUTOR": narrator,
            "ABORDADOR_M": abordador,
            "TENTANTE_M": tentante,
        }
        if cast["ABORDADOR_M"] == cast["TENTANTE_M"]:
            raise RuntimeError("Abordador e tentante receberam a mesma voz.")
        if any("Multilingual" in voice for voice in cast.values()):
            raise RuntimeError(f"Casting multilingual proibido no A1-008: {cast}")
        if voice_gender(cast["ABORDADOR_M"]) != "M" or voice_gender(cast["TENTANTE_M"]) != "M":
            raise RuntimeError(f"Casting masculino invalido: {cast}")
        return cast

    return force_cast


def speakable_ptbr_factory(original):
    def speakable_ptbr(text: str) -> str:
        text = re.sub(r"\bhobby\b", "passatempo", text, flags=re.IGNORECASE)
        text = re.sub(r"\bMPB\b", "eme pê bê", text, flags=re.IGNORECASE)
        return original(text)

    return speakable_ptbr


async def main() -> None:
    patch_roteiro()
    patch_pronunciation_dictionary()
    patch_renderer_defaults()

    n3.TMP.mkdir(parents=True, exist_ok=True)
    narrator = await first_available(NARRATOR_CANDIDATES, gender="F")
    abordador, tentante = await two_distinct_males()

    pool = [
        {"voice": narrator, "gender": "F"},
        {"voice": abordador, "gender": "M"},
        {"voice": tentante, "gender": "M"},
    ]

    original_cast = n3.build_episode_cast
    original_speakable = n3.speakable
    n3.build_episode_cast = forced_cast_factory(narrator, abordador, tentante)
    n3.speakable = speakable_ptbr_factory(original_speakable)
    try:
        result = await n3.build_episode(EPISODE, pool, asyncio.Semaphore(1))
    finally:
        n3.build_episode_cast = original_cast
        n3.speakable = original_speakable
        shutil.rmtree(n3.TMP / f"a1-{EPISODE:03d}", ignore_errors=True)

    output = n3.OUT / result["output"]
    if not output.exists() or output.stat().st_size <= 1000:
        raise RuntimeError(f"Master A1-008 invalido: {output}")

    result["version"] = HOTFIX_VERSION
    result["hotfix_language_guard"] = True
    result["hotfix_distinct_male_cast"] = True
    result["normalized_terms"] = {"hobby": "passatempo", "MPB": "eme pê bê"}

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    episodes = report.get("episodes", [])
    replaced = False
    for idx, episode in enumerate(episodes):
        if episode.get("episode") == EPISODE:
            episodes[idx] = result
            replaced = True
            break
    if not replaced:
        raise RuntimeError("A1-008 nao encontrado em quality-n3.json")
    report["episodes"] = episodes
    report["latest_hotfix"] = {
        "episode": EPISODE,
        "version": HOTFIX_VERSION,
        "reason": "casting masculino duplicado e sonoridade estrangeira",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    patch_app_cache_buster()

    HOTFIX_REPORT.parent.mkdir(parents=True, exist_ok=True)
    HOTFIX_REPORT.write_text(
        json.dumps(
            {
                "episode": EPISODE,
                "version": HOTFIX_VERSION,
                "speaker_cast": result["speaker_cast"],
                "distinct_male_cast": result["speaker_cast"]["ABORDADOR_M"] != result["speaker_cast"]["TENTANTE_M"],
                "multilingual_forbidden": all("Multilingual" not in v for v in result["speaker_cast"].values()),
                "normalizations": result["normalized_terms"],
                "output": str(output.relative_to(n3.ROOT)),
                "duration_seconds": result["duration_seconds"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
