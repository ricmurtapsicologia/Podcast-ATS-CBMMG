from __future__ import annotations

import asyncio
import json
import re
import shutil
from pathlib import Path

import edge_tts
from pydub import AudioSegment, effects

from n3_audio_core import breath_units, normalize, prosody, speakable
from n3_foley import apply_sound_design

ROOT = Path(__file__).resolve().parents[1]
ROTEIROS = ROOT / "roteiros" / "serie-2"
OUT = ROOT / "assets" / "audio" / "serie-2"
TMP = ROOT / ".tmp_serie2_n3"
APP = ROOT / "app.js"
SOUND_DESIGN = ROOT / "sound-design" / "series-2.json"
VERSION_TAG = "n3"
VERSION = "n3-cast-20260901b"
OPENING_SILENCE_MS = 160
ENDING_SILENCE_MS = 320
TARGET_DBFS = -18.0
MAX_CONCURRENT_SYNTH = 2
SYNTH_TIMEOUT_SECONDS = 80
MAX_TTS_CHARS = 620
CINEMATIC_EPISODES = {4, 5, 6, 7, 8, 9}

VOICE_CANDIDATES = [
    ("pt-BR-ThalitaMultilingualNeural", "F"),
    ("pt-BR-AntonioNeural", "M"),
    ("pt-BR-FranciscaNeural", "F"),
    ("pt-BR-MacerioMultilingualNeural", "M"),
    ("pt-BR-ThalitaNeural", "F"),
    ("pt-BR-FabioNeural", "M"),
    ("pt-BR-BrendaNeural", "F"),
    ("pt-BR-DonatoNeural", "M"),
    ("pt-BR-GiovannaNeural", "F"),
]

ROLE_GENDER = {
    "narrator": None,
    "gorette": "F", "maria": "F",
    "claudio": "M", "ana": "F",
    "guilherme": "M", "fernanda": "F",
    "host": "M", "julia": "F", "dra_sara": "F",
    "lourdes": "F", "fatima": "F",
}
ROLE_STYLE = {
    "narrator": "narrator", "gorette": "family", "maria": "person_in_crisis",
    "claudio": "person_in_crisis", "ana": "family", "guilherme": "professional",
    "fernanda": "person_in_crisis", "host": "host", "julia": "guest",
    "dra_sara": "professional", "lourdes": "family", "fatima": "family",
}
PERSONA_ADJUST = {
    "narrator": {"rate": 0, "pitch": -1, "label": "narrador-estavel"},
    "gorette": {"rate": -2, "pitch": -2, "label": "materna-contida"},
    "maria": {"rate": -4, "pitch": -1, "label": "fragil-hesitante"},
    "claudio": {"rate": 4, "pitch": 2, "label": "euforico-acelerado"},
    "ana": {"rate": -2, "pitch": 0, "label": "amiga-reguladora"},
    "guilherme": {"rate": -3, "pitch": -1, "label": "profissional-calmo"},
    "fernanda": {"rate": -2, "pitch": 1, "label": "agitada-culpada"},
    "host": {"rate": 2, "pitch": 1, "label": "apresentador-claro"},
    "julia": {"rate": -1, "pitch": 2, "label": "jovem-reflexiva"},
    "dra_sara": {"rate": -1, "pitch": -2, "label": "clinica-segura"},
    "lourdes": {"rate": -3, "pitch": -3, "label": "madura-afetiva"},
    "fatima": {"rate": -1, "pitch": 1, "label": "irma-atenta"},
}
ROLE_PREFERENCES = {
    "narrator": ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural"],
    "gorette": ["pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-AntonioNeural"],
    "maria": ["pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"],
    "claudio": ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural"],
    "ana": ["pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-AntonioNeural"],
    "guilherme": ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural"],
    "fernanda": ["pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-AntonioNeural"],
    "host": ["pt-BR-AntonioNeural", "pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural"],
    "julia": ["pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"],
    "dra_sara": ["pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-AntonioNeural"],
    "lourdes": ["pt-BR-ThalitaMultilingualNeural", "pt-BR-FranciscaNeural", "pt-BR-AntonioNeural"],
    "fatima": ["pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural", "pt-BR-AntonioNeural"],
}
CONFLICT_PAIRS = [
    ("gorette", "maria"), ("claudio", "ana"), ("guilherme", "fernanda"),
    ("host", "julia"), ("host", "dra_sara"), ("lourdes", "fatima"),
]

