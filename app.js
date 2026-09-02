(() => {
"use strict";
const SERIES={1:{id:"1",title:"Abordagem Técnica: comunicação que salva",shortTitle:"Abordagem Técnica",description:"Episódios voltados à comunicação operacional, aproximação, escuta e ferramentas de diálogo em ATS.",image:"https://i.pinimg.com/736x/46/a2/33/46a2335ebc2074b6df9a9774ce9cfd5d.jpg",alt:"Ampulheta como imagem simbólica da Série 1",status:"available"},2:{id:"2",title:"Engrenagens do comportamento suicida",shortTitle:"Engrenagens do comportamento",description:"Conteúdos de apoio para compreensão de fatores psicológicos, sociais e clínicos associados ao sofrimento em crise.",image:"https://i.pinimg.com/736x/51/e8/8c/51e88c0d477d8812200af68229bf66d7.jpg",alt:"Imagem simbólica sobre engrenagens e compreensão do comportamento",status:"available"},3:{id:"3",title:"Prevenção e transformação de vidas",shortTitle:"Prevenção",description:"Trilha em preparação para conteúdos voltados à prevenção, rede de apoio e continuidade do cuidado.",image:"https://i.pinimg.com/736x/1f/68/67/1f6867294fd6c1b101f2fdab626e658b.jpg",alt:"Imagem simbólica sobre prevenção e cuidado",status:"building"}};
const AUDIOS={1:[
{title:"A1 001: Abordagem Técnica - comunicação que salva!",url:"assets/audio/serie-1/a1-001-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 002: Comportamentos Desejáveis na Abordagem Técnica",url:"assets/audio/serie-1/a1-002-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 003: Comportamentos que Devem Ser Evitados na Abordagem Técnica",url:"assets/audio/serie-1/a1-003-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 004: A Aproximação Segura no Atendimento a Tentativas de Suicídio",url:"assets/audio/serie-1/a1-004-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 005: O Poder de Ouvir",url:"assets/audio/serie-1/a1-005-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 006: A Apresentação Pessoal - A Primeira Conexão",url:"assets/audio/serie-1/a1-006-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 007: Perguntas Simples - Rastreando Fatores de Risco e Proteção",url:"assets/audio/serie-1/a1-007-n3.mp3?v=n3-cast-20260901f"},
{title:"A1 008: Usando Perguntas Simples com Tentante de Perfil Depressivo",url:"assets/audio/serie-1/a1-008-n3.mp3?v=n3-cast-20260901e"},
{title:"A1 009: Usando Perguntas Simples com Tentante de Perfil Agressivo",url:"assets/audio/serie-1/a1-009-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 010: Usando Perguntas Simples com Tentante de Perfil Psicótico",url:"assets/audio/serie-1/a1-010-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 011: Usando Perguntas Complexas para Apoiar o Tentante",url:"assets/audio/serie-1/a1-011-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 012: Ferramentas de Diálogo Influenciando a Reflexão do Tentante",url:"assets/audio/serie-1/a1-012-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 013: Técnica do Sucesso Anterior - Resgatando Estratégias do Passado",url:"assets/audio/serie-1/a1-013-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 014: Ponte para o Passado - Resgatando Memórias Agradáveis",url:"assets/audio/serie-1/a1-014-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 015: Ponte para o Futuro - Criando Perspectivas Positivas",url:"assets/audio/serie-1/a1-015-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 016: Paráfrase Resumida - Refinando o Foco no Diálogo",url:"assets/audio/serie-1/a1-016-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 017: Especificidades para Abordar Tentantes de Perfil Depressivo",url:"assets/audio/serie-1/a1-017-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 018: Especificidades para Abordar Tentantes de Perfil Agressivo",url:"assets/audio/serie-1/a1-018-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 019: Especificidades para Abordar Tentantes de Perfil Psicótico",url:"assets/audio/serie-1/a1-019-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 020: Entrada Forçada - Quando a Segurança Exige Ação",url:"assets/audio/serie-1/a1-020-n3.mp3?v=n3-cast-20260901c"},
{title:"A1 021: Encerramento - Continuemos a Girar a Ampulheta da Vida",url:"assets/audio/serie-1/a1-021-n3.mp3?v=n3-cast-20260901c"}
],2:[
{title:"A2 000: Desvendando as Engrenagens",url:"assets/audio/serie-2/a2-000-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 001: O Suicídio ao Longo da História",url:"assets/audio/serie-2/a2-001-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 002: Decisões no Caos: O Cérebro em Crise",url:"assets/audio/serie-2/a2-002-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 003: Transtornos Mentais e o Peso do Sofrimento",url:"assets/audio/serie-2/a2-003-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 004: Maria e as Sombras da Depressão",url:"assets/audio/serie-2/a2-004-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 005: Cláudio e os Ciclos da Bipolaridade",url:"assets/audio/serie-2/a2-005-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 006: Fernanda e o Labirinto da Cocaína",url:"assets/audio/serie-2/a2-006-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 007: Programa em Foco - Saúde Mental: Júlia e o Desafio do Borderline",url:"assets/audio/serie-2/a2-007-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 008: Programa em Foco - Saúde Mental: Dra. Sara e os Transtornos de Personalidade",url:"assets/audio/serie-2/a2-008-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 009: Dona Lurdes, Mônica e os Desafios da Esquizofrenia",url:"assets/audio/serie-2/a2-009-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 010: As Vulnerabilidades Invisíveis: Um Olhar Filosófico e Social",url:"assets/audio/serie-2/a2-010-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 011: Quando as Emoções Dominam",url:"assets/audio/serie-2/a2-011-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 012: A Ação Antes da Razão",url:"assets/audio/serie-2/a2-012-n3.mp3?v=n3-cast-20260901c"},
{title:"A2 013: Um Novo Olhar para as Engrenagens",url:"assets/audio/serie-2/a2-013-n3.mp3?v=n3-cast-20260901c"}
],3:[]};
const LS={ONBOARD:"gav:onboard_done_v2",LAST:"gav:last_series_v2",PROGRESS:u=>`gav:progress:${u}`};
const $=(s,c=document)=>c.querySelector(s),$$=(s,c=document)=>[...c.querySelectorAll(s)];
const dom={onboarding:$("#onboarding"),slides:$$(".onboard-slide"),prev:$("#onboardPrev"),next:$("#onboardNext"),skip:$("#onboardSkip"),dont:$("#dontShowAgain"),aboutOpen:$("#aboutOpen"),aboutToggle:$("#aboutToggle"),aboutContent:$("#aboutContent"),seriesGrid:$("#seriesGrid"),panel:$("#libraryPanel"),kicker:$("#activeSeriesKicker"),title:$("#activeSeriesTitle"),desc:$("#activeSeriesDescription"),list:$("#episodeList"),tip:$("#audioTip"),back:$("#backToSeries")};
let slide=0,audios=[],lastFocus=null;
const format=s=>{const t=Math.floor(Number(s||0));return `${String(Math.floor(t/60)).padStart(2,"0")}:${String(t%60).padStart(2,"0")}`};
const save=(u,t)=>{try{localStorage.setItem(LS.PROGRESS(u),String(t||0))}catch{}};const load=u=>{try{return parseFloat(localStorage.getItem(LS.PROGRESS(u))||"0")}catch{return 0}};
function setAbout(open){dom.aboutContent.classList.toggle("is-open",open);dom.aboutToggle.setAttribute("aria-expanded",String(open));dom.aboutToggle.textContent=open?"Ocultar proposta":"Entenda a proposta"}
function renderSeries(){dom.seriesGrid.innerHTML="";Object.values(SERIES).forEach(s=>{const eps=AUDIOS[s.id]||[],available=s.status==="available"&&eps.length>0,a=document.createElement("article");a.className="series-card";a.innerHTML=`<div class="series-media"><img src="${s.image}" alt="${s.alt}" loading="lazy" decoding="async"><span class="series-badge">Série ${s.id}</span></div><div class="series-body"><h3>${s.title}</h3><p>${s.description}</p><div class="series-meta"><span class="pill ${available?"available":"building"}">${available?"Disponível":"Em construção"}</span><span class="pill">${eps.length} episódio(s)</span></div><div class="series-actions"><button class="btn ${available?"":"ghost"}" type="button" ${available?"":"disabled"} data-series-id="${s.id}">${available?"Ouvir episódios":"Disponível em breve"}</button></div></div>`;if(available)a.querySelector("button").addEventListener("click",()=>openSeries(s.id));dom.seriesGrid.appendChild(a)})}
function pauseAll(){audios.forEach(a=>a.pause());audios=[]}
function renderEpisodes(id){const s=SERIES[id],eps=AUDIOS[id]||[];if(!s||!eps.length)return;pauseAll();dom.list.innerHTML="";dom.tip.hidden=true;dom.kicker.textContent=`Série ${s.id} • ${eps.length} episódio(s)`;dom.title.textContent=s.title;dom.desc.textContent=s.description;eps.forEach((ep,i)=>{const saved=load(ep.url),a=document.createElement("article");a.className="episode-card";a.innerHTML=`<div class="episode-number">${String(i+1).padStart(2,"0")}</div><div class="episode-content"><h3>${ep.title}</h3><div class="episode-player"><audio controls preload="metadata" aria-label="${ep.title}"><source src="${ep.url}" type="audio/mpeg">Seu navegador não suporta áudio HTML5.</audio></div><div class="episode-meta"><span data-status>${saved>0?`Retomar em ${format(saved)}`:"Novo"}</span><a href="${ep.url}" download>Baixar arquivo</a><button type="button" data-reset>Zerar progresso</button></div></div>`;const audio=$("audio",a),status=$("[data-status]",a),reset=$("[data-reset]",a);audio.addEventListener("loadedmetadata",()=>{const p=load(ep.url);if(p>0&&p<audio.duration-2){audio.currentTime=p;dom.tip.hidden=false;status.textContent=`Retomar em ${format(p)}`}});audio.addEventListener("play",()=>audios.forEach(x=>{if(x!==audio&&!x.paused)x.pause()}));audio.addEventListener("timeupdate",()=>{save(ep.url,audio.currentTime);status.textContent=`Em ${format(audio.currentTime)}`});audio.addEventListener("ended",()=>{save(ep.url,0);status.textContent="Concluído"});reset.addEventListener("click",()=>{save(ep.url,0);audio.currentTime=0;status.textContent="Novo"});audios.push(audio);dom.list.appendChild(a)})}
function openSeries(id){renderEpisodes(id);dom.panel.classList.add("is-open");try{localStorage.setItem(LS.LAST,String(id))}catch{};setTimeout(()=>dom.panel.scrollIntoView({behavior:"smooth",block:"start"}),40)}
function closeSeries(){pauseAll();dom.panel.classList.remove("is-open");dom.list.innerHTML="";try{localStorage.removeItem(LS.LAST)}catch{};$("#series")?.scrollIntoView({behavior:"smooth",block:"start"})}
function showSlide(i){slide=Math.max(0,Math.min(i,dom.slides.length-1));dom.slides.forEach((s,n)=>s.classList.toggle("is-active",n===slide));dom.prev.disabled=slide===0;dom.next.textContent=slide===dom.slides.length-1?"Começar":"Próximo"}
function openOnboard(){lastFocus=document.activeElement;dom.onboarding.classList.add("is-open");dom.onboarding.setAttribute("aria-hidden","false");document.documentElement.style.overflow="hidden";showSlide(0);setTimeout(()=>dom.next.focus(),60)}
function closeOnboard(){if(dom.dont.checked)try{localStorage.setItem(LS.ONBOARD,"1")}catch{};dom.onboarding.classList.remove("is-open");dom.onboarding.setAttribute("aria-hidden","true");document.documentElement.style.overflow="";lastFocus?.focus?.()}
function bind(){dom.aboutToggle.addEventListener("click",()=>setAbout(!dom.aboutContent.classList.contains("is-open")));dom.aboutOpen.addEventListener("click",()=>{setAbout(true);$("#sobre")?.scrollIntoView({behavior:"smooth",block:"start"})});dom.back.addEventListener("click",closeSeries);dom.prev.addEventListener("click",()=>showSlide(slide-1));dom.next.addEventListener("click",()=>slide>=dom.slides.length-1?closeOnboard():showSlide(slide+1));dom.skip.addEventListener("click",closeOnboard);document.addEventListener("keydown",e=>{if(e.key==="Escape"&&dom.onboarding.classList.contains("is-open"))closeOnboard()})}
function restore(){let last=null;try{last=localStorage.getItem(LS.LAST)}catch{};if(last&&SERIES[last]&&(AUDIOS[last]||[]).length)openSeries(last)}
function init(){renderSeries();bind();try{if(localStorage.getItem(LS.ONBOARD)!=="1")openOnboard()}catch{openOnboard()}restore()}
document.readyState==="loading"?document.addEventListener("DOMContentLoaded",init,{once:true}):init();
})();