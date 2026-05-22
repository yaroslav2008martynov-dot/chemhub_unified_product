import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = 'http://localhost:8000';

const elements = [
  [1,'H','Водород',1,1,'s'],[2,'He','Гелий',18,1,'s'],
  [3,'Li','Литий',1,2,'s'],[4,'Be','Бериллий',2,2,'s'],[5,'B','Бор',13,2,'p'],[6,'C','Углерод',14,2,'p'],[7,'N','Азот',15,2,'p'],[8,'O','Кислород',16,2,'p'],[9,'F','Фтор',17,2,'p'],[10,'Ne','Неон',18,2,'p'],
  [11,'Na','Натрий',1,3,'s'],[12,'Mg','Магний',2,3,'s'],[13,'Al','Алюминий',13,3,'p'],[14,'Si','Кремний',14,3,'p'],[15,'P','Фосфор',15,3,'p'],[16,'S','Сера',16,3,'p'],[17,'Cl','Хлор',17,3,'p'],[18,'Ar','Аргон',18,3,'p'],
  [19,'K','Калий',1,4,'s'],[20,'Ca','Кальций',2,4,'s'],[21,'Sc','Скандий',3,4,'d'],[22,'Ti','Титан',4,4,'d'],[23,'V','Ванадий',5,4,'d'],[24,'Cr','Хром',6,4,'d'],[25,'Mn','Марганец',7,4,'d'],[26,'Fe','Железо',8,4,'d'],[27,'Co','Кобальт',9,4,'d'],[28,'Ni','Никель',10,4,'d'],[29,'Cu','Медь',11,4,'d'],[30,'Zn','Цинк',12,4,'d'],[31,'Ga','Галлий',13,4,'p'],[32,'Ge','Германий',14,4,'p'],[33,'As','Мышьяк',15,4,'p'],[34,'Se','Селен',16,4,'p'],[35,'Br','Бром',17,4,'p'],[36,'Kr','Криптон',18,4,'p'],
  [37,'Rb','Рубидий',1,5,'s'],[38,'Sr','Стронций',2,5,'s'],[39,'Y','Иттрий',3,5,'d'],[40,'Zr','Цирконий',4,5,'d'],[41,'Nb','Ниобий',5,5,'d'],[42,'Mo','Молибден',6,5,'d'],[43,'Tc','Технеций',7,5,'d'],[44,'Ru','Рутений',8,5,'d'],[45,'Rh','Родий',9,5,'d'],[46,'Pd','Палладий',10,5,'d'],[47,'Ag','Серебро',11,5,'d'],[48,'Cd','Кадмий',12,5,'d'],[49,'In','Индий',13,5,'p'],[50,'Sn','Олово',14,5,'p'],[51,'Sb','Сурьма',15,5,'p'],[52,'Te','Теллур',16,5,'p'],[53,'I','Иод',17,5,'p'],[54,'Xe','Ксенон',18,5,'p'],
  [55,'Cs','Цезий',1,6,'s'],[56,'Ba','Барий',2,6,'s'],[57,'La–Lu','Лантаноиды',3,6,'f-link'],[72,'Hf','Гафний',4,6,'d'],[73,'Ta','Тантал',5,6,'d'],[74,'W','Вольфрам',6,6,'d'],[75,'Re','Рений',7,6,'d'],[76,'Os','Осмий',8,6,'d'],[77,'Ir','Иридий',9,6,'d'],[78,'Pt','Платина',10,6,'d'],[79,'Au','Золото',11,6,'d'],[80,'Hg','Ртуть',12,6,'d'],[81,'Tl','Таллий',13,6,'p'],[82,'Pb','Свинец',14,6,'p'],[83,'Bi','Висмут',15,6,'p'],[84,'Po','Полоний',16,6,'p'],[85,'At','Астат',17,6,'p'],[86,'Rn','Радон',18,6,'p'],
  [87,'Fr','Франций',1,7,'s'],[88,'Ra','Радий',2,7,'s'],[89,'Ac–Lr','Актиноиды',3,7,'f-link'],[104,'Rf','Резерфордий',4,7,'d'],[105,'Db','Дубний',5,7,'d'],[106,'Sg','Сиборгий',6,7,'d'],[107,'Bh','Борий',7,7,'d'],[108,'Hs','Хассий',8,7,'d'],[109,'Mt','Мейтнерий',9,7,'d'],[110,'Ds','Дармштадтий',10,7,'d'],[111,'Rg','Рентгений',11,7,'d'],[112,'Cn','Коперниций',12,7,'d'],[113,'Nh','Нихоний',13,7,'p'],[114,'Fl','Флеровий',14,7,'p'],[115,'Mc','Московий',15,7,'p'],[116,'Lv','Ливерморий',16,7,'p'],[117,'Ts','Теннессин',17,7,'p'],[118,'Og','Оганесон',18,7,'p'],
];
const lanth = [[57,'La','Лантан'],[58,'Ce','Церий'],[59,'Pr','Празеодим'],[60,'Nd','Неодим'],[61,'Pm','Прометий'],[62,'Sm','Самарий'],[63,'Eu','Европий'],[64,'Gd','Гадолиний'],[65,'Tb','Тербий'],[66,'Dy','Диспрозий'],[67,'Ho','Гольмий'],[68,'Er','Эрбий'],[69,'Tm','Тулий'],[70,'Yb','Иттербий'],[71,'Lu','Лютеций']].map(x=>[...x,'f']);
const act = [[89,'Ac','Актиний'],[90,'Th','Торий'],[91,'Pa','Протактиний'],[92,'U','Уран'],[93,'Np','Нептуний'],[94,'Pu','Плутоний'],[95,'Am','Америций'],[96,'Cm','Кюрий'],[97,'Bk','Берклий'],[98,'Cf','Калифорний'],[99,'Es','Эйнштейний'],[100,'Fm','Фермий'],[101,'Md','Менделевий'],[102,'No','Нобелий'],[103,'Lr','Лоуренсий']].map(x=>[...x,'f']);