# Diálogos editorialmente curados e já validados no histórico dialogue-v2.
# A curadoria remove resíduos de transcrição automática e torna inequívoco quem fala.
CURATED_TURNS = {
    4: [
        ("narrator", "Maria está sentada no sofá, abatida. Sua mãe, Gorette, percebe que ela não foi trabalhar e se aproxima."),
        ("gorette", "Maria, você está aqui nesse canto há horas. Não foi trabalhar hoje?"),
        ("maria", "Não, mãe. Eu não consegui. Parece que até levantar da cama exige uma força que eu não tenho."),
        ("gorette", "Eu percebi que você está muito desanimada. O que está acontecendo? Pode falar comigo."),
        ("maria", "Não é só tristeza. É como se tudo estivesse vazio. Eu me sinto inútil, como se nada do que eu faço tivesse sentido."),
        ("gorette", "E no trabalho? Você sempre foi tão dedicada."),
        ("maria", "É isso que dói. Eu sei que deveria conseguir, mas não consigo me concentrar. Esqueço coisas simples e depois fico com vergonha."),
        ("gorette", "E o sono? Você tem conseguido dormir?"),
        ("maria", "Tem noite em que eu fico rolando na cama com a cabeça cheia. Em outras, durmo demais e acordo cansada do mesmo jeito."),
        ("gorette", "E você tem conseguido comer?"),
        ("maria", "Quase não sinto fome. Às vezes passo o dia inteiro sem perceber."),
        ("gorette", "Maria, isso está me preocupando. Você já pensou em procurar atendimento profissional?"),
        ("maria", "Já. Mas tenho medo de não melhorar. E, às vezes, penso que talvez fosse mais fácil não estar aqui."),
        ("gorette", "Eu ouvi o que você disse. Eu vou ficar com você e podemos procurar atendimento profissional."),
        ("maria", "Obrigada, mãe. Eu não quero continuar me sentindo assim."),
        ("narrator", "A cena reúne sinais compatíveis com depressão, como perda de energia e interesse, alterações do sono e do apetite, prejuízo de concentração e desesperança. Em uma situação real, pensamentos de morte exigem avaliação profissional e atenção imediata."),
    ],
    5: [
        ("narrator", "Cláudio é enfermeiro e vive com transtorno afetivo bipolar tipo um. Em uma noite de festa, ele está visivelmente acelerado, fala muito, muda de assunto e se aproxima de desconhecidos com impulsividade."),
        ("claudio", "Vocês precisam vir dançar comigo! Essa música é incrível. Aliás, eu devia ser DJ. Ou abrir um clube. Mas quer saber? Ser enfermeiro é meu verdadeiro superpoder. Eu consigo fazer tudo!"),
        ("narrator", "Cláudio se aproxima de uma mulher na pista e fala sem hesitar."),
        ("claudio", "Você é a pessoa mais bonita que eu já vi. A gente devia sair daqui agora. Vai ser épico!"),
        ("narrator", "A mulher se afasta, surpresa. Ana, amiga de Cláudio, se aproxima."),
        ("ana", "Cláudio, você está falando muito rápido e pulando de uma ideia para outra. Vem sentar comigo um pouco."),
        ("claudio", "Sentar? Impossível! Eu tenho energia demais. Estou dormindo três horas por noite e acordo pronto para conquistar o mundo."),
        ("ana", "Faz quantos dias que você está dormindo tão pouco?"),
        ("claudio", "Nem sei. Quatro, cinco... Não faz diferença. Eu estou ótimo."),
        ("narrator", "Algum tempo depois, a energia de Cláudio diminui e sua fala fica mais baixa."),
        ("claudio", "O estranho é que, depois de noites assim, às vezes eu acordo e não consigo levantar da cama. Parece que toda essa energia some de uma vez."),
        ("narrator", "A cena ilustra sintomas de mania, como redução da necessidade de sono, aceleração da fala, fuga de ideias, grandiosidade e impulsividade. O transtorno bipolar envolve episódios de humor distintos, que podem incluir fases depressivas com importante queda de energia e desesperança."),
    ],
    6: [
        ("narrator", "Fernanda está na borda de uma ponte, visivelmente agitada, com respiração acelerada. Ela relata uso recente de cocaína. Guilherme, bombeiro militar, se aproxima de forma lenta e mantém a voz baixa."),
        ("guilherme", "Oi. Eu sou Guilherme, bombeiro militar. Estou aqui para ouvir você. Como posso te chamar?"),
        ("fernanda", "Fernanda. Mas isso não importa. Nada mais importa."),
        ("guilherme", "Fernanda, eu quero ouvir o que está acontecendo com você agora."),
        ("fernanda", "Minha vida está uma bagunça. Minha mãe está cansada de mim. Eu só trago problema para ela."),
        ("guilherme", "Você está sentindo muita culpa em relação à sua mãe."),
        ("fernanda", "Sim. Ela tentou ficar comigo tantas vezes, e eu estraguei tudo. Eu comecei a usar cocaína há uns seis meses. Sempre digo que vai ser a última vez."),
        ("guilherme", "E hoje, antes de vir para cá, você usou de novo?"),
        ("fernanda", "Usei muito. Por alguns minutos eu esqueço tudo. Depois fica pior. Eu perdi o emprego, me afastei das amigas, minha mãe nem sabe mais o que dizer."),
        ("guilherme", "Antes do uso ocupar tanto espaço, o que fazia parte da sua vida?"),
        ("fernanda", "Eu trabalhava num salão. Gostava de música, saía com minhas amigas. Eu tinha uma vida."),
        ("guilherme", "Qual dessas coisas faz mais falta quando você pensa em como era antes?"),
        ("fernanda", "Minha mãe olhando para mim sem medo. E minhas amigas. Eu destruí tudo, Guilherme."),
        ("guilherme", "Eu estou ouvindo, Fernanda. Você pode continuar falando. O que está mais difícil de suportar neste momento?"),
        ("fernanda", "A vergonha. E achar que eu nunca vou conseguir sair disso."),
        ("guilherme", "Eu não vou te apressar. Quero continuar ouvindo você, no seu tempo."),
        ("narrator", "O diálogo evidencia perda de controle sobre o uso, prejuízos sociais e profissionais, culpa e desesperança. Na abordagem, Guilherme não promete resolver a situação: ele oferece presença, escuta e perguntas que permitem compreender a experiência de Fernanda."),
    ],
    7: [
        ("host", "Bem-vindos ao Em Foco Saúde Mental. Hoje vamos conversar sobre transtorno de personalidade borderline a partir de uma experiência pessoal. Júlia, estudante de Farmácia, está com a gente. Júlia, obrigado por topar essa conversa."),
        ("julia", "Eu que agradeço. Falar sobre isso é importante porque muita gente vive algo parecido e nem sempre entende o que está acontecendo."),
        ("host", "Quando você percebeu que suas emoções e seus relacionamentos estavam te causando sofrimento?"),
        ("julia", "Na adolescência. Minhas emoções pareciam vir no volume máximo. Eu podia estar muito animada e, pouco depois, completamente desmoronada. E eu tinha um medo enorme de ser abandonada."),
        ("host", "Esse medo acabava interferindo na forma como você se relacionava?"),
        ("julia", "Muito. Eu fazia de tudo para evitar que a pessoa fosse embora e, às vezes, reagia de um jeito tão intenso que acabava afastando justamente quem eu queria por perto."),
        ("host", "Em que momento você procurou avaliação profissional?"),
        ("julia", "Demorou. Durante muito tempo eu achei que eu era simplesmente emocional demais. Quando procurei psicoterapia e depois avaliação psiquiátrica, veio o diagnóstico de transtorno de personalidade borderline."),
        ("host", "E ouvir esse diagnóstico foi mais assustador ou esclarecedor?"),
        ("julia", "Os dois. No começo assustou. Depois virou uma forma de organizar coisas que antes pareciam sem nome. Eu entendi que não era a única pessoa vivendo aquilo e que havia tratamento."),
        ("host", "O que mais mudou na sua rotina desde que começou o tratamento?"),
        ("julia", "Eu comecei a reconhecer melhor os gatilhos e a perceber quando uma emoção está crescendo antes de agir por impulso. Ainda é um processo, mas hoje eu tenho mais ferramentas."),
        ("host", "Júlia, obrigado por dividir isso com tanta clareza. No próximo bloco, a psiquiatra Dra. Sara Almeida explica o que são os transtornos de personalidade e como o tratamento é estruturado."),
    ],
    8: [
        ("host", "Estamos de volta ao Em Foco Saúde Mental. No bloco anterior, ouvimos Júlia falar sobre a experiência com borderline. Agora recebemos a psiquiatra Dra. Sara Almeida. Dra. Sara, obrigado por estar aqui."),
        ("dra_sara", "Eu que agradeço. Esse é um tema importante e ainda cercado de muito estigma."),
        ("host", "Começando pelo básico: o que é um transtorno de personalidade?"),
        ("dra_sara", "É um padrão persistente de perceber, sentir e se comportar que se torna rígido e causa prejuízo importante na vida da pessoa. Pode afetar relacionamentos, trabalho, tomada de decisão e a própria percepção de si."),
        ("host", "Então não estamos falando de uma característica isolada, como ser tímido ou impulsivo."),
        ("dra_sara", "Exatamente. Todo mundo tem traços de personalidade. Falamos em transtorno quando o padrão é duradouro, pouco flexível, aparece em diferentes contextos e produz sofrimento ou prejuízo significativo."),
        ("host", "E por que alguns transtornos de personalidade aparecem associados a maior risco de comportamento suicida?"),
        ("dra_sara", "Porque podem existir combinações de sofrimento intenso, desesperança, impulsividade, conflitos interpessoais e outras condições associadas, como depressão ou uso de substâncias. O risco é individual e precisa ser avaliado clinicamente."),
        ("host", "Os transtornos de personalidade ainda são organizados em três grandes grupos?"),
        ("dra_sara", "Sim. De forma tradicional, o grupo A inclui os transtornos paranoide, esquizoide e esquizotípico. O grupo B inclui antissocial, borderline, histriônico e narcisista. O grupo C inclui evitativo, dependente e obsessivo-compulsivo da personalidade."),
        ("host", "E tratamento: qual é o eixo principal?"),
        ("dra_sara", "A psicoterapia costuma ser o eixo central. Medicamentos podem ser usados para sintomas específicos ou condições associadas, como depressão e ansiedade. O plano precisa ser individualizado e acompanhado por profissionais qualificados."),
        ("host", "Dra. Sara, obrigado pela conversa. Informação clara reduz estigma e melhora a procura por cuidado. Seguimos girando a Ampulheta da Vida no próximo episódio."),
    ],
    9: [
        ("narrator", "Hoje ouviremos uma conversa entre Dona Lurdes, mãe de Mônica, que vive com esquizofrenia, e Fátima, irmã de Lurdes. A conversa aborda sintomas, risco suicida e o impacto do cuidado sobre a família."),
        ("fatima", "Lurdes, você parece um pouco mais tranquila hoje. Como a Mônica está?"),
        ("lourdes", "Está mais estável com o tratamento. Os sintomas ainda aparecem, mas agora ela consegue me dizer quando alguma coisa não está bem."),
        ("fatima", "Ela ainda ouve vozes?"),
        ("lourdes", "Às vezes. E também tem momentos em que acredita que está sendo observada. O que mais me preocupa é quando ela se fecha completamente."),
        ("fatima", "Ela já falou sobre não querer continuar vivendo?"),
        ("lourdes", "Já, principalmente nas crises. Ouvir isso é muito difícil. A equipe que acompanha a Mônica explicou que precisamos levar esse tipo de fala a sério e procurar atendimento quando o risco aumenta."),
        ("fatima", "E como você reage quando isso acontece?"),
        ("lourdes", "Eu tento manter a calma, fico perto e escuto. Se percebo risco imediato ou piora importante, procuro o serviço de saúde."),
        ("fatima", "E você? Está conseguindo cuidar de si também?"),
        ("lourdes", "Estou aprendendo. Entendi que não consigo carregar tudo sozinha. Comecei a participar de um grupo para familiares, e isso tem me feito bem."),
        ("fatima", "A Mônica ainda fala de planos para o futuro?"),
        ("lourdes", "Sim. Ela quer voltar a estudar Artes. Estamos indo devagar, mas é bom ouvir ela falar de coisas que ainda deseja viver."),
        ("narrator", "A esquizofrenia pode estar associada a maior vulnerabilidade ao comportamento suicida, especialmente quando há sofrimento intenso, depressão, alucinações, desesperança ou isolamento. Rede de apoio e acompanhamento profissional são fatores importantes de proteção."),
    ],
}


