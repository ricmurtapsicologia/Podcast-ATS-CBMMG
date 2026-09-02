from __future__ import annotations

import asyncio
import json
import re
import shutil

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

# O provedor Edge TTS, no momento, responde de forma estável com Antonio e
# Macerio para casting masculino PT-BR. Macerio é multilíngue, mas fica
# restrito ao personagem TENTANTE_M; narrador e abordador permanecem em vozes
# PT-BR não multilíngues, e o texto do episódio é normalizado para português.
MALE_CANDIDATES = [
    "pt-BR-AntonioNeural",
    "pt-BR-MacerioMultilingualNeural",
    "pt-BR-FabioNeural",
    "pt-BR-DonatoNeural",
    "pt-BR-HumbertoNeural",
    "pt-BR-JulioNeural",
    "pt-BR-NicolauNeural",
    "pt-BR-ValerioNeural",
]


def patch_roteiro() -> None:
    text = ROTEIRO.read_text(encoding="utf-8")
    text = re.sub(r"\bhobby\b", "passatempo", text, flags=re.IGNORECASE)
    text = re.sub(r"\bMPB\b", "música popular brasileira", text, flags=re.IGNORECASE)
    lowered = text.lower()
    if "hobby" in lowered or "passatempo" not in lowered:
        raise RuntimeError("Normalização de 'hobby' falhou no A1-008.")
    if "gosto de mpb" in lowered or "música popular brasileira" not in lowered:
        raise RuntimeError("Normalização de 'MPB' falhou no A1-008.")
    ROTEIRO.write_text(text, encoding="utf-8")


def patch_pronunciation_dictionary() -> None:
    text = CORE.read_text(encoding="utf-8")
    marker = "r'\\bMPB\\b': 'música popular brasileira'"
    if marker in text:
        return
    needle = "    r'\\bOMS\\b': 'O M S',"
    if needle not in text:
        raise RuntimeError("Ponto de inserção do dicionário MPB não encontrado.")
    text = text.replace(needle, "    r'\\bMPB\\b': 'música popular brasileira',\n" + needle, 1)
    CORE.write_text(text, encoding="utf-8")


def patch_renderer_defaults() -> None:
    text = REMASTER.read_text(encoding="utf-8")
    text = text.replace('VERSION = "n3-cast-20260901c"', f'VERSION = "{HOTFIX_VERSION}"')
    text = text.replace(
        "if pool_ready(operational, min_male=1, min_female=2):",
        "if pool_ready(operational, min_male=2, min_female=2):",
    )
    text = text.replace(
        "require_balanced_pool(operational, min_male=1, min_female=2)",
        "require_balanced_pool(operational, min_male=2, min_female=2)",
    )

    old_common = '        return ["pt-BR-AntonioNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural"]'
    narrator_new = (
        '        return ["pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural", "pt-BR-AntonioNeural", '
        '"pt-BR-ThalitaMultilingualNeural"]'
    )
    male_new = (
        '        return ["pt-BR-AntonioNeural", "pt-BR-MacerioMultilingualNeural", "pt-BR-FabioNeural", '
        '"pt-BR-DonatoNeural", "pt-BR-HumbertoNeural", "pt-BR-JulioNeural", '
        '"pt-BR-NicolauNeural", "pt-BR-ValerioNeural"]'
    )
    if old_common in text:
        text = text.replace(old_common, narrator_new, 1)
    if old_common in text:
        text = text.replace(old_common, male_new, 1)

    required = [
        "min_male=2, min_female=2",
        '"pt-BR-AntonioNeural", "pt-BR-MacerioMultilingualNeural"',
        'return ["pt-BR-FranciscaNeural", "pt-BR-ThalitaNeural"',
        f'VERSION = "{HOTFIX_VERSION}"',
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise RuntimeError(f"Blindagem permanente do casting incompleta: {missing}")
    REMASTER.write_text(text, encoding="utf-8")


def patch_app_cache_buster() -> None:
    text = APP.read_text(encoding="utf-8")
    old = "assets/audio/serie-1/a1-008-n3.mp3?v=n3-cast-20260901c"
    new = f"assets/audio/serie-1/a1-008-n3.mp3?v={HOTFIX_VERSION}"
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise RuntimeError("URL do A1-008 não localizada em app.js.")
    APP.write_text(text, encoding="utf-8")


async def first_available(candidates: list[str], *, gender: str) -> str:
    for voice in candidates:
        if voice_gender(voice) != gender:
            raise RuntimeError(f"Candidato com gênero inesperado: {voice}")
        if "Multilingual" in voice:
            continue
        if await n3.probe_voice(voice):
            return voice
    raise RuntimeError(f"Nenhuma voz {gender} PT-BR não multilíngue disponível.")


async def two_distinct_males() -> tuple[str, str]:
    operational: list[str] = []
    for voice in MALE_CANDIDATES:
        if voice_gender(voice) != "M":
            continue
        if await n3.probe_voice(voice):
            operational.append(voice)
        if len(operational) >= 2:
            break
    if len(operational) < 2:
        raise RuntimeError(f"Casting masculino insuficiente: {operational}")

    # O abordador deve permanecer na voz não multilíngue mais estável.
    non_multilingual = [v for v in operational if "Multilingual" not in v]
    if not non_multilingual:
        raise RuntimeError(f"Nenhuma voz masculina não multilíngue disponível: {operational}")
    abordador = non_multilingual[0]
    tentante = next((v for v in operational if v != abordador), None)
    if not tentante:
        raise RuntimeError(f"Não foi possível separar os personagens: {operational}")
    return abordador, tentante


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
        if "Multilingual" in cast["INSTRUTOR"]:
            raise RuntimeError(f"Narrador multilíngue proibido no A1-008: {cast}")
        if "Multilingual" in cast["ABORDADOR_M"]:
            raise RuntimeError(f"Abordador multilíngue proibido no A1-008: {cast}")
        if voice_gender(cast["ABORDADOR_M"]) != "M" or voice_gender(cast["TENTANTE_M"]) != "M":
            raise RuntimeError(f"Casting masculino inválido: {cast}")
        return cast

    return force_cast


def speakable_ptbr_factory(original):
    def speakable_ptbr(text: str) -> str:
        text = re.sub(r"\bhobby\b", "passatempo", text, flags=re.IGNORECASE)
        text = re.sub(r"\bMPB\b", "música popular brasileira", text, flags=re.IGNORECASE)
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
        raise RuntimeError(f"Master A1-008 inválido: {output}")

    result["version"] = HOTFIX_VERSION
    result["hotfix_language_guard"] = True
    result["hotfix_distinct_male_cast"] = True
    result["normalized_terms"] = {
        "hobby": "passatempo",
        "MPB": "música popular brasileira",
    }

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    episodes = report.get("episodes", [])
    replaced = False
    for idx, episode in enumerate(episodes):
        if episode.get("episode") == EPISODE:
            episodes[idx] = result
            replaced = True
            break
    if not replaced:
        raise RuntimeError("A1-008 não encontrado em quality-n3.json")
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
                "narrator_non_multilingual": "Multilingual" not in result["speaker_cast"]["INSTRUTOR"],
                "abordador_non_multilingual": "Multilingual" not in result["speaker_cast"]["ABORDADOR_M"],
                "normalizations": result["normalized_terms"],
                "output": str(output.relative_to(n3.ROOT)),
                "duration_seconds": result["duration_seconds"],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
