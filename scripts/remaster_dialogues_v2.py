from __future__ import annotations

"""Remasterização editorial v2 dos diálogos das Séries 1 e 2.

Regras desta versão:
- falas curadas manualmente para legibilidade e naturalidade;
- apenas episódios que contêm conversa real recebem múltiplas vozes;
- no A1, o abordador fala de forma profissional, regulada e não confrontativa;
- o tentante mantém emoção compatível com a cena (depressiva, agressiva ou psicótica);
- A2 007/008 têm ritmo de podcast, com turnos mais curtos e transições naturais;
- A2 005 usa narrador perceptivelmente diferente de Cláudio;
- em A2 006 o bombeiro oferece presença e escuta, sem prometer "ajudar";
- arquivos anteriores permanecem intactos para rollback;
- app.js só é atualizado depois de todos os gates automáticos.
"""

import asyncio
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import edge_tts
from pydub import AudioSegment, effects

ROOT = Path(__file__).resolve().parents[1]
OUT1 = ROOT / "assets" / "audio" / "serie-1"
OUT2 = ROOT / "assets" / "audio" / "serie-2"
TMP = ROOT / ".tmp_dialogues_v2"
APP = ROOT / "app.js"

VERSION = "dialogue-v2"
TARGET_LUFS = -18.0
TRUE_PEAK = -1.5
MAX_CONCURRENT = 4
TIMEOUT = 70

ANTONIO = "pt-BR-AntonioNeural"
FRANCISCA = "pt-BR-FranciscaNeural"
THALITA = "pt-BR-ThalitaMultilingualNeural"


@dataclass(frozen=True)
class Voice:
    model: str
    rate: int
    pitch: int
    style: str