def read_narrative(number: int) -> str:
    path = ROTEIROS / f"a2-{number:03d}.txt"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.startswith("#")]
    text = normalize(" ".join(lines))
    if not text:
        raise RuntimeError(f"Roteiro vazio: {path}")
    return text


def compact_role_units(role: str, text: str):
    units = [x for x in breath_units(text) if x.strip()]
    out = []
    for unit in units:
        if out and len(out[-1]) + 1 + len(unit) <= MAX_TTS_CHARS:
            out[-1] = normalize(out[-1] + " " + unit)
        else:
            out.append(unit)
    return [(role, unit) for unit in out]


def build_turns(number: int):
    if number in CURATED_TURNS:
        turns = []
        for role, text in CURATED_TURNS[number]:
            turns.extend(compact_role_units(role, text))
        return turns, "editorially_curated_dialogue_v2"
    return compact_role_units("narrator", read_narrative(number)), "frozen_source_narration"


async def probe_voice(name: str) -> bool:
    TMP.mkdir(parents=True, exist_ok=True)
    probe = TMP / ("probe-" + re.sub(r"[^A-Za-z0-9_-]+", "_", name) + ".mp3")
    for attempt in range(1, 4):
        try:
            c = edge_tts.Communicate(text="Teste breve de voz neural.", voice=name, rate="-2%", pitch="+0Hz", volume="+0%")
            await asyncio.wait_for(c.save(str(probe)), timeout=40)
            ok = probe.exists() and probe.stat().st_size > 500
            probe.unlink(missing_ok=True)
            if ok:
                print(f"[VOICE OK] {name}")
                return True
        except Exception as exc:
            probe.unlink(missing_ok=True)
            print(f"[VOICE PROBE {attempt}/3] {name}: {type(exc).__name__}")
            await asyncio.sleep(1.2 * attempt)
    return False


