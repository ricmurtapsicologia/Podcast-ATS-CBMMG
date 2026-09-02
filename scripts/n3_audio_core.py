from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

SOFT_BREAK_BEFORE = {
    'mas','porém','porem','contudo','entretanto','porque','quando','enquanto','então','entao',
    'assim','agora','portanto','se','como','além','alem','ainda','inclusive','depois','antes','embora',
    'enquanto','apesar','entretanto','por isso','por outro lado'
}

QUESTION_STARTS = (
    'o que ','como ','por que ','qual ','quais ','quem ','onde ','quando ','será ','sera ',
    'você ','voce ','podemos ','pode ','consegue ','já ','ja ','e como ','e o que '
)

INSTRUCTION_STARTS = (
    'observe','imagine','pense','respire','inspire','expire','exale','perceba','note','sinta','coloque',
    'apoie','mantenha','deixe','permita','guarde','faça','faca','tente','olhe','escute','volte','leve'
)

REFLECTIVE_STARTS = (
    'talvez','por enquanto','agora','às vezes','as vezes','vale lembrar','repare','considere','pergunte-se',
    'uma possibilidade','isso pode','pode ser que','é possível','e possivel'
)

SUPPORTIVE_MARKERS = (
    'estou aqui','você não está sozinho','voce nao esta sozinho','não está sozinha','nao esta sozinha',
    'entendo que','imagino que','deve ser difícil','deve ser dificil','pode falar comigo','vamos juntos',
    'você pode','voce pode','eu te ouço','eu te ouco'
)

CONCLUSION_STARTS = (
    'em resumo','para concluir','por fim','em síntese','em sintese','o ponto principal','leve com você',
    'leve com voce','no próximo episódio','no proximo episodio','até breve','ate breve'
)

TRANSITION_STARTS = (
    'mas ','porém ','porem ','contudo ','entretanto ','por outro lado','ao mesmo tempo','além disso',
    'alem disso','depois ','antes ','agora ','então ','entao ','por isso '
)

# Dicionário aplicado somente à camada de síntese. O roteiro canônico não é alterado.
PRONUNCIATION_MAP = {
    r'\bCBMMG\b': 'C B M M G',
    r'\bATS\b': 'A T S',
    r'\bATTS\b': 'A T T S',
    r'\bPSP\b': 'P S P',
    r'\bRPD\b': 'R P D',
    r'\bTCC-I\b': 'T C C I',
    r'\bTCC\b': 'T C C',
    r'\bMPB\b': 'música popular brasileira',
    r'\bOMS\b': 'O M S',
    r'\bOPAS\b': 'O P A S',
    r'\bCATS\b': 'C A T S',
    r'\bCATTS\b': 'C A T T S',
}

@dataclass(frozen=True)
class Prosody:
    intent: str
    rate: str
    pitch: str
    pause_ms: int


def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', text or '').strip()


def lexical_tokens(text: str) -> list[str]:
    return re.findall(r'[\wÀ-ÿ]+', text.lower(), flags=re.UNICODE)


def speakable(text: str) -> str:
    """Expande apenas siglas propensas a pronúncia errada pelo TTS."""
    spoken = text
    for pattern, replacement in PRONUNCIATION_MAP.items():
        spoken = re.sub(pattern, replacement, spoken, flags=re.IGNORECASE)
    return normalize(spoken)


def stable_unit(text: str, salt: str = '') -> float:
    digest = hashlib.sha256((salt + '|' + normalize(text)).encode('utf-8')).digest()
    value = int.from_bytes(digest[:4], 'big') / 0xFFFFFFFF
    return value


def stable_int(text: str, low: int, high: int, salt: str = '') -> int:
    if high <= low:
        return low
    return low + int(round(stable_unit(text, salt) * (high - low)))


def classify_intent(text: str) -> str:
    t = normalize(text)
    low = t.lower()
    if not t:
        return 'explain'
    if any(marker in low for marker in SUPPORTIVE_MARKERS):
        return 'supportive'
    if low.startswith(CONCLUSION_STARTS):
        return 'conclusion'
    if t.endswith('?') or low.startswith(QUESTION_STARTS):
        return 'question'
    if low.startswith(INSTRUCTION_STARTS):
        return 'instruction'
    if low.startswith(REFLECTIVE_STARTS):
        return 'reflective'
    if low.startswith(TRANSITION_STARTS):
        return 'transition'
    if t.endswith('!'):
        return 'emphasis'
    return 'explain'