# Texto editorialmente curado. Cada episódio preserva o objetivo pedagógico,
# mas corrige erros de transcrição e separa locutores de modo explícito.
EPISODES: dict[str, dict] = {
    "a1-008": {
        "series": 1,
        "title": "Usando Perguntas Simples com Tentante de Perfil Depressivo",
        "voices": {
            "NARRADOR": Voice(FRANCISCA, -5, 0, "didático-discreto"),
            "ABORDADORA": Voice(THALITA, -5, -1, "profissional-calma"),
            "TENTANTE": Voice(ANTONIO, -8, -2, "abatido-hesitante"),
        },
        "interlocutors": ("ABORDADORA", "TENTANTE"),
        "turns": [
            ("NARRADOR", "Usando perguntas simples com um tentante de perfil depressivo. Nesta ocorrência, um homem está sentado na borda de um viaduto, com o olhar baixo, demonstrando tristeza e cansaço. A abordadora se aproxima com calma e respeita o silêncio inicial."),
            ("ABORDADORA", "Oi. Meu nome é Ana, sou bombeira militar. Estou aqui para ouvir você. Como posso te chamar?"),
            ("TENTANTE", "Rafael."),
            ("ABORDADORA", "Rafael, você mora com alguém ou está sozinho em casa?"),
            ("TENTANTE", "Moro com a minha mãe. Ela tenta ficar perto, mas eu não quero preocupar ninguém."),
            ("ABORDADORA", "Parece que sua mãe é importante para você. Tem mais alguém com quem costumava conversar?"),
            ("TENTANTE", "Não muito. Antes eu falava com alguns colegas. Agora eu me afastei de todo mundo."),
            ("ABORDADORA", "E quando você estava um pouco melhor, tinha algo de que gostava? Música, desenho, algum lugar, alguma rotina?"),
            ("TENTANTE", "Eu desenhava. E ouvia MPB. Faz tempo que não faço nenhuma das duas coisas."),
            ("ABORDADORA", "O que você costumava desenhar?"),
            ("TENTANTE", "Pessoas. Lugares. Era uma forma de desligar a cabeça por um tempo."),
            ("ABORDADORA", "Entendi. E sobre o trabalho, como as coisas ficaram nos últimos meses?"),
            ("TENTANTE", "Perdi o emprego. Depois disso parece que eu fui apagando. Não tenho força para começar de novo."),
            ("ABORDADORA", "Eu estou ouvindo. O que ficou mais pesado para você desde que perdeu o emprego?"),
            ("TENTANTE", "A sensação de que eu fracassei. E de que não vou conseguir sair disso."),
            ("NARRADOR", "As perguntas simples permitem conhecer vínculos, rotina, perdas, interesses e fatores de proteção sem transformar a conversa em interrogatório. O abordador pergunta com naturalidade e, principalmente, escuta as respostas."),
        ],
    },
    "a1-009": {
        "series": 1,
        "title": "Usando Perguntas Simples com Tentante de Perfil Agressivo",
        "voices": {
            "NARRADOR": Voice(ANTONIO, -5, -1, "didático-discreto"),
            "ABORDADORA": Voice(FRANCISCA, -5, 0, "profissional-firme-calma"),
            "TENTANTE": Voice(THALITA, 1, 1, "irritada-emocional"),
        },
        "interlocutors": ("ABORDADORA", "TENTANTE"),
        "turns": [
            ("NARRADOR", "Usando perguntas simples com uma tentante de perfil agressivo. Uma mulher está no terraço de um prédio, andando de um lado para o outro, gesticulando e falando em tom elevado. A abordadora mantém distância e não reage às provocações."),
            ("ABORDADORA", "Oi. Meu nome é Ana, sou bombeira militar. Estou aqui para ouvir você. Como posso te chamar?"),
            ("TENTANTE", "Eu não quero falar com ninguém!"),
            ("ABORDADORA", "Tudo bem. Eu não vou te pressionar. Posso permanecer aqui enquanto você decide se quer falar?"),
            ("TENTANTE", "Faz o que quiser. Ninguém se importa mesmo."),
            ("ABORDADORA", "Isso parece estar doendo muito. O que aconteceu hoje para você chegar até aqui?"),
            ("TENTANTE", "Minha irmã gritou comigo de novo. Meu chefe me trata como lixo. Eu estou cansada de todo mundo."),
            ("ABORDADORA", "Você está carregando conflitos em casa e no trabalho ao mesmo tempo."),
            ("TENTANTE", "Sim! E todo mundo acha que eu tenho que aguentar calada."),
            ("ABORDADORA", "Antes de hoje, havia alguma coisa que diminuía um pouco essa tensão?"),
            ("TENTANTE", "Eu fazia academia. Às vezes ouvia música. Mas parei com tudo."),
            ("ABORDADORA", "Qual música você costumava ouvir quando precisava ficar sozinha?"),
            ("TENTANTE", "Rock. Bem alto. Era a única hora em que eu sentia que ninguém estava mandando em mim."),
            ("ABORDADORA", "Entendi. Quero continuar ouvindo o que está acontecendo com você. O que mais está pesando agora?"),
            ("NARRADOR", "Com um tentante agressivo, o abordador reduz o próprio tom de voz, oferece espaço e evita disputar controle. Perguntas simples podem transformar hostilidade em narrativa, permitindo que a pessoa expresse o que está por trás da raiva."),
        ],
    },
    "a1-010": {
        "series": 1,
        "title": "Usando Perguntas Simples com Tentante de Perfil Psicótico",
        "voices": {
            "NARRADOR": Voice(FRANCISCA, -5, 0, "didático-discreto"),
            "ABORDADOR": Voice(ANTONIO, -5, -1, "profissional-calmo"),
            "TENTANTE": Voice(THALITA, -1, 1, "desconfiada-oscilante"),
        },
        "interlocutors": ("ABORDADOR", "TENTANTE"),
        "turns": [
            ("NARRADOR", "Usando perguntas simples com uma tentante de perfil psicótico. Janaína está sentada no parapeito de uma ponte, segurando uma mochila contra o peito e falando sobre uma missão. O abordador evita confrontar diretamente sua percepção da realidade."),
            ("ABORDADOR", "Oi. Meu nome é João, sou bombeiro militar. Estou aqui para ouvir você. Como posso te chamar?"),
            ("TENTANTE", "Janaína. Mas eles me chamam de Comandante das Estrelas."),
            ("ABORDADOR", "Janaína, para você essa missão é muito importante. Você me permite ficar aqui e ouvir como ela começou?"),
            ("TENTANTE", "Talvez. Depende se você está aqui para atrapalhar."),
            ("ABORDADOR", "Eu quero entender o que você está vivendo. Como você chegou até esta ponte hoje?"),
            ("TENTANTE", "As vozes me trouxeram. Elas disseram que eu precisava vir."),
            ("ABORDADOR", "Essas vozes estão falando com você agora?"),
            ("TENTANTE", "Estão. Mas estão confusas. Algumas mandam uma coisa, outras mandam outra."),
            ("ABORDADOR", "E quando as vozes ficam assim, existe alguma coisa que costuma deixá-las menos intensas?"),
            ("TENTANTE", "Às vezes eu canto. Ou desenho mapas das estrelas."),
            ("ABORDADOR", "Que tipo de mapa você gosta de desenhar?"),
            ("TENTANTE", "Os caminhos que eu vejo no céu. Ninguém entende, mas eu entendo."),
            ("ABORDADOR", "Eu estou ouvindo. O que você gostaria que eu entendesse sobre esses caminhos?"),
            ("NARRADOR", "A abordagem não valida nem ridiculariza o delírio. O profissional demonstra interesse pela experiência subjetiva, faz perguntas claras e mantém a conversa ancorada no presente."),
        ],
    },
    "a1-011": {
        "series": 1,
        "title": "Usando Perguntas Complexas para Apoiar o Tentante",
        "voices": {
            "NARRADOR": Voice(FRANCISCA, -5, 0, "didático-discreto"),
            "ABORDADOR": Voice(ANTONIO, -5, -1, "profissional-reflexivo"),
            "TENTANTE": Voice(THALITA, -5, 0, "angustiada-aberta"),
        },
        "interlocutors": ("ABORDADOR", "TENTANTE"),
        "turns": [
            ("NARRADOR", "Perguntas complexas são usadas quando já existe algum vínculo e a pessoa demonstra disposição para falar com mais profundidade. Nesta cena, Athena está no parapeito de um prédio após uma longa ocorrência."),
            ("ABORDADOR", "Athena, o que aconteceu para que hoje parecesse impossível continuar?"),
            ("TENTANTE", "Parece que tudo desmoronou junto. Eu perdi o emprego há dois meses. Meu chefe dizia que eu nunca era boa o suficiente e, depois que fui demitida, comecei a acreditar nisso. Minha mãe tenta conversar, mas parece que ninguém entende. Ontem o banco ligou cobrando uma dívida e eu só pensei que não aguentava mais."),
            ("ABORDADOR", "Você está lidando com perda, cobrança e uma sensação muito forte de fracasso. Como é colocar isso em palavras agora?"),
            ("TENTANTE", "Dói. Mas é diferente de ficar repetindo tudo sozinha na minha cabeça."),
            ("ABORDADOR", "O que você gostaria que alguém entendesse sobre o que está vivendo, sem tentar resolver por você?"),
            ("TENTANTE", "Que eu estou cansada. Que não é preguiça. Eu só não sei mais por onde começar."),
            ("NARRADOR", "Perguntas complexas dão espaço para respostas amplas. O objetivo é compreender a cadeia de acontecimentos, significados e emoções, sem transformar a escuta em aconselhamento precoce."),
        ],
    },
    "a1-013": {
        "series": 1,
        "title": "Técnica do Sucesso Anterior",
        "voices": {
            "NARRADOR": Voice(ANTONIO, -5, -1, "didático-discreto"),
            "ABORDADORA": Voice(FRANCISCA, -5, 0, "profissional-reflexiva"),
            "TENTANTE": Voice(THALITA, -6, -1, "cansado-reflexivo"),
        },
        "interlocutors": ("ABORDADORA", "TENTANTE"),
        "turns": [
            ("NARRADOR", "Técnica do sucesso anterior. Carlos está à beira de uma ponte e relata que a perda recente do emprego foi o principal precipitante da crise. A abordadora busca lembranças concretas de enfrentamento, sem minimizar o sofrimento atual."),
            ("ABORDADORA", "Carlos, você disse que esta não foi a primeira vez que perdeu um emprego. O que aconteceu da outra vez?"),
            ("TENTANTE", "Foi ruim também. Eu achei que não ia conseguir, mas depois de um tempo consegui outro trabalho."),
            ("ABORDADORA", "O que você fez naquele período que aumentou suas chances de conseguir?"),
            ("TENTANTE", "Eu mandei muitos currículos. E um amigo, o Pedro, me indicou para uma vaga."),
            ("ABORDADORA", "Então você procurou oportunidades e aceitou apoio de alguém em quem confiava."),
            ("TENTANTE", "Sim. Só que agora parece diferente. Parece muito maior."),
            ("ABORDADORA", "Eu entendo que hoje pareça maior. Daquilo que funcionou antes, existe alguma parte que ainda faria sentido tentar novamente?"),
            ("TENTANTE", "Talvez falar com o Pedro. Eu me afastei, mas acho que ele atenderia."),
            ("NARRADOR", "A técnica não afirma que o problema atual é igual ao passado. Ela recupera estratégias já utilizadas e devolve ao tentante a percepção de que existem ações possíveis, construídas a partir da própria história."),
        ],
    },
    "a1-014": {
        "series": 1,
        "title": "Ponte para o Passado",
        "voices": {
            "NARRADOR": Voice(FRANCISCA, -5, 0, "didático-discreto"),
            "ABORDADOR": Voice(ANTONIO, -5, -1, "profissional-suave"),
            "TENTANTE": Voice(THALITA, -5, 0, "emocionada-nostálgica"),
        },
        "interlocutors": ("ABORDADOR", "TENTANTE"),
        "turns": [
            ("NARRADOR", "Ponte para o passado. Larissa segura um colar dado pelo avô e demonstra forte emoção. O abordador percebe que o objeto está ligado a uma memória afetiva e explora essa lembrança com perguntas sensoriais."),
            ("ABORDADOR", "Larissa, esse colar parece muito importante. Qual é a história dele?"),
            ("TENTANTE", "Meu avô me deu. Foi na varanda da casa dele. A gente estava tomando café."),
            ("ABORDADOR", "O que você lembra daquela varanda?"),
            ("TENTANTE", "Tinha uma rede branca, muitas plantas e cheiro de flor. Ele colocava milho para os pássaros."),
            ("ABORDADOR", "E como você se sentia quando estava ali com ele?"),
            ("TENTANTE", "Tranquila. Protegida. Era como se o mundo ficasse mais devagar."),
            ("ABORDADOR", "Quando ele entregou o colar, disse alguma coisa?"),
            ("TENTANTE", "Disse que eu era forte e que queria que eu lembrasse dele quando as coisas ficassem difíceis."),
            ("ABORDADOR", "Quando você toca nesse colar agora, qual parte daquele momento aparece primeiro?"),
            ("TENTANTE", "A voz dele. E a sensação de paz."),
            ("NARRADOR", "A ponte para o passado utiliza memórias significativas para ampliar o campo emocional e atencional. O abordador não impõe uma interpretação; ele acompanha o que a própria pessoa reconhece como significativo."),
        ],
    },
    "a1-015": {
        "series": 1,
        "title": "Ponte para o Futuro",
        "voices": {
            "NARRADOR": Voice(ANTONIO, -5, -1, "didático-discreto"),
            "ABORDADORA": Voice(FRANCISCA, -5, 0, "profissional-curiosa"),
            "TENTANTE": Voice(THALITA, -5, -1, "cansado-com-pequena-abertura"),
        },
        "interlocutors": ("ABORDADORA", "TENTANTE"),
        "turns": [
            ("NARRADOR", "Ponte para o futuro. Daniel relata que cozinhar para os amigos era uma das poucas atividades que ainda lhe dava prazer. A abordadora usa esse tema para explorar uma cena futura concreta, sem prometer que tudo ficará bem."),
            ("ABORDADORA", "Daniel, você falou do jantar que fez na semana passada. O que você cozinhou?"),
            ("TENTANTE", "Lasanha. Meus amigos gostam."),
            ("ABORDADORA", "Se vocês se encontrassem de novo no próximo sábado, o que provavelmente aconteceria primeiro?"),
            ("TENTANTE", "Eu compraria queijo, massa, molho. Eles sempre aparecem com sobremesa."),
            ("ABORDADORA", "E depois que a comida fica pronta?"),
            ("TENTANTE", "A gente coloca tudo na bancada. Cada um se serve. Depois ficamos conversando."),
            ("ABORDADORA", "Como você costuma se sentir quando a casa está cheia e vocês estão conversando depois do jantar?"),
            ("TENTANTE", "Feliz. É uma das poucas horas em que eu paro de pensar em tudo."),
            ("ABORDADORA", "Quando você imagina essa cena agora, o que muda, mesmo que seja pouco, no que está sentindo?"),
            ("TENTANTE", "Dá uma dúvida. Uma parte de mim pensa que talvez eu ainda quisesse viver isso de novo."),
            ("NARRADOR", "A ponte para o futuro explora possibilidades concretas e emocionalmente significativas. O objetivo é ampliar a percepção de futuro e introduzir alternativas ao estreitamento provocado pela crise."),
        ],
    },
    "a2-004": {
        "series": 2,
        "title": "Maria e as Sombras da Depressão",
        "voices": {
            "NARRADOR": Voice(ANTONIO, -5, -1, "narrador-discreto"),
            "MARIA": Voice(THALITA, -7, -1, "jovem-abatida"),
            "GORETTE": Voice(FRANCISCA, -4, 0, "mãe-preocupada"),
        },
        "interlocutors": ("MARIA", "GORETTE"),
        "turns": [
            ("NARRADOR", "Maria está sentada no sofá, abatida. Sua mãe, Gorette, percebe que ela não foi trabalhar e se aproxima."),
            ("GORETTE", "Maria, você está aqui nesse canto há horas. Não foi trabalhar hoje?"),
            ("MARIA", "Não, mãe. Eu não consegui. Parece que até levantar da cama exige uma força que eu não tenho."),
            ("GORETTE", "Eu percebi que você está muito desanimada. O que está acontecendo? Pode falar comigo."),
            ("MARIA", "Não é só tristeza. É como se tudo estivesse vazio. Eu me sinto inútil, como se nada do que eu faço tivesse sentido."),
            ("GORETTE", "E no trabalho? Você sempre foi tão dedicada."),
            ("MARIA", "É isso que dói. Eu sei que deveria conseguir, mas não consigo me concentrar. Esqueço coisas simples e depois fico com vergonha."),
            ("GORETTE", "E o sono? Você tem conseguido dormir?"),
            ("MARIA", "Tem noite em que eu fico rolando na cama com a cabeça cheia. Em outras, durmo demais e acordo cansada do mesmo jeito."),
            ("GORETTE", "E você tem conseguido comer?"),
            ("MARIA", "Quase não sinto fome. Às vezes passo o dia inteiro sem perceber."),
            ("GORETTE", "Maria, isso está me preocupando. Você já pensou em procurar atendimento profissional?"),
            ("MARIA", "Já. Mas tenho medo de não melhorar. E, às vezes, penso que talvez fosse mais fácil não estar aqui."),
            ("GORETTE", "Eu ouvi o que você disse. Eu vou ficar com você e podemos procurar atendimento profissional."),
            ("MARIA", "Obrigada, mãe. Eu não quero continuar me sentindo assim."),
            ("NARRADOR", "A cena reúne sinais compatíveis com depressão, como perda de energia e interesse, alterações do sono e do apetite, prejuízo de concentração e desesperança. Em uma situação real, pensamentos de morte exigem avaliação profissional e atenção imediata."),
        ],
    },
    "a2-005": {
        "series": 2,
        "title": "Cláudio e os Ciclos da Bipolaridade",
        "voices": {
            "NARRADOR": Voice(THALITA, -5, 0, "narradora-discreta"),
            "CLAUDIO": Voice(ANTONIO, 3, 2, "eufórico-acelerado"),
            "ANA": Voice(FRANCISCA, -4, 0, "amiga-reguladora"),
        },
        "interlocutors": ("CLAUDIO", "ANA"),
        "turns": [
            ("NARRADOR", "Cláudio é enfermeiro e vive com transtorno afetivo bipolar tipo um. Em uma noite de festa, ele está visivelmente acelerado, fala muito, muda de assunto e se aproxima de desconhecidos com impulsividade."),
            ("CLAUDIO", "Vocês precisam vir dançar comigo! Essa música é incrível. Aliás, eu devia ser DJ. Ou abrir um clube. Mas quer saber? Ser enfermeiro é meu verdadeiro superpoder. Eu consigo fazer tudo!"),
            ("NARRADOR", "Cláudio se aproxima de uma mulher na pista e fala sem hesitar."),
            ("CLAUDIO", "Você é a pessoa mais bonita que eu já vi. A gente devia sair daqui agora. Vai ser épico!"),
            ("NARRADOR", "A mulher se afasta, surpresa. Ana, amiga de Cláudio, se aproxima."),
            ("ANA", "Cláudio, você está falando muito rápido e pulando de uma ideia para outra. Vem sentar comigo um pouco."),
            ("CLAUDIO", "Sentar? Impossível! Eu tenho energia demais. Estou dormindo três horas por noite e acordo pronto para conquistar o mundo."),
            ("ANA", "Faz quantos dias que você está dormindo tão pouco?"),
            ("CLAUDIO", "Nem sei. Quatro, cinco... Não faz diferença. Eu estou ótimo."),
            ("NARRADOR", "Algum tempo depois, a energia de Cláudio diminui e sua fala fica mais baixa."),
            ("CLAUDIO", "O estranho é que, depois de noites assim, às vezes eu acordo e não consigo levantar da cama. Parece que toda essa energia some de uma vez."),
            ("NARRADOR", "A cena ilustra sintomas de mania, como redução da necessidade de sono, aceleração da fala, fuga de ideias, grandiosidade e impulsividade. O transtorno bipolar envolve episódios de humor distintos, que podem incluir fases depressivas com importante queda de energia e desesperança."),
        ],
    },
    "a2-006": {
        "series": 2,
        "title": "Fernanda e o Labirinto da Cocaína",
        "voices": {
            "NARRADOR": Voice(FRANCISCA, -5, 0, "narradora-discreta"),
            "GUILHERME": Voice(ANTONIO, -6, -1, "bombeiro-profissional-calmo"),
            "FERNANDA": Voice(THALITA, -1, 1, "agitada-culpada"),
        },
        "interlocutors": ("GUILHERME", "FERNANDA"),
        "turns": [
            ("NARRADOR", "Fernanda está na borda de uma ponte, visivelmente agitada, com respiração acelerada. Ela relata uso recente de cocaína. Guilherme, bombeiro militar, se aproxima de forma lenta e mantém a voz baixa."),
            ("GUILHERME", "Oi. Eu sou Guilherme, bombeiro militar. Estou aqui para ouvir você. Como posso te chamar?"),
            ("FERNANDA", "Fernanda. Mas isso não importa. Nada mais importa."),
            ("GUILHERME", "Fernanda, eu quero ouvir o que está acontecendo com você agora."),
            ("FERNANDA", "Minha vida está uma bagunça. Minha mãe está cansada de mim. Eu só trago problema para ela."),
            ("GUILHERME", "Você está sentindo muita culpa em relação à sua mãe."),
            ("FERNANDA", "Sim. Ela tentou ficar comigo tantas vezes, e eu estraguei tudo. Eu comecei a usar cocaína há uns seis meses. Sempre digo que vai ser a última vez."),
            ("GUILHERME", "E hoje, antes de vir para cá, você usou de novo?"),
            ("FERNANDA", "Usei muito. Por alguns minutos eu esqueço tudo. Depois fica pior. Eu perdi o emprego, me afastei das amigas, minha mãe nem sabe mais o que dizer."),
            ("GUILHERME", "Antes do uso ocupar tanto espaço, o que fazia parte da sua vida?"),
            ("FERNANDA", "Eu trabalhava num salão. Gostava de música, saía com minhas amigas. Eu tinha uma vida."),
            ("GUILHERME", "Qual dessas coisas faz mais falta quando você pensa em como era antes?"),
            ("FERNANDA", "Minha mãe olhando para mim sem medo. E minhas amigas. Eu destruí tudo, Guilherme."),
            ("GUILHERME", "Eu estou ouvindo, Fernanda. Você pode continuar falando. O que está mais difícil de suportar neste momento?"),
            ("FERNANDA", "A vergonha. E achar que eu nunca vou conseguir sair disso."),
            ("GUILHERME", "Eu não vou te apressar. Quero continuar ouvindo você, no seu tempo."),
            ("NARRADOR", "O diálogo evidencia perda de controle sobre o uso, prejuízos sociais e profissionais, culpa e desesperança. Na abordagem, Guilherme não promete resolver a situação: ele oferece presença, escuta e perguntas que permitem compreender a experiência de Fernanda."),
        ],
    },
    "a2-007": {
        "series": 2,
        "title": "Programa em Foco — Júlia e o Borderline",
        "podcast": True,
        "voices": {
            "ENTREVISTADOR": Voice(ANTONIO, 0, 0, "host-dinâmico-curioso"),
            "JULIA": Voice(THALITA, -2, 0, "jovem-reflexiva"),
        },
        "interlocutors": ("ENTREVISTADOR", "JULIA"),
        "turns": [
            ("ENTREVISTADOR", "Bem-vindos ao Em Foco Saúde Mental. Hoje vamos conversar sobre transtorno de personalidade borderline a partir de uma experiência pessoal. Júlia, estudante de Farmácia, está com a gente. Júlia, obrigado por topar essa conversa."),
            ("JULIA", "Eu que agradeço. Falar sobre isso é importante porque muita gente vive algo parecido e nem sempre entende o que está acontecendo."),
            ("ENTREVISTADOR", "Quando você percebeu que suas emoções e seus relacionamentos estavam te causando sofrimento?"),
            ("JULIA", "Na adolescência. Minhas emoções pareciam vir no volume máximo. Eu podia estar muito animada e, pouco depois, completamente desmoronada. E eu tinha um medo enorme de ser abandonada."),
            ("ENTREVISTADOR", "Esse medo acabava interferindo na forma como você se relacionava?"),
            ("JULIA", "Muito. Eu fazia de tudo para evitar que a pessoa fosse embora e, às vezes, reagia de um jeito tão intenso que acabava afastando justamente quem eu queria por perto."),
            ("ENTREVISTADOR", "Em que momento você procurou avaliação profissional?"),
            ("JULIA", "Demorou. Durante muito tempo eu achei que eu era simplesmente emocional demais. Quando procurei psicoterapia e depois avaliação psiquiátrica, veio o diagnóstico de transtorno de personalidade borderline."),
            ("ENTREVISTADOR", "E ouvir esse diagnóstico foi mais assustador ou esclarecedor?"),
            ("JULIA", "Os dois. No começo assustou. Depois virou uma forma de organizar coisas que antes pareciam sem nome. Eu entendi que não era a única pessoa vivendo aquilo e que havia tratamento."),
            ("ENTREVISTADOR", "O que mais mudou na sua rotina desde que começou o tratamento?"),
            ("JULIA", "Eu comecei a reconhecer melhor os gatilhos e a perceber quando uma emoção está crescendo antes de agir por impulso. Ainda é um processo, mas hoje eu tenho mais ferramentas."),
            ("ENTREVISTADOR", "Júlia, obrigado por dividir isso com tanta clareza. No próximo bloco, a psiquiatra Dra. Sara Almeida explica o que são os transtornos de personalidade e como o tratamento é estruturado."),
        ],
    },
    "a2-008": {
        "series": 2,
        "title": "Programa em Foco — Dra. Sara e os Transtornos de Personalidade",
        "podcast": True,
        "voices": {
            "ENTREVISTADOR": Voice(ANTONIO, 0, 0, "host-dinâmico-curioso"),
            "SARA": Voice(FRANCISCA, -1, 0, "especialista-clara-conversacional"),
        },
        "interlocutors": ("ENTREVISTADOR", "SARA"),
        "turns": [
            ("ENTREVISTADOR", "Estamos de volta ao Em Foco Saúde Mental. No bloco anterior, ouvimos Júlia falar sobre a experiência com borderline. Agora recebemos a psiquiatra Dra. Sara Almeida. Dra. Sara, obrigado por estar aqui."),
            ("SARA", "Eu que agradeço. Esse é um tema importante e ainda cercado de muito estigma."),
            ("ENTREVISTADOR", "Começando pelo básico: o que é um transtorno de personalidade?"),
            ("SARA", "É um padrão persistente de perceber, sentir e se comportar que se torna rígido e causa prejuízo importante na vida da pessoa. Pode afetar relacionamentos, trabalho, tomada de decisão e a própria percepção de si."),
            ("ENTREVISTADOR", "Então não estamos falando de uma característica isolada, como ser tímido ou impulsivo."),
            ("SARA", "Exatamente. Todo mundo tem traços de personalidade. Falamos em transtorno quando o padrão é duradouro, pouco flexível, aparece em diferentes contextos e produz sofrimento ou prejuízo significativo."),
            ("ENTREVISTADOR", "E por que alguns transtornos de personalidade aparecem associados a maior risco de comportamento suicida?"),
            ("SARA", "Porque podem existir combinações de sofrimento intenso, desesperança, impulsividade, conflitos interpessoais e outras condições associadas, como depressão ou uso de substâncias. O risco é individual e precisa ser avaliado clinicamente."),
            ("ENTREVISTADOR", "Os transtornos de personalidade ainda são organizados em três grandes grupos?"),
            ("SARA", "Sim. De forma tradicional, o grupo A inclui os transtornos paranoide, esquizoide e esquizotípico. O grupo B inclui antissocial, borderline, histriônico e narcisista. O grupo C inclui evitativo, dependente e obsessivo-compulsivo da personalidade."),
            ("ENTREVISTADOR", "E tratamento: qual é o eixo principal?"),
            ("SARA", "A psicoterapia costuma ser o eixo central. Medicamentos podem ser usados para sintomas específicos ou condições associadas, como depressão e ansiedade. O plano precisa ser individualizado e acompanhado por profissionais qualificados."),
            ("ENTREVISTADOR", "Dra. Sara, obrigado pela conversa. Informação clara reduz estigma e melhora a procura por cuidado. Seguimos girando a Ampulheta da Vida no próximo episódio."),
        ],
    },
    "a2-009": {
        "series": 2,
        "title": "Dona Lurdes, Mônica e os Desafios da Esquizofrenia",
        "voices": {
            "NARRADOR": Voice(ANTONIO, -5, -1, "narrador-discreto"),
            "LOURDES": Voice(FRANCISCA, -4, 0, "cuidadora-cansada-afetuosa"),
            "FATIMA": Voice(THALITA, -3, 0, "irmã-atenta"),
        },
        "interlocutors": ("LOURDES", "FATIMA"),
        "turns": [
            ("NARRADOR", "Hoje ouviremos uma conversa entre Dona Lurdes, mãe de Mônica, que vive com esquizofrenia, e Fátima, irmã de Lurdes. A conversa aborda sintomas, risco suicida e o impacto do cuidado sobre a família."),
            ("FATIMA", "Lurdes, você parece um pouco mais tranquila hoje. Como a Mônica está?"),
            ("LOURDES", "Está mais estável com o tratamento. Os sintomas ainda aparecem, mas agora ela consegue me dizer quando alguma coisa não está bem."),
            ("FATIMA", "Ela ainda ouve vozes?"),
            ("LOURDES", "Às vezes. E também tem momentos em que acredita que está sendo observada. O que mais me preocupa é quando ela se fecha completamente."),
            ("FATIMA", "Ela já falou sobre não querer continuar vivendo?"),
            ("LOURDES", "Já, principalmente nas crises. Ouvir isso é muito difícil. A equipe que acompanha a Mônica explicou que precisamos levar esse tipo de fala a sério e procurar atendimento quando o risco aumenta."),
            ("FATIMA", "E como você reage quando isso acontece?"),
            ("LOURDES", "Eu tento manter a calma, fico perto e escuto. Se percebo risco imediato ou piora importante, procuro o serviço de saúde."),
            ("FATIMA", "E você? Está conseguindo cuidar de si também?"),
            ("LOURDES", "Estou aprendendo. Entendi que não consigo carregar tudo sozinha. Comecei a participar de um grupo para familiares, e isso tem me feito bem."),
            ("FATIMA", "A Mônica ainda fala de planos para o futuro?"),
            ("LOURDES", "Sim. Ela quer voltar a estudar Artes. Estamos indo devagar, mas é bom ouvir ela falar de coisas que ainda deseja viver."),
            ("NARRADOR", "A esquizofrenia pode estar associada a maior vulnerabilidade ao comportamento suicida, especialmente quando há sofrimento intenso, depressão, alucinações, desesperança ou isolamento. Rede de apoio e acompanhamento profissional são fatores importantes de proteção."),
        ],
    },
}