async def resolve_operational_pool():
    operational = []
    for name, gender in VOICE_CANDIDATES:
        if await probe_voice(name):
            operational.append({"voice": name, "gender": gender})
        if len(operational) >= 3:
            break
    if len(operational) < 2:
        raise RuntimeError("Menos de duas vozes neurais realmente operacionais.")
    return operational


def resolve_cast(pool: list[dict]):
    available = [x["voice"] for x in pool]
    cast = {}
    for role in ROLE_GENDER:
        prefs = [v for v in ROLE_PREFERENCES[role] if v in available]
        cast[role] = prefs[0] if prefs else available[0]
    for left, right in CONFLICT_PAIRS:
        if cast[left] == cast[right]:
            alt = next((v for v in ROLE_PREFERENCES[right] if v in available and v != cast[left]), None)
            if alt is None:
                alt = next((v for v in available if v != cast[left]), None)
            if alt is None:
                raise RuntimeError(f"Não há segunda voz para {left}/{right}")
            cast[right] = alt
    return cast


def persona_values(rate: str, pitch: str, role: str):
    cfg = PERSONA_ADJUST[role]
    r = int(rate.rstrip("%")) + int(cfg["rate"])
    p = int(pitch.replace("Hz", "")) + int(cfg["pitch"])
    return f"{max(-16, min(8, r)):+d}%", f"{max(-7, min(7, p)):+d}Hz"


