(() => {
  "use strict";

  const RELEASE = "gav-learning-v4-20260902";

  const s1 = [
    ["a1-001","A1 001","Abordagem Técnica - comunicação que salva!","assets/audio/serie-1/a1-001-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-002","A1 002","Comportamentos Desejáveis na Abordagem Técnica","assets/audio/serie-1/a1-002-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-003","A1 003","Comportamentos que Devem Ser Evitados na Abordagem Técnica","assets/audio/serie-1/a1-003-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-004","A1 004","A Aproximação Segura no Atendimento a Tentativas de Suicídio","assets/audio/serie-1/a1-004-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-005","A1 005","O Poder de Ouvir","assets/audio/serie-1/a1-005-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-006","A1 006","A Apresentação Pessoal - A Primeira Conexão","assets/audio/serie-1/a1-006-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-007","A1 007","Perguntas Simples - Rastreando Fatores de Risco e Proteção","assets/audio/serie-1/a1-007-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-008","A1 008","Usando Perguntas Simples com Tentante de Perfil Depressivo","assets/audio/serie-1/a1-008-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-009","A1 009","Usando Perguntas Simples com Tentante de Perfil Agressivo","assets/audio/serie-1/a1-009-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-010","A1 010","Usando Perguntas Simples com Tentante de Perfil Psicótico","assets/audio/serie-1/a1-010-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-011","A1 011","Usando Perguntas Complexas para Apoiar o Tentante","assets/audio/serie-1/a1-011-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-012","A1 012","Ferramentas de Diálogo Influenciando a Reflexão do Tentante","assets/audio/serie-1/a1-012-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-013","A1 013","Técnica do Sucesso Anterior - Resgatando Estratégias do Passado","assets/audio/serie-1/a1-013-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-014","A1 014","Ponte para o Passado - Resgatando Memórias Agradáveis","assets/audio/serie-1/a1-014-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-015","A1 015","Ponte para o Futuro - Criando Perspectivas Positivas","assets/audio/serie-1/a1-015-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-016","A1 016","Paráfrase Resumida - Refinando o Foco no Diálogo","assets/audio/serie-1/a1-016-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-017","A1 017","Especificidades para Abordar Tentantes de Perfil Depressivo","assets/audio/serie-1/a1-017-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-018","A1 018","Especificidades para Abordar Tentantes de Perfil Agressivo","assets/audio/serie-1/a1-018-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-019","A1 019","Especificidades para Abordar Tentantes de Perfil Psicótico","assets/audio/serie-1/a1-019-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-020","A1 020","Entrada Forçada - Quando a Segurança Exige Ação","assets/audio/serie-1/a1-020-n3.mp3?v=n3-ptbr-native-20260901"],
    ["a1-021","A1 021","Encerramento - Continuemos a Girar a Ampulheta da Vida","assets/audio/serie-1/a1-021-n3.mp3?v=n3-ptbr-native-20260901"]
  ].map(([id,code,title,url]) => ({id,code,title,url,type:"audio"}));

  const s2 = [
    ["a2-000","A2 000","Desvendando as Engrenagens","assets/audio/serie-2/a2-000-n3.mp3?v=n3-cast-20260901g"],
    ["a2-001","A2 001","O Suicídio ao Longo da História","assets/audio/serie-2/a2-001-n3.mp3?v=n3-cast-20260901g"],
    ["a2-002","A2 002","Decisões no Caos: O Cérebro em Crise","assets/audio/serie-2/a2-002-n3.mp3?v=n3-cast-20260901g"],
    ["a2-003","A2 003","Transtornos Mentais e o Peso do Sofrimento","assets/audio/serie-2/a2-003-n3.mp3?v=n3-cast-20260901g"],
    ["a2-004","A2 004","Maria e as Sombras da Depressão","assets/audio/serie-2/a2-004-n3.mp3?v=n3-cast-20260901c"],
    ["a2-005","A2 005","Cláudio e os Ciclos da Bipolaridade","assets/audio/serie-2/a2-005-n3.mp3?v=n3-cast-20260901c"],
    ["a2-006","A2 006","Fernanda e o Labirinto da Cocaína","assets/audio/serie-2/a2-006-n3.mp3?v=n3-cast-20260901c"],
    ["a2-007","A2 007","Programa em Foco - Saúde Mental: Júlia e o Desafio do Borderline","assets/audio/serie-2/a2-007-n3.mp3?v=n3-cast-20260901c"],
    ["a2-008","A2 008","Programa em Foco - Saúde Mental: Dra. Sara e os Transtornos de Personalidade","assets/audio/serie-2/a2-008-n3.mp3?v=n3-cast-20260901c"],
    ["a2-009","A2 009","Dona Lurdes, Mônica e os Desafios da Esquizofrenia","assets/audio/serie-2/a2-009-n3.mp3?v=n3-cast-20260901c"],
    ["a2-010","A2 010","As Vulnerabilidades Invisíveis: Um Olhar Filosófico e Social","assets/audio/serie-2/a2-010-n3.mp3?v=n3-cast-20260901g"],
    ["a2-011","A2 011","Quando as Emoções Dominam","assets/audio/serie-2/a2-011-n3.mp3?v=n3-cast-20260901g"],
    ["a2-012","A2 012","A Ação Antes da Razão","assets/audio/serie-2/a2-012-n3.mp3?v=n3-cast-20260901g"],
    ["a2-013","A2 013","Um Novo Olhar para as Engrenagens","assets/audio/serie-2/a2-013-n3.mp3?v=n3-cast-20260901g"]
  ].map(([id,code,title,url]) => ({id,code,title,url,type:"audio"}));

  window.GAV_MANIFEST = Object.freeze({
    release: RELEASE,
    series: Object.freeze([
      Object.freeze({
        id:"1", slug:"serie-1", kind:"audio", status:"available",
        title:"Abordagem Técnica: comunicação que salva", shortTitle:"Abordagem Técnica",
        description:"Episódios voltados à comunicação operacional, aproximação, escuta e ferramentas de diálogo em ATS.",
        image:"assets/img/series-1.jpg", alt:"Ampulheta como imagem simbólica da Série 1", items:Object.freeze(s1)
      }),
      Object.freeze({
        id:"2", slug:"serie-2", kind:"audio", status:"available",
        title:"Engrenagens do comportamento suicida", shortTitle:"Engrenagens do comportamento",
        description:"Conteúdos de apoio para compreensão de fatores psicológicos, sociais e clínicos associados ao sofrimento em crise.",
        image:"assets/img/series-2.jpg", alt:"Imagem simbólica sobre engrenagens e compreensão do comportamento", items:Object.freeze(s2)
      }),
      Object.freeze({
        id:"3", slug:"serie-3", kind:"psp", status:"available",
        title:"Primeiros Socorros Psicológicos no Trabalho", shortTitle:"Primeiros Socorros Psicológicos",
        description:"Trilha baseada em PSP da OMS, adaptada à prevenção em saúde mental, apoio entre pares e autocuidado em profissionais de segurança e emergência.",
        image:"assets/img/series-3.jpg", alt:"Profissional de emergência oferecendo presença e apoio a um colega", itemCount:10
      })
    ])
  });
})();