BANNED_GARBAGE = (
    "sena.", "sustentante", "dratarsara", "parsara", "corsara", "rissa em jeito",
    "terapelta", "mandimônica", "esquisofrenia", "impossividade", "encutindo",
)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def prosody(key: str, speaker: str, text: str, idx: int) -> tuple[str, str, int]:
    ep = EPISODES[key]
    v: Voice = ep["voices"][speaker]
    rate = v.rate + (-1, 0, 1, 0)[idx % 4]
    pitch = v.pitch
    lower = text.lower()

    if ep.get("podcast"):
        # Podcast: mais ágil, sem atropelar. Perguntas ganham leve subida melódica.
        rate += 2 if speaker == "ENTREVISTADOR" else 1
        pause = 280 if speaker == "ENTREVISTADOR" else 330
        if text.endswith("?"):
            pitch += 1
            pause = 300
    else:
        pause = 520
        if speaker.startswith("ABORDADOR") or speaker == "GUILHERME":
            pause = 470
            rate -= 1
        if speaker in {"TENTANTE", "MARIA", "FERNANDA"}:
            pause = 620
        if any(x in lower for x in ("não quero", "não aguent", "desaparecer", "não estar aqui", "fracassei", "vergonha")):
            pause = max(pause, 760)
            rate -= 1
        if text.endswith("?"):
            pitch += 1
            pause += 80

    rate = max(-10, min(5, rate))
    pitch = max(-4, min(4, pitch))
    return f"{rate:+d}%", f"{pitch:+d}Hz", pause