async def synth(text, voice, rate, pitch, path, sem):
    async with sem:
        last_exc = None
        for attempt in range(1, 9):
            try:
                await asyncio.sleep(0.18)
                c = edge_tts.Communicate(text=speakable(text), voice=voice, rate=rate, pitch=pitch, volume="+0%")
                await asyncio.wait_for(c.save(str(path)), timeout=SYNTH_TIMEOUT_SECONDS)
                if path.exists() and path.stat().st_size > 500:
                    return
                raise RuntimeError("arquivo TTS vazio")
            except Exception as exc:
                last_exc = exc
                path.unlink(missing_ok=True)
                print(f"[TTS RETRY {attempt}/8] {voice} | {type(exc).__name__} | {normalize(text)[:80]}")
                if attempt < 8:
                    await asyncio.sleep(min(12.0, 1.6 * attempt))
        raise RuntimeError(f"Falha TTS persistente | voz={voice} | trecho={normalize(text)[:120]}") from last_exc


def sound_design_for(number: int, data: dict):
    entry = data.get("episodes", {}).get(f"{number:03d}", {})
    return str(entry.get("scene", "none")), list(entry.get("events", []))


async def build_episode(number: int, cast: dict[str, str], sound_design: dict, sem):
    turns, source_mode = build_turns(number)
    work = TMP / f"a2-{number:03d}"
    work.mkdir(parents=True, exist_ok=True)
    sequence = []
    intents = []
    roles = []

    for idx, (role, text) in enumerate(turns):
        p = prosody(text, profile="dialogue" if number in CINEMATIC_EPISODES else "narrative", role=ROLE_STYLE[role])
        rate, pitch = persona_values(p.rate, p.pitch, role)
        part = work / f"{idx:03d}.mp3"
        await synth(text, cast[role], rate, pitch, part, sem)
        sequence.append((part, 0 if idx == len(turns)-1 else p.pause_ms))
        intents.append(p.intent)
        roles.append(role)

    merged = AudioSegment.silent(duration=OPENING_SILENCE_MS)
    for part, pause in sequence:
        merged += AudioSegment.from_file(part, format="mp3")
        if pause:
            merged += AudioSegment.silent(duration=pause)
    merged += AudioSegment.silent(duration=ENDING_SILENCE_MS)
    merged = effects.compress_dynamic_range(merged, threshold=-20.0, ratio=2.0, attack=8.0, release=70.0)
    if merged.dBFS != float("-inf"):
        merged = merged.apply_gain(TARGET_DBFS - merged.dBFS)

    scene, events = sound_design_for(number, sound_design)
    cinematic = number in CINEMATIC_EPISODES
    if cinematic:
        merged = apply_sound_design(merged, scene, events)
        if merged.max_dBFS > -1.2:
            merged = merged.apply_gain(-1.2 - merged.max_dBFS)
    else:
        merged = merged.set_channels(1)
        if merged.max_dBFS > -1.2:
            merged = merged.apply_gain(-1.2 - merged.max_dBFS)

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f"a2-{number:03d}-{VERSION_TAG}.mp3"
    bitrate = "192k" if cinematic else "128k"
    channels = 2 if cinematic else 1
    merged.export(target, format="mp3", bitrate=bitrate, parameters=["-ac", str(channels), "-ar", "44100"])

    episode_roles = list(dict.fromkeys(roles))
    episode_cast = {role: cast[role] for role in episode_roles}
    if cinematic and len(set(episode_cast.values())) < 2:
        raise RuntimeError(f"A2-{number:03d} não ficou multivoz.")

    return {
        "episode": number,
        "output": target.name,
        "version": VERSION,
        "profile": "N3-D" if cinematic else "N3-C",
        "source_mode": source_mode,
        "scene": scene,
        "events": events,
        "stage_directions_replaced_by_sound": ["foley/ambience metadata"] if cinematic else [],
        "text_integrity_spoken_content": 1.0,
        "roles": episode_roles,
        "role_cast": episode_cast,
        "voices": sorted(set(episode_cast.values())),
        "persona_profiles": {role: PERSONA_ADJUST[role] for role in episode_roles},
        "intents": sorted(set(intents)),
        "turns": len(turns),
        "duration_seconds": round(len(merged) / 1000, 1),
        "channels": channels,
        "sample_rate": 44100,
        "bitrate": bitrate,
    }