function normalizeEquation(text='') { return String(text).replace(/<->|⇄|↔|⇌/g,'⇌').replace(/=>|->|⟶|→/g,'→').replace(/[;,.:\s]+$/g,'').trim(); }
function slugifyReaction(r) { return `${r.id}-${String(r.reaction_name || r.equation || 'reaction').toLowerCase().replace(/→|⇌|->|<->|=>/g,'-').replace(/[^a-zа-яё0-9]+/gi,'-').replace(/-+/g,'-').replace(/^-|-$/g,'').slice(0,90) || 'reaction'}`; }
function reactionUrl(r) { return `/reaction/${slugifyReaction(r)}`; }
function conditionText(r) { return [r.temperature,r.pressure,r.catalysts,r.solvents,r.conditions,r.states].filter(Boolean).map(x=>String(x).trim()).filter(Boolean).filter((v,i,a)=>a.indexOf(v)===i).join(', '); }

function ChemText({ text='' }) {
  const s = String(text);
  const out = [];
  for (let i=0;i<s.length;i++) {
    const ch=s[i], prev=s[i-1]||'', next=s[i+1]||'';
    if (/\d/.test(ch) && /[A-Za-zА-Яа-я\]\)]/.test(prev)) {
      let n=ch; while(i+1<s.length && /\d/.test(s[i+1])) { i++; n+=s[i]; }
      out.push(<sub className="idx" key={out.length}>{n}</sub>);
    } else if ((ch==='+' || ch==='-' || ch==='−') && /[\]\)]|[A-Za-zА-Яа-я]|\d/.test(prev) && (next==='' || /[\s,\]]/.test(next))) {
      out.push(<sup className="charge" key={out.length}>{ch}</sup>);
    } else if ((ch==='↑' || ch==='↓')) {
      out.push(<span className={ch==='↑'?'gas':'ppt'} key={out.length}>{ch}</span>);
    } else {
      out.push(ch);
    }
  }
  return <>{out}</>;
}

function ReactionEquation({ reaction }) {
  const normalized = normalizeEquation(reaction.equation || '');
  const cond = conditionText(reaction);
  const arrow = normalized.includes('⇌') ? '⇌' : (normalized.includes('≠') ? '≠' : '→');
  const parts = normalized.split(arrow);
  if (parts.length < 2) return <div className="eq-line"><ChemText text={normalized}/></div>;
  return <div className="eq-wrap">
    <div className="eq-main">
      <div className="eq-side right"><ChemText text={parts[0].trim()} /></div>
      <div className="arrow-box"><div className="arrow-cond">{cond}</div><div className="arrow-symbol">{arrow}</div></div>
      <div className="eq-side left"><ChemText text={parts.slice(1).join(arrow).trim()} /></div>
    </div>
    {reaction.reaction_name ? <div className="reaction-name">{reaction.reaction_name}</div> : null}
  </div>;
}