async def synth(text: str, voice: Voice, rate: str, pitch: str, path: Path, sem: asyncio.Semaphore) -> None:
    async with sem:
        for attempt in range(1, 4):
            try:
                c = edge_tts.Communicate(text=text, voice=voice.model, rate=rate, pitch=pitch, volume="+0%")
                await asyncio.wait_for(c.save(str(path)), timeout=TIMEOUT)
                if not path.exists() or path.stat().st_size < 1024:
                    raise RuntimeError(f"Segmento inválido: {path}")
                return
            except Exception:
                if attempt == 3:
                    raise
                await asyncio.sleep(attempt)


def loudnorm(src: Path, dst: Path) -> None:
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
        "-af", f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA=11",
        "-ar", "44100", "-ac", "1", "-b:a", "128k", str(dst)
    ], check=True)


def metrics(path: Path) -> tuple[float, float, float]:
    p = subprocess.run([
        "ffmpeg", "-hide_banner", "-i", str(path),
        "-af", f"loudnorm=I={TARGET_LUFS}:TP={TRUE_PEAK}:LRA=11:print_format=json",
        "-f", "null", "-"
    ], text=True, capture_output=True)
    blocks = re.findall(r'\{\s*"input_i".*?\}', p.stderr, flags=re.S)
    if not blocks:
        raise RuntimeError(f"Falha ao medir {path.name}")
    data = json.loads(blocks[-1])
    audio = AudioSegment.from_file(path, format="mp3")
    return float(data["input_i"]), float(data["input_tp"]), float(audio.max_dBFS)


