from __future__ import annotations

from collections import Counter

VOICE_GENDER = {
    "pt-BR-ThalitaMultilingualNeural": "F",
    "pt-BR-AntonioNeural": "M",
    "pt-BR-FranciscaNeural": "F",
    "pt-BR-MacerioMultilingualNeural": "M",
    "pt-BR-ThalitaNeural": "F",
    "pt-BR-FabioNeural": "M",
    "pt-BR-BrendaNeural": "F",
    "pt-BR-DonatoNeural": "M",
    "pt-BR-GiovannaNeural": "F",
}


def voice_gender(voice: str) -> str:
    try:
        return VOICE_GENDER[voice]
    except KeyError as exc:
        raise RuntimeError(f"Voz sem gênero registrado no N3: {voice}") from exc


def gender_counts(pool: list[dict]) -> Counter:
    return Counter(str(item["gender"]) for item in pool)


def pool_ready(pool: list[dict], min_male: int = 2, min_female: int = 2) -> bool:
    counts = gender_counts(pool)
    return counts["M"] >= min_male and counts["F"] >= min_female


def require_balanced_pool(pool: list[dict], min_male: int = 2, min_female: int = 2) -> None:
    if not pool_ready(pool, min_male=min_male, min_female=min_female):
        counts = gender_counts(pool)
        raise RuntimeError(
            "Pool N3 insuficiente para casting coerente: "
            f"M={counts['M']} F={counts['F']} (mínimo M={min_male}, F={min_female})."
        )
    for item in pool:
        registered = voice_gender(str(item["voice"]))
        if registered != item["gender"]:
            raise RuntimeError(
                f"Registro de gênero inconsistente: {item['voice']} manifesto={item['gender']} registro={registered}"
            )


def choose_voice(
    pool: list[dict],
    preferences: list[str],
    *,
    expected_gender: str | None = None,
    used: set[str] | None = None,
) -> str:
    available = [str(item["voice"]) for item in pool]
    used = used or set()
    eligible = [v for v in available if expected_gender is None or voice_gender(v) == expected_gender]
    if not eligible:
        raise RuntimeError(f"Nenhuma voz N3 disponível para gênero {expected_gender!r}.")
    ordered = [v for v in preferences if v in eligible] + [v for v in eligible if v not in preferences]
    return next((v for v in ordered if v not in used), ordered[0])


def assert_cast_gender(cast: dict[str, str], expected: dict[str, str | None], *, context: str = "") -> None:
    for role, voice in cast.items():
        gender = expected.get(role)
        if gender is None:
            continue
        actual = voice_gender(voice)
        if actual != gender:
            prefix = f"{context}: " if context else ""
            raise RuntimeError(f"{prefix}{role} exige voz {gender}, mas recebeu {voice} ({actual}).")


def assert_distinct_pairs(cast: dict[str, str], pairs: list[tuple[str, str]], *, context: str = "") -> None:
    for left, right in pairs:
        if left in cast and right in cast and cast[left] == cast[right]:
            prefix = f"{context}: " if context else ""
            raise RuntimeError(f"{prefix}{left} e {right} não podem compartilhar a voz {cast[left]}.")
