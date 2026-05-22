import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = 'http://localhost:8000';

const ELEMENTS = [
  ['H','Водород',1],['He','Гелий',18],['Li','Литий',1],['Be','Бериллий',2],['B','Бор',13],['C','Углерод',14],['N','Азот',15],['O','Кислород',16],['F','Фтор',17],['Ne','Неон',18],
  ['Na','Натрий',1],['Mg','Магний',2],['Al','Алюминий',13],['Si','Кремний',14],['P','Фосфор',15],['S','Сера',16],['Cl','Хлор',17],['Ar','Аргон',18],
  ['K','Калий',1],['Ca','Кальций',2],['Sc','Скандий',3],['Ti','Титан',4],['V','Ванадий',5],['Cr','Хром',6],['Mn','Марганец',7],['Fe','Железо',8],['Co','Кобальт',9],['Ni','Никель',10],['Cu','Медь',11],['Zn','Цинк',12],['Ga','Галлий',13],['Ge','Германий',14],['As','Мышьяк',15],['Se','Селен',16],['Br','Бром',17],['Kr','Криптон',18],
  ['Rb','Рубидий',1],['Sr','Стронций',2],['Y','Иттрий',3],['Zr','Цирконий',4],['Nb','Ниобий',5],['Mo','Молибден',6],['Tc','Технеций',7],['Ru','Рутений',8],['Rh','Родий',9],['Pd','Палладий',10],['Ag','Серебро',11],['Cd','Кадмий',12],['In','Индий',13],['Sn','Олово',14],['Sb','Сурьма',15],['Te','Теллур',16],['I','Иод',17],['Xe','Ксенон',18],
  ['Cs','Цезий',1],['Ba','Барий',2],['La','Лантан',3],['Ce','Церий',3],['Pr','Празеодим',3],['Nd','Неодим',3],['Pm','Прометий',3],['Sm','Самарий',3],['Eu','Европий',3],['Gd','Гадолиний',3],['Tb','Тербий',3],['Dy','Диспрозий',3],['Ho','Гольмий',3],['Er','Эрбий',3],['Tm','Тулий',3],['Yb','Иттербий',3],['Lu','Лютеций',3],['Hf','Гафний',4],['Ta','Тантал',5],['W','Вольфрам',6],['Re','Рений',7],['Os','Осмий',8],['Ir','Иридий',9],['Pt','Платина',10],['Au','Золото',11],['Hg','Ртуть',12],['Tl','Таллий',13],['Pb','Свинец',14],['Bi','Висмут',15],['Po','Полоний',16],['At','Астат',17],['Rn','Радон',18],
  ['Fr','Франций',1],['Ra','Радий',2],['Ac','Актиний',3],['Th','Торий',3],['Pa','Протактиний',3],['U','Уран',3],['Np','Нептуний',3],['Pu','Плутоний',3],['Am','Америций',3],['Cm','Кюрий',3],['Bk','Берклий',3],['Cf','Калифорний',3],['Es','Эйнштейний',3],['Fm','Фермий',3],['Md','Менделевий',3],['No','Нобелий',3],['Lr','Лоуренсий',3],['Rf','Резерфордий',4],['Db','Дубний',5],['Sg','Сиборгий',6],['Bh','Борий',7],['Hs','Хассий',8],['Mt','Мейтнерий',9],['Ds','Дармштадтий',10],['Rg','Рентгений',11],['Cn','Коперниций',12],['Nh','Нихоний',13],['Fl','Флеровий',14],['Mc','Московий',15],['Lv','Ливерморий',16],['Ts','Теннессин',17],['Og','Оганесон',18]
];

function normalizeEquation(text = '') {
  return String(text).replace(/<->|⇄|↔|⇌/g, '⇌').replace(/=>|->|⟶|→/g, '→').replace(/[;,.:\s]+$/g, '').trim();
}
function ChemText({ text = '' }) {
  return <span>{String(text).replace(/(\d+)/g, '$1')}</span>;
}
function ArrowBlock({ reaction }) {
  const equation = normalizeEquation(reaction.equation || '');
  const arrow = equation.includes('⇌') ? '⇌' : '→';
  const [left, ...rightParts] = equation.split(arrow);
  const conditions = [reaction.conditions, reaction.temperature, reaction.pressure, reaction.catalysts && `кат. ${reaction.catalysts}`, reaction.solvents && `раств. ${reaction.solvents}`].filter(Boolean).join(' · ');
  if (!rightParts.length) return <div className="equation"><ChemText text={equation}/></div>;
  return <div className="equation"><span><ChemText text={left.trim()}/></span><span className="arrowWrap"><span className="arrowCond">{conditions}</span><span className="arrow">{arrow}</span></span><span><ChemText text={rightParts.join(arrow).trim()}/></span></div>;
}
function ElementTable({ onPick }) {
  const [filter, setFilter] = useState('');
  const list = ELEMENTS.filter(([s,n]) => (s+n).toLowerCase().includes(filter.toLowerCase()));
  return <section className="card"><h2>Периодическая таблица</h2><input value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Найти элемент: Fe, железо..."/><div className="ptable">{list.map(([s,n,g],i)=><button key={s} className={`el g${g}`} onClick={()=>onPick(s)}><b>{s}</b><small>{i+1}</small><span>{n}</span></button>)}</div></section>;
}
function App() {
  const [q,setQ]=useState('');
  const [reactions,setReactions]=useState([]);
  const [loading,setLoading]=useState(false);
  useEffect(()=>{const query=q.trim(); if(!query){setReactions([]);return;} const t=setTimeout(async()=>{setLoading(true); const data=await fetch(`${API}/reactions?q=${encodeURIComponent(query)}`).then(r=>r.json()).catch(()=>[]); setReactions(Array.isArray(data)?data:[]); setLoading(false);},250); return()=>clearTimeout(t);},[q]);
  return <main className="page"><header className="hero"><h1>ChemHub — химический справочник реакций</h1><p>Поиск по формулам, условиям, катализаторам и элементам.</p><input className="search" value={q} onChange={e=>setQ(e.target.value)} placeholder="Например: Fe, H2SO4, электролиз NaCl" autoFocus/></header><ElementTable onPick={setQ}/><section className="card"><h2>Реакции</h2>{loading&&<p>Поиск...</p>}{!q.trim()&&<p>Введите запрос или выберите элемент.</p>}{q.trim()&&!loading&&reactions.length===0&&<p>Ничего не найдено.</p>}{reactions.map(r=><article className="reaction" key={r.id}><h3>{r.reaction_name||'Реакция'}</h3><ArrowBlock reaction={r}/>{(r.conditions||r.temperature||r.catalysts||r.pressure||r.solvents)&&<p className="meta">Условия: {[r.conditions,r.temperature,r.pressure,r.catalysts&&`катализатор ${r.catalysts}`,r.solvents&&`растворитель ${r.solvents}`].filter(Boolean).join('; ')}</p>}</article>)}</section><footer>Создатель проекта: Telegram @brovler228</footer></main>;
}

createRoot(document.getElementById('root')).render(<App />);
