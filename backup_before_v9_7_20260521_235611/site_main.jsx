import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = 'http://localhost:8000';

const ELEMENTS = [
  [1,'H','s'],[2,'He','p'],[3,'Li','s'],[4,'Be','s'],[5,'B','p'],[6,'C','p'],[7,'N','p'],[8,'O','p'],[9,'F','p'],[10,'Ne','p'],
  [11,'Na','s'],[12,'Mg','s'],[13,'Al','p'],[14,'Si','p'],[15,'P','p'],[16,'S','p'],[17,'Cl','p'],[18,'Ar','p'],
  [19,'K','s'],[20,'Ca','s'],[21,'Sc','d'],[22,'Ti','d'],[23,'V','d'],[24,'Cr','d'],[25,'Mn','d'],[26,'Fe','d'],[27,'Co','d'],[28,'Ni','d'],[29,'Cu','d'],[30,'Zn','d'],[31,'Ga','p'],[32,'Ge','p'],[33,'As','p'],[34,'Se','p'],[35,'Br','p'],[36,'Kr','p'],
  [37,'Rb','s'],[38,'Sr','s'],[39,'Y','d'],[40,'Zr','d'],[41,'Nb','d'],[42,'Mo','d'],[43,'Tc','d'],[44,'Ru','d'],[45,'Rh','d'],[46,'Pd','d'],[47,'Ag','d'],[48,'Cd','d'],[49,'In','p'],[50,'Sn','p'],[51,'Sb','p'],[52,'Te','p'],[53,'I','p'],[54,'Xe','p'],
  [55,'Cs','s'],[56,'Ba','s'],[57,'La-Lu','f'],[72,'Hf','d'],[73,'Ta','d'],[74,'W','d'],[75,'Re','d'],[76,'Os','d'],[77,'Ir','d'],[78,'Pt','d'],[79,'Au','d'],[80,'Hg','d'],[81,'Tl','p'],[82,'Pb','p'],[83,'Bi','p'],[84,'Po','p'],[85,'At','p'],[86,'Rn','p'],
  [87,'Fr','s'],[88,'Ra','s'],[89,'Ac-Lr','f'],[104,'Rf','d'],[105,'Db','d'],[106,'Sg','d'],[107,'Bh','d'],[108,'Hs','d'],[109,'Mt','d'],[110,'Ds','d'],[111,'Rg','d'],[112,'Cn','d'],[113,'Nh','p'],[114,'Fl','p'],[115,'Mc','p'],[116,'Lv','p'],[117,'Ts','p'],[118,'Og','p'],
];
const LANTH = [[57,'La'],[58,'Ce'],[59,'Pr'],[60,'Nd'],[61,'Pm'],[62,'Sm'],[63,'Eu'],[64,'Gd'],[65,'Tb'],[66,'Dy'],[67,'Ho'],[68,'Er'],[69,'Tm'],[70,'Yb'],[71,'Lu']];
const ACT = [[89,'Ac'],[90,'Th'],[91,'Pa'],[92,'U'],[93,'Np'],[94,'Pu'],[95,'Am'],[96,'Cm'],[97,'Bk'],[98,'Cf'],[99,'Es'],[100,'Fm'],[101,'Md'],[102,'No'],[103,'Lr']];
const POS = {1:[1,1],2:[18,1],3:[1,2],4:[2,2],5:[13,2],6:[14,2],7:[15,2],8:[16,2],9:[17,2],10:[18,2],11:[1,3],12:[2,3],13:[13,3],14:[14,3],15:[15,3],16:[16,3],17:[17,3],18:[18,3]};
for (let n=19;n<=36;n++) POS[n]=[n-18,4];
for (let n=37;n<=54;n++) POS[n]=[n-36,5];
for (let n=55;n<=86;n++) { if(n<=57) POS[n]=[n-54,6]; else if(n>=72) POS[n]=[n-68,6]; }
for (let n=87;n<=118;n++) { if(n<=89) POS[n]=[n-86,7]; else if(n>=104) POS[n]=[n-100,7]; }

function normalizeEquation(text = '') { return String(text).replace(/<->|⇄|↔|⇌/g, '⇌').replace(/=>|->|⟶|→/g, '→').replace(/[;,.:\s]+$/g, '').trim(); }
function displayConditions(r) { return [r.temperature, r.pressure, r.catalysts, r.solvents, r.conditions, r.states].filter(Boolean).join(', '); }

function ChemText({ text = '' }) {
  const s = String(text);
  const nodes = [];
  for (let i = 0; i < s.length; i++) {
    const ch = s[i], prev = s[i-1] || '', next = s[i+1] || '';
    if (/\d/.test(ch) && /[A-Za-zА-Яа-я\]\)]/.test(prev)) {
      let n = ch; while (i+1 < s.length && /\d/.test(s[i+1])) { i++; n += s[i]; }
      nodes.push(<sub className="chem-sub" key={i}>{n}</sub>);
    } else if ((ch === '+' || ch === '-') && /[\]\)]|[A-Za-zА-Яа-я]|\d/.test(prev) && (next === ' ' || next === '' || next === ',' || next === ']')) {
      nodes.push(<sup className="chem-sup" key={i}>{ch}</sup>);
    } else if (ch === '^') {
      let charge = ''; while (i+1 < s.length && /[0-9+\-]/.test(s[i+1])) { i++; charge += s[i]; }
      nodes.push(<sup className="chem-sup" key={i}>{charge}</sup>);
    } else {
      nodes.push(ch);
    }
  }
  return <>{nodes}</>;
}