def breath_units(text: str, min_words: int = 9, target_words: int = 14, max_words: int = 20) -> list[str]:
    text = normalize(text)
    if not text:
        return []
    sentences = [s.strip() for s in re.split(r'(?<=[.!?…])\s+', text) if s.strip()]
    output: list[str] = []
    for sentence in sentences:
        words = sentence.split()
        if len(words) <= max_words:
            output.append(sentence)
            continue
        start = 0
        total = len(words)
        while total - start > max_words:
            low_idx = start + min_words
            high_idx = min(start + max_words, total)
            target_idx = min(start + target_words, high_idx)
            candidates = []
            for idx in range(low_idx, high_idx):
                token = re.sub(r'^[^\wÀ-ÿ]+|[^\wÀ-ÿ]+$', '', words[idx].lower())
                if token in SOFT_BREAK_BEFORE:
                    candidates.append(idx)
            cut = min(candidates, key=lambda idx: abs(idx - target_idx)) if candidates else target_idx
            if total - cut < 5:
                cut = max(low_idx, total - 6)
            unit = ' '.join(words[start:cut]).strip()
            if unit and not unit.endswith((',', ';', ':', '.', '?', '!', '…')):
                unit += ','
            output.append(unit)
            start = cut
        if start < total:
            output.append(' '.join(words[start:]).strip())
    if lexical_tokens(' '.join(output)) != lexical_tokens(text):
        raise RuntimeError('Gate lexical falhou na segmentação respiratória N3.')
    return output


def prosody(text: str, profile: str = 'clinical', role: str = 'narrator') -> Prosody:
    intent = classify_intent(text)
    if profile == 'experiential':
        base_rate, base_pitch = -9, -2
    elif profile == 'dialogue':
        base_rate, base_pitch = -3, 0
    elif profile == 'narrative':
        base_rate, base_pitch = -4, -1
    else:
        base_rate, base_pitch = -4, -1

    intent_rate = {
        'explain': 0, 'question': 1, 'instruction': -3, 'reflective': -3,
        'supportive': -3, 'transition': -1, 'conclusion': -2, 'emphasis': 1,
    }[intent]
    intent_pitch = {
        'explain': 0, 'question': 2, 'instruction': -1, 'reflective': -1,
        'supportive': -1, 'transition': 0, 'conclusion': -1, 'emphasis': 1,
    }[intent]

    role_adjust = {
        'host': (0, 0), 'narrator': (0, 0), 'professional': (-1, 0),
        'person_in_crisis': (-2, -1), 'guest': (-1, 0), 'family': (-2, -1),
    }.get(role, (0, 0))

    rate_jitter = stable_int(text, -1, 1, 'rate')
    pitch_jitter = stable_int(text, -1, 1, 'pitch')
    rate = base_rate + intent_rate + role_adjust[0] + rate_jitter
    pitch = base_pitch + intent_pitch + role_adjust[1] + pitch_jitter

    if profile == 'experiential':
        pause_ranges = {
            'instruction': (1400, 2600), 'reflective': (1100, 2100), 'supportive': (900, 1500),
            'question': (850, 1400), 'conclusion': (900, 1400), 'transition': (650, 1000),
            'emphasis': (650, 950), 'explain': (650, 1000),
        }
    elif profile == 'dialogue':
        pause_ranges = {
            'instruction': (650, 1050), 'reflective': (700, 1150), 'supportive': (750, 1250),
            'question': (450, 760), 'conclusion': (650, 1000), 'transition': (330, 560),
            'emphasis': (380, 620), 'explain': (380, 620),
        }
    else:
        pause_ranges = {
            'instruction': (750, 1200), 'reflective': (720, 1150), 'supportive': (720, 1150),
            'question': (480, 760), 'conclusion': (650, 1050), 'transition': (340, 560),
            'emphasis': (390, 650), 'explain': (390, 650),
        }

    lo, hi = pause_ranges[intent]
    pause = stable_int(text, lo, hi, 'pause')
    rate = max(-14, min(5, rate))
    pitch = max(-5, min(5, pitch))
    return Prosody(intent, f'{rate:+d}%', f'{pitch:+d}Hz', pause)