def text_gates(key: str) -> dict:
    ep = EPISODES[key]
    joined = norm(" ".join(t for _, t in ep["turns"]))
    lower = joined.lower()
    voices = ep["voices"]
    a, b = ep["interlocutors"]
    gates = {
        "legible_text": not any(token in lower for token in BANNED_GARBAGE),
        "two_distinct_interlocutors": voices[a].model != voices[b].model,
        "no_empty_turns": all(norm(t) for _, t in ep["turns"]),
        "known_speakers": all(s in voices for s, _ in ep["turns"]),
    }
    if key == "a2-005":
        gates["narrator_distinct_from_claudio"] = voices["NARRADOR"].model != voices["CLAUDIO"].model
    if key == "a2-006":
        guilherme = " ".join(t for s, t in ep["turns"] if s == "GUILHERME").lower()
        gates["bombeiro_does_not_promise_help"] = "ajud" not in guilherme
        gates["narrator_distinct_from_bombeiro"] = voices["NARRADOR"].model != voices["GUILHERME"].model
    if key in {"a2-007", "a2-008"}:
        gates["podcast_turn_density"] = len(ep["turns"]) >= 12
    return gates


async def build(key: str, sem: asyncio.Semaphore) -> dict:
    ep = EPISODES[key]
    gates = text_gates(key)
    if not all(gates.values()):
        raise RuntimeError(f"Gate textual falhou em {key}: {gates}")

    work = TMP / key
    work.mkdir(parents=True, exist_ok=True)
    seq = []
    tasks = []
    turns = ep["turns"]
    for idx, (speaker, text) in enumerate(turns):
        rate, pitch, pause = prosody(key, speaker, text, idx)
        part = work / f"{idx:03d}-{speaker.lower()}.mp3"
        tasks.append(synth(text, ep["voices"][speaker], rate, pitch, part, sem))
        seq.append((part, pause))
    await asyncio.gather(*tasks)

    merged = AudioSegment.silent(duration=180)
    for idx, (part, pause) in enumerate(seq):
        audio = AudioSegment.from_file(part, format="mp3").fade_in(6).fade_out(10)
        merged += audio
        if idx < len(seq) - 1:
            merged += AudioSegment.silent(duration=pause)
    merged += AudioSegment.silent(duration=380)
    merged = merged.high_pass_filter(70).low_pass_filter(14500)
    merged = effects.compress_dynamic_range(merged, threshold=-20.0, ratio=2.0, attack=8.0, release=75.0)

    out_dir = OUT1 if ep["series"] == 1 else OUT2
    out_dir.mkdir(parents=True, exist_ok=True)
    wav = work / "premaster.wav"
    target = out_dir / f"{key}-{VERSION}.mp3"
    merged.export(wav, format="wav")
    loudnorm(wav, target)
    lufs, tp, sample_peak = metrics(target)

    gates.update({
        "loudness": -19.5 <= lufs <= -16.5,
        "true_peak": tp <= -0.5,
        "no_clipping": sample_peak < -0.1,
        "minimum_duration": len(merged) >= 35000,
    })
    status = "PASS" if all(gates.values()) else "FAIL"
    return {
        "episode": key,
        "title": ep["title"],
        "output": target.name,
        "voice_ids": {k: v.model for k, v in ep["voices"].items()},
        "turns": len(turns),
        "duration_seconds": round(len(merged) / 1000, 2),
        "loudness_lufs": round(lufs, 2),
        "true_peak_db": round(tp, 2),
        "sample_peak_dbfs": round(sample_peak, 2),
        "gates": gates,
        "status": status,
    }