function SubstanceNote({ part }) {
  const m = String(part).match(/^(.*?)(\((?:конц\.|разб\.|[^)]*(?:ж|тв|газ|бел|красн|аморф|крист)[^)]*)\))$/i);
  if (!m) return <ChemText text={part} />;
  return <span className="substance"><ChemText text={m[1].trim()} /><small>{m[2]}</small></span>;
}
function FormulaSide({ text }) { return <>{String(text).split(/\s*\+\s*/).map((p,i)=><React.Fragment key={i}>{i>0 && <span className="plus"> + </span>}<SubstanceNote part={p}/></React.Fragment>)}</>; }
function ReactionEquation({ reaction }) {
  const equation = normalizeEquation(reaction.equation || '');
  if (equation.includes('≠')) return <div className="negative">{reaction.reactants || equation.replace('≠','')} — {reaction.impossible_note || 'не реагируют между собой'}</div>;
  const arrow = equation.includes('⇌') ? '⇌' : '→';
  const parts = equation.split(arrow); if (parts.length < 2) return <ChemText text={equation}/>;
  return <div className="reaction-visual"><div className="side left"><FormulaSide text={parts[0].trim()} /></div><div className="arrow-block"><div className="arrow-conditions">{displayConditions(reaction)}</div><div className="arrow-symbol">{arrow}</div></div><div className="side right"><FormulaSide text={parts.slice(1).join(arrow).trim()} /></div></div>;
}
function PeriodicTable({ onPick }) { return <section className="card"><h2>Интерактивная таблица Менделеева</h2><div className="ptable">{ELEMENTS.map(([n,s,b])=>{const [x,y]=POS[n]||[1,1];return <button className={`el block-${b}`} style={{gridColumn:x,gridRow:y}} key={n} onClick={()=>onPick(s)}><span>{n}</span><b>{s}</b></button>})}</div><div className="frows"><div className="f-label">Лантаноиды</div>{LANTH.map(([n,s])=><button className="el block-f" key={n} onClick={()=>onPick(s)}><span>{n}</span><b>{s}</b></button>)}<div className="f-label">Актиноиды</div>{ACT.map(([n,s])=><button className="el block-f" key={n} onClick={()=>onPick(s)}><span>{n}</span><b>{s}</b></button>)}</div></section> }

function App() {
  const [q, setQ] = useState(''); const [reactions,setReactions]=useState([]); const [ads,setAds]=useState([]); const [loading,setLoading]=useState(false);
  const hasQuery = useMemo(()=>q.trim().length>0,[q]);
  useEffect(()=>{fetch(`${API}/ads?placement=top`).then(r=>r.json()).then(d=>setAds(Array.isArray(d)?d:[])).catch(()=>setAds([]));},[]);
  useEffect(()=>{const query=q.trim(); if(!query){setReactions([]);return;} const t=setTimeout(async()=>{setLoading(true);const d=await fetch(`${API}/reactions?q=${encodeURIComponent(query)}`).then(r=>r.json()).catch(()=>[]);setReactions(Array.isArray(d)?d:[]);setLoading(false);},250); return()=>clearTimeout(t);},[q]);
  return <main className="page"><header className="hero"><div className="brand">ChemHub</div><h1>Поиск химических реакций</h1><p>Введите реагент(ы), продукт, условие, катализатор или название реакции.</p><input className="search" value={q} onChange={e=>setQ(e.target.value)} placeholder="Введите реагент(ы)" autoFocus /></header><div className="ad-slot">{ads.length?ads.map(a=><div key={a.id} dangerouslySetInnerHTML={{__html:a.html||a.title}}/>):'Место для рекламы'}</div><PeriodicTable onPick={(s)=>setQ(s)} /><section className="card"><h2>Найденные реакции</h2>{loading && <p>Поиск...</p>}{!hasQuery && <p>Начните вводить запрос, чтобы увидеть реакции.</p>}{hasQuery&&!loading&&reactions.length===0&&<p>Ничего не найдено.</p>}{reactions.map(r=><article className="reaction-card" key={r.id}><ReactionEquation reaction={r}/>{r.reaction_name&&<div className="reaction-name">{r.reaction_name}</div>}{r.impossible_note&&<div className="impossible-note">{r.impossible_note}</div>}<div className="reaction-meta"><span>Реагенты: <ChemText text={r.reactants}/></span><span>Продукты: <ChemText text={r.products}/></span></div>{r.url&&<a href={r.url}>Открыть страницу реакции</a>}</article>)}</section><footer>Создатель проекта: Telegram @brovler228. По рекламе, сотрудничеству и исправлениям реакций: @brovler228 · <a href="/sitemap.xml">sitemap.xml</a></footer></main>;
}
createRoot(document.getElementById('root')).render(<App/>);
