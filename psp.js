(() => {
"use strict";

const PSP_IMAGE="https://images.pexels.com/photos/6519869/pexels-photo-6519869.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1500&fit=crop";
const RATE=.90,STATE="gav:psp-audio:";
let CARDS=[];
const cache=new Map();
const run={card:null,chunks:[],i:0,paused:false,cancelled:false};

const speechOK=()=>("speechSynthesis"in window)&&("SpeechSynthesisUtterance"in window);
const loadState=id=>{try{return{index:0,completed:false,...JSON.parse(localStorage.getItem(STATE+id)||"{}")}}catch{return{index:0,completed:false}}};
const saveState=(id,s)=>{try{localStorage.setItem(STATE+id,JSON.stringify(s))}catch{}};
const voices=()=>{if(!speechOK())return[];const v=speechSynthesis.getVoices(),br=v.filter(x=>/^pt-BR$/i.test(x.lang)),pt=v.filter(x=>/^pt/i.test(x.lang));return br.length?br:pt};
const voiceFor=s=>{const v=voices();return s==="profissional"&&v[1]?v[1]:(v[0]||null)};
const chunksOf=segs=>segs.flatMap(s=>(s.text.match(/[^.!?]+[.!?]+|[^.!?]+$/g)||[s.text]).map(t=>({speaker:s.speaker,text:t.trim()})).filter(x=>x.text));

async function loadCards(){
  const r=await fetch("psp-cards.json",{cache:"no-store"});
  if(!r.ok)throw new Error("Não foi possível carregar os cards PSP.");
  CARDS=await r.json();
}

async function loadLesson(index){
  if(cache.has(index))return cache.get(index);
  const p=(async()=>{
    const n=String(index+1).padStart(2,"0");
    const r=await fetch(`roteiros/serie-3/psp-${n}.md`,{cache:"force-cache"});
    if(!r.ok)throw new Error("Roteiro de áudio indisponível.");
    const text=await r.text(),segs=[];
    text.split(/\r?\n/).forEach(line=>{
      let m=line.match(/^\*\*(INSTRUTOR|PROFISSIONAL):\*\*\s*(.+)$/);
      if(m)segs.push({speaker:m[1]==="PROFISSIONAL"?"profissional":"instrutor",text:m[2].trim()});
    });
    if(!segs.length)throw new Error("Roteiro de áudio vazio.");
    return segs;
  })();
  cache.set(index,p);return p;
}

function pauseHtml(){document.querySelectorAll("audio").forEach(a=>a.pause())}
function cancel(keep=true){
  if(speechOK())speechSynthesis.cancel();
  run.cancelled=true;run.paused=false;
  const old=run.card;run.card=null;run.chunks=[];run.i=0;
  if(old&&keep)updateUi(old);
}

function updateUi(card,state=null){
  if(!card)return;
  const index=+card.dataset.pspIndex,id=`psp-${String(index+1).padStart(2,"0")}`,s=state||loadState(id);
  const b=card.querySelector("[data-audio-toggle]"),reset=card.querySelector("[data-audio-reset]"),status=card.querySelector("[data-audio-status]"),bar=card.querySelector("[data-audio-progress]");
  const active=run.card===card,total=active?run.chunks.length:0,current=active?run.i:s.index,pct=s.completed&&!active?100:(total?Math.round(current/total*100):Math.min(95,current*8));
  if(b){
    b.disabled=!speechOK();
    b.textContent=!speechOK()?"Áudio indisponível":active?(run.paused?"Retomar":"Pausar"):s.completed?"Ouvir novamente":s.index>0?"Retomar microaula":"Ouvir microaula";
  }
  if(reset)reset.hidden=!active&&!s.completed&&!s.index;
  if(status)status.textContent=!speechOK()?"Use o conteúdo escrito neste navegador.":active?(run.paused?"Pausado":"Em reprodução"):s.completed?"Concluído":s.index>0?"Em andamento":"Novo";
  if(bar){bar.style.width=`${pct}%`;bar.parentElement?.setAttribute("aria-valuenow",String(pct))}
}

function speakChunk(card,id){
  if(run.card!==card||run.cancelled)return;
  if(run.i>=run.chunks.length){
    saveState(id,{index:0,completed:true});run.card=null;run.chunks=[];run.i=0;run.paused=false;updateUi(card,{index:0,completed:true});return;
  }
  const c=run.chunks[run.i],u=new SpeechSynthesisUtterance(c.text);
  u.lang="pt-BR";u.rate=RATE;u.pitch=c.speaker==="profissional"?1.04:.98;
  const v=voiceFor(c.speaker);if(v)u.voice=v;
  u.onend=()=>{if(run.card!==card||run.cancelled)return;run.i++;saveState(id,{index:run.i,completed:false});updateUi(card,{index:run.i,completed:false});speakChunk(card,id)};
  u.onerror=()=>{if(run.card!==card)return;saveState(id,{index:run.i,completed:false});run.card=null;run.paused=false;updateUi(card)};
  speechSynthesis.speak(u);updateUi(card,{index:run.i,completed:false});
}

async function toggleLesson(card){
  if(!card||!speechOK())return;
  if(run.card===card){if(run.paused){speechSynthesis.resume();run.paused=false}else{speechSynthesis.pause();run.paused=true}updateUi(card);return}
  cancel(true);pauseHtml();
  const index=+card.dataset.pspIndex,id=`psp-${String(index+1).padStart(2,"0")}`;
  const button=card.querySelector("[data-audio-toggle]"),status=card.querySelector("[data-audio-status]");
  try{
    if(button){button.disabled=true;button.textContent="Preparando áudio…"}if(status)status.textContent="Carregando roteiro";
    const segs=await loadLesson(index),chunks=chunksOf(segs),s=loadState(id);
    run.card=card;run.chunks=chunks;run.i=s.completed?0:Math.min(s.index,Math.max(0,chunks.length-1));run.paused=false;run.cancelled=false;
    saveState(id,{index:run.i,completed:false});speakChunk(card,id);
  }catch(e){
    if(button){button.disabled=false;button.textContent="Tentar novamente"}if(status)status.textContent="Não foi possível iniciar o áudio";
    console.error(e);
  }
}

function resetLesson(card){
  const index=+card.dataset.pspIndex,id=`psp-${String(index+1).padStart(2,"0")}`;
  if(run.card===card)cancel(false);saveState(id,{index:0,completed:false});updateUi(card,{index:0,completed:false});
}

function audioMarkup(c){
  return `<section class="psp-audio" aria-label="Microaula em áudio do Card ${c.n}">
    <div class="psp-audio-head"><div><span class="psp-audio-kicker">Microaula em áudio</span><strong>${c.title}</strong></div><span class="psp-audio-duration">2–4 min</span></div>
    <p class="psp-audio-note">Ouça uma explicação aplicada deste card. O conteúdo escrito permanece integralmente disponível para consulta.</p>
    <div class="psp-audio-controls"><button class="btn secondary psp-audio-play" type="button" data-audio-toggle>Ouvir microaula</button><button class="psp-audio-reset" type="button" data-audio-reset hidden>Reiniciar</button><span class="psp-audio-status" data-audio-status>Novo</span></div>
    <div class="psp-audio-track" role="progressbar" aria-label="Progresso da microaula" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><span data-audio-progress></span></div>
    <p class="psp-audio-fallback">A voz é gerada pelo mecanismo em português do próprio dispositivo; quando houver duas vozes disponíveis, instrutor e profissional usam timbres distintos.</p>
  </section>`;
}

function cardMarkup(c,index){
  const id=`psp-detail-${index+1}`;
  return `<article class="psp-card" data-psp-index="${index}">
    <button class="psp-card-toggle" type="button" aria-expanded="false" aria-controls="${id}">
      <div class="psp-media"><img src="${c.image}" alt="${c.alt}" loading="lazy" decoding="async"></div>
      <div class="psp-summary"><div class="psp-top"><span class="psp-step">Card ${c.n} • ${c.phase}</span><span class="psp-tag">${c.tag}</span></div><h3>${c.title}</h3><div class="psp-summary-meta"><span class="psp-audio-chip">Áudio • 2–4 min</span><span class="psp-open-label">Abrir conteúdo <span aria-hidden="true">＋</span></span></div></div>
    </button>
    <div class="psp-card-details" id="${id}" hidden>
      <p class="psp-lead">${c.lead}</p><p class="psp-context">${c.context}</p>${audioMarkup(c)}
      <div class="psp-objective"><strong>Objetivo de aprendizagem</strong><p>${c.objective}</p></div>
      <div class="psp-block"><strong>Aplicação no campo</strong><ul>${c.field.map(x=>`<li>${x}</li>`).join("")}</ul></div>
      <div class="psp-block psp-team"><strong>Colega e equipe</strong><p>${c.team}</p></div>
      <div class="psp-block psp-avoid"><strong>Evite</strong><p>${c.avoid}</p></div>
      <p class="psp-check"><strong>Microchecagem:</strong> ${c.check}</p>
    </div></article>`;
}

function closeAll(except=null){
  document.querySelectorAll(".psp-card").forEach(card=>{
    if(card===except)return;if(run.card===card)cancel(false);card.classList.remove("is-open");
    const t=card.querySelector(".psp-card-toggle"),d=card.querySelector(".psp-card-details"),l=card.querySelector(".psp-open-label");
    if(t)t.setAttribute("aria-expanded","false");if(d)d.hidden=true;if(l)l.innerHTML='Abrir conteúdo <span aria-hidden="true">＋</span>';updateUi(card);
  });
}

function bindCards(){
  document.querySelectorAll(".psp-card-toggle").forEach(t=>t.addEventListener("click",()=>{
    const card=t.closest(".psp-card"),d=card?.querySelector(".psp-card-details"),l=card?.querySelector(".psp-open-label");if(!card||!d)return;
    const opening=t.getAttribute("aria-expanded")!=="true";closeAll(opening?card:null);if(!opening&&run.card===card)cancel(false);
    card.classList.toggle("is-open",opening);t.setAttribute("aria-expanded",String(opening));d.hidden=!opening;
    if(l)l.innerHTML=opening?'Ocultar conteúdo <span aria-hidden="true">−</span>':'Abrir conteúdo <span aria-hidden="true">＋</span>';
    if(opening){updateUi(card);setTimeout(()=>card.scrollIntoView({behavior:"smooth",block:"start"}),40)}
  }));
  document.querySelectorAll("[data-audio-toggle]").forEach(b=>b.addEventListener("click",()=>toggleLesson(b.closest(".psp-card"))));
  document.querySelectorAll("[data-audio-reset]").forEach(b=>b.addEventListener("click",()=>resetLesson(b.closest(".psp-card"))));
  document.querySelectorAll(".psp-card").forEach(updateUi);
}

function returnToSeries(){cancel(false);const b=document.getElementById("backToSeries");b?b.click():document.getElementById("series")?.scrollIntoView({behavior:"smooth",block:"start"})}
const endAction=label=>`<div class="series-end-action"><button class="btn ghost series-end-button" type="button">${label}</button></div>`;
function bindEnd(root=document){root.querySelectorAll(".series-end-button").forEach(b=>{if(b.dataset.bound==="1")return;b.dataset.bound="1";b.addEventListener("click",returnToSeries)})}
function ensureAudioEnd(){const list=document.getElementById("episodeList");if(!list||!list.children.length||list.querySelector(".psp-shell"))return;if(!list.querySelector(".series-end-action"))list.insertAdjacentHTML("beforeend",endAction("Fechar esta série e voltar à página inicial"));bindEnd(list)}

function openPsp(){
  const panel=document.getElementById("libraryPanel"),k=document.getElementById("activeSeriesKicker"),title=document.getElementById("activeSeriesTitle"),desc=document.getElementById("activeSeriesDescription"),tip=document.getElementById("audioTip"),list=document.getElementById("episodeList");
  if(!panel||!k||!title||!desc||!list)return;cancel(false);pauseHtml();if(tip)tip.hidden=true;
  k.textContent="Série 3 • 10 cards • 10 microaulas";title.textContent="Primeiros Socorros Psicológicos";desc.textContent="Leia cada card para consulta rápida e use a microaula de 2 a 4 minutos para aprofundar a aplicação.";
  list.innerHTML=`<div class="psp-shell"><div class="psp-path" aria-label="Progressão da trilha de PSP"><div class="psp-path-step"><strong>Preparar</strong><span>contexto e recursos</span></div><div class="psp-path-step"><strong>Observar</strong><span>segurança e prioridades</span></div><div class="psp-path-step"><strong>Escutar</strong><span>contato e necessidades</span></div><div class="psp-path-step"><strong>Conectar</strong><span>apoio e continuidade</span></div><div class="psp-path-step"><strong>Cuidar</strong><span>colega, equipe e si</span></div></div><div class="psp-intro"><strong>Como usar:</strong> abra um card para ler o conteúdo e ouvir sua microaula. Na primeira leitura, siga a ordem numérica; depois, use os cards como consulta rápida. O progresso dos áudios fica salvo neste dispositivo.</div><div class="psp-grid">${CARDS.map(cardMarkup).join("")}</div><div class="psp-references"><strong>Base técnica</strong><p>Conteúdo estruturado a partir do guia de Primeiros Socorros Psicológicos da OMS/WHO e da versão em português da OPAS. <a href="https://www.who.int/publications-detail-redirect/9789241548205" target="_blank" rel="noopener noreferrer">OMS/WHO</a> • <a href="https://iris.paho.org/handle/10665.2/7676" target="_blank" rel="noopener noreferrer">OPAS/OMS em português</a>.</p></div>${endAction("Fechar a trilha de PSP e voltar à página inicial")}</div>`;
  bindCards();bindEnd(list);panel.classList.add("is-open");setTimeout(()=>panel.scrollIntoView({behavior:"smooth",block:"start"}),40);
}

function enhance(){
  const all=[...document.querySelectorAll(".series-card")],button=document.querySelector('button[data-series-id="3"]'),card=button?.closest(".series-card")||all[2];if(!card||!button)return;
  card.dataset.series="3";const img=card.querySelector(".series-media img"),h=card.querySelector(".series-body h3"),p=card.querySelector(".series-body p"),m=card.querySelector(".series-meta");
  if(img){img.src=PSP_IMAGE;img.alt="Paramédico oferecendo presença e apoio a uma pessoa junto a uma ambulância";img.referrerPolicy="no-referrer"}
  if(h)h.textContent="Primeiros Socorros Psicológicos";if(p)p.textContent="Trilha prática de PSP com 10 cards e 10 microaulas em áudio para profissionais de emergência e segurança pública.";if(m)m.innerHTML='<span class="pill available">Disponível</span><span class="pill">10 cards + 10 áudios</span>';
  button.disabled=false;button.classList.remove("ghost");button.textContent="Abrir trilha de PSP";if(button.dataset.pspBound!=="1"){button.dataset.pspBound="1";button.addEventListener("click",openPsp)}
  const items=document.querySelectorAll(".about-list li");if(items[2])items[2].innerHTML="<strong>Série 3:</strong> Primeiros Socorros Psicológicos.";
}

function observe(){const list=document.getElementById("episodeList");if(!list)return;new MutationObserver(()=>setTimeout(ensureAudioEnd,0)).observe(list,{childList:true,subtree:false})}
document.addEventListener("play",e=>{if(e.target instanceof HTMLAudioElement&&run.card)cancel(true)},true);
window.addEventListener("beforeunload",()=>{if(speechOK())speechSynthesis.cancel()});
if(speechOK()){speechSynthesis.getVoices();speechSynthesis.onvoiceschanged=()=>speechSynthesis.getVoices()}

async function init(){try{await loadCards();enhance();observe()}catch(e){console.error(e)}}
document.readyState==="loading"?document.addEventListener("DOMContentLoaded",init,{once:true}):init();
})();