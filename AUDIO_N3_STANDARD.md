# Padrão Sonoro N3 Natural

Versão canônica: `n3-20260831`.

## Objetivo

O N3 Natural substitui o N2 como referência de produção para novas masters, preservando todas as versões anteriores para rollback e comparação perceptual. O objetivo não é apenas uma voz neural correta, mas fala interpretada de forma semanticamente coerente, respirada e adequada ao papel comunicacional.

## Perfis

- `N3-C` — Clinical/Instructional: mono, voz limpa, sem efeitos decorativos. Usado em conteúdos clínicos, psicoeducativos e instruções.
- `N3-D` — Dialog/Cinematic: estéreo, casting persistente, paisagem sonora e Foley somente quando a cena justificar.

## Motor de voz

Síntese de fala neural pt-BR via `edge-tts`. As vozes devem ser resolvidas em tempo de execução e ter fallback seguro. Narradores, instrutores e personagens mantêm identidade vocal persistente dentro de uma série.

## Prosódia

É proibido usar ciclos mecânicos baseados apenas no índice do turno. Velocidade, pitch e pausa devem ser calculados pela função da frase: explicação, pergunta, acolhimento, reflexão, instrução, contraste/transição, conclusão, hesitação ou tensão controlada. Microvariações podem existir, desde que determinísticas e derivadas do conteúdo, não de um metrônomo de turnos.

## Respiração e segmentação

Blocos longos devem ser segmentados em unidades respiratórias semanticamente plausíveis, preferencialmente entre 9 e 20 palavras, favorecendo quebras antes de conectivos e mudanças de ideia. Nenhuma palavra do conteúdo pode ser alterada por esse processo.

## Pausas

O N3 diferencia:

- pausa linguística;
- pausa reflexiva/emocional;
- pausa experiencial para execução de instrução;
- pausa dramática em narrativa.

Pausas não devem seguir um valor fixo recorrente. O motor aplica pequenas variações determinísticas dentro de faixas seguras.

## Pronúncia

Manter dicionário de pronúncia para siglas, nomes próprios e termos técnicos. Alterações fonéticas devem ser aplicadas apenas na camada de síntese e nunca modificar o roteiro canônico.

## Sound design

Ambiente e Foley são autorizados apenas em `N3-D` e quando houver função narrativa. Regras obrigatórias:

1. nunca mascarar palavras;
2. nunca inserir efeito sem função de cena;
3. não dramatizar material clínico/instrucional;
4. usar apenas efeitos próprios, procedurais ou com licença compatível;
5. registrar cada efeito no manifesto de sound design.

A biblioteca procedural inclui room tone, vento, tráfego, passagem de veículo, passos, xícara/mesa, isqueiro, crepitação de cigarro e ambiente de boate. A existência do efeito não autoriza seu uso: ele só entra quando o roteiro ou a cena o justificarem.

## Masterização

### N3-C
- MP3 128 kbps;
- mono;
- 44,1 kHz;
- alvo aproximado: -18 dBFS;
- teto de pico: -1,2 dBFS;
- compressão leve 2:1.

### N3-D
- MP3 192 kbps;
- estéreo;
- 44,1 kHz;
- voz sempre perceptualmente dominante;
- ambiente normalmente entre -32 e -40 dBFS, com automação conforme a cena;
- teto de pico: -1,2 dBFS.

## Gates obrigatórios

Antes da promoção para runtime: arquivo decodificável, duração > 0, sample rate correto, canal correto, ausência de clipping, ausência de `speechSynthesis`, URL válida, roteiro preservado, voz/casting esperado, manifesto atualizado e smoke test do player.

O gate automatizado não substitui escuta perceptual. Pronúncia, naturalidade, emoção e adequação de pausas exigem revisão auditiva humana antes de declarar uma master como perceptualmente definitiva.