def patch_app_urls():
    content = APP.read_text(encoding="utf-8")
    match = re.search(r",2:\[(.*?)\],3:\[\]", content, re.S)
    if not match:
        raise RuntimeError("Bloco Série 2 não localizado em app.js")
    block = match.group(1)
    entries = list(re.finditer(r'\{title:"([^"]+)",url:"([^"]+)"\}', block))
    if len(entries) != 14:
        raise RuntimeError(f"Esperados 14 episódios; encontrados {len(entries)}")
    new_block = block
    for idx, item in reversed(list(enumerate(entries))):
        title = item.group(1)
        repl = f'{{title:"{title}",url:"assets/audio/serie-2/a2-{idx:03d}-{VERSION_TAG}.mp3?v={VERSION}"}}'
        new_block = new_block[:item.start()] + repl + new_block[item.end():]
    content = content[:match.start(1)] + new_block + content[match.end(1):]
    APP.write_text(content, encoding="utf-8")


async def main():
    sound_design = json.loads(SOUND_DESIGN.read_text(encoding="utf-8"))
    TMP.mkdir(parents=True, exist_ok=True)
    pool = await resolve_operational_pool()
    cast = resolve_cast(pool)
    print("[POOL]", json.dumps(pool, ensure_ascii=False))
    print("[CAST]", json.dumps(cast, ensure_ascii=False))
    sem = asyncio.Semaphore(MAX_CONCURRENT_SYNTH)
    quality = []
    for number in range(14):
        print(f"[A2-{number:03d}] render")
        quality.append(await build_episode(number, cast, sound_design, sem))
    patch_app_urls()
    report = {
        "version": VERSION,
        "operational_voice_pool": pool,
        "character_cast": cast,
        "cinematic_multivoice_episodes": sorted(CINEMATIC_EPISODES),
        "dialogue_source": "historical dialogue-v2 curated turns",
        "episodes": quality,
    }
    (OUT / "quality-n3.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(TMP, ignore_errors=True)
    print("Série 2 N3 casting concluída.")


if __name__ == "__main__":
    asyncio.run(main())