def patch_app() -> None:
    text = APP.read_text(encoding="utf-8")
    for key, ep in EPISODES.items():
        n = int(key.split("-")[1])
        series = ep["series"]
        pattern = rf'assets/audio/serie-{series}/{key}-[^" ]+\.mp3'
        repl = f'assets/audio/serie-{series}/{key}-{VERSION}.mp3'
        text, count = re.subn(pattern, repl, text, count=1)
        if count != 1:
            raise RuntimeError(f"URL não localizada para {key}")
    APP.write_text(text, encoding="utf-8")


async def main() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    catalog = {v["ShortName"] for v in await edge_tts.list_voices()}
    required = {voice.model for ep in EPISODES.values() for voice in ep["voices"].values()}
    missing = sorted(required - catalog)
    if missing:
        raise RuntimeError(f"Vozes indisponíveis: {missing}")

    sem = asyncio.Semaphore(MAX_CONCURRENT)
    results = []
    for key in EPISODES:
        print(f"[{key}] gerando {VERSION}")
        results.append(await build(key, sem))

    # Continuidade do apresentador entre os dois blocos de entrevista.
    host7 = EPISODES["a2-007"]["voices"]["ENTREVISTADOR"].model
    host8 = EPISODES["a2-008"]["voices"]["ENTREVISTADOR"].model
    continuity = host7 == host8
    all_pass = all(r["status"] == "PASS" for r in results) and continuity

    report = {
        "profile": "A1/A2 dialogue editorial v2",
        "all_automated_gates_pass": all_pass,
        "interviewer_voice_continuity_a2_007_008": continuity,
        "a1_dialogue_episodes": [8, 9, 10, 11, 13, 14, 15],
        "a1_single_voice_preserved": [1, 2, 3, 4, 5, 6, 7, 12, 16, 17, 18, 19, 20, 21],
        "perceptual_review": "REQUIRED_BEFORE_MAIN_MERGE",
        "episodes": results,
    }
    (OUT2 / "qa-dialogue-v2.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not all_pass:
        raise RuntimeError("Um ou mais gates v2 falharam")

    patch_app()
    print("Todos os episódios v2 passaram; app.js atualizado apenas na branch de revisão.")


if __name__ == "__main__":
    asyncio.run(main())