function ElementCard({ e, small=false, onClick }) {
  const [num,sym,name,group,period,block] = e;
  return <button className={`el ${block} ${small?'small':''}`} style={!small?{gridColumn:group, gridRow:period}:undefined} onClick={()=>onClick(sym)} title={name}><span className="num">{num}</span><b>{sym}</b><span>{name}</span></button>;
}
function PeriodicTable({ onPick }) { return <section className="card"><h2>Интерактивная таблица Менделеева</h2><div className="legend"><span className="s">s-блок</span><span className="p">p-блок</span><span className="d">d-блок</span><span className="f">f-блок</span></div><div className="ptable">{elements.map((e,i)=><ElementCard key={i} e={e} onClick={onPick}/>)}</div><div className="frows"><div className="frow"><span className="label">Лантаноиды</span>{lanth.map((e,i)=><ElementCard key={i} e={e} small onClick={onPick}/>)}</div><div className="frow"><span className="label">Актиноиды</span>{act.map((e,i)=><ElementCard key={i} e={e} small onClick={onPick}/>)}</div></div></section> }

function ReactionCard({ r }) { return <article className="reaction-card"><a className="card-link" href={reactionUrl(r)}><h3>{r.reaction_name || 'Химическая реакция'}</h3></a><ReactionEquation reaction={r}/>{r.impossible_note ? <p className="warn">{r.impossible_note}</p> : null}<div className="meta"><span>Реагенты: <ChemText text={r.reactants}/></span><span>Продукты: <ChemText text={r.products}/></span></div></article> }

function App() {
  const [q,setQ] = useState('');
  const [reactions,setReactions] = useState([]);
  const [ads,setAds] = useState([]);
  const [loading,setLoading] = useState(false);
  const hasQuery = useMemo(()=>q.trim().length>0,[q]);
  async function loadAds(){ const data = await fetch(`${API}/ads?placement=top`).then(r=>r.json()).catch(()=>[]); setAds(Array.isArray(data)?data:[]); }
  useEffect(()=>{loadAds();},[]);
  useEffect(()=>{ const path = window.location.pathname; const m = path.match(/\/reaction\/(.+)$/); if(m){ fetch(`${API}/reactions?q=${encodeURIComponent(path)}`).then(r=>r.json()).then(d=>{setReactions(Array.isArray(d)?d:[]); setQ(path);}).catch(()=>{}); } },[]);
  useEffect(()=>{ const query=q.trim(); if(!query){setReactions([]);return;} const t=setTimeout(async()=>{setLoading(true); const data=await fetch(`${API}/reactions?q=${encodeURIComponent(query)}`).then(r=>r.json()).catch(()=>[]); setReactions(Array.isArray(data)?data:[]); setLoading(false);},250); return()=>clearTimeout(t); },[q]);
  return <main className="page"><header className="hero"><div className="brand">ChemHub</div><h1>Поиск химических реакций</h1><p>Введите реагент(ы), продукт, условие, катализатор или название реакции.</p><input className="search" placeholder="Введите реагент(ы)" value={q} onChange={e=>setQ(e.target.value)} autoFocus/></header>{ads.length ? ads.map(ad=><div className="ad" key={ad.id} dangerouslySetInnerHTML={{__html:ad.html||ad.title}} />) : <div className="ad">Место для рекламы</div>}<PeriodicTable onPick={sym=>setQ(sym)}/><section className="card"><h2>Найденные реакции</h2>{loading && <p>Поиск...</p>}{!hasQuery && <p>Начните вводить запрос, чтобы увидеть реакции.</p>}{hasQuery && !loading && reactions.length===0 && <p>Ничего не найдено.</p>}{reactions.map(r=><ReactionCard key={r.id} r={r}/>)}</section><footer>Создатель проекта: Telegram @brovler228. По рекламе, сотрудничеству и исправлениям реакций: @brovler228 · <a href="/sitemap.xml">sitemap.xml</a></footer></main>
}

createRoot(document.getElementById('root')).render(<App/>);
