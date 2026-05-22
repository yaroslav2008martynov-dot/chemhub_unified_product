import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = 'http://localhost:8000';

const ELEMENTS = [
  ['H',1,1,'s'],['He',1,18,'s'],
  ['Li',2,1,'s'],['Be',2,2,'s'],['B',2,13,'p'],['C',2,14,'p'],['N',2,15,'p'],['O',2,16,'p'],['F',2,17,'p'],['Ne',2,18,'p'],
  ['Na',3,1,'s'],['Mg',3,2,'s'],['Al',3,13,'p'],['Si',3,14,'p'],['P',3,15,'p'],['S',3,16,'p'],['Cl',3,17,'p'],['Ar',3,18,'p'],
  ['K',4,1,'s'],['Ca',4,2,'s'],['Sc',4,3,'d'],['Ti',4,4,'d'],['V',4,5,'d'],['Cr',4,6,'d'],['Mn',4,7,'d'],['Fe',4,8,'d'],['Co',4,9,'d'],['Ni',4,10,'d'],['Cu',4,11,'d'],['Zn',4,12,'d'],['Ga',4,13,'p'],['Ge',4,14,'p'],['As',4,15,'p'],['Se',4,16,'p'],['Br',4,17,'p'],['Kr',4,18,'p'],
  ['Rb',5,1,'s'],['Sr',5,2,'s'],['Y',5,3,'d'],['Zr',5,4,'d'],['Nb',5,5,'d'],['Mo',5,6,'d'],['Tc',5,7,'d'],['Ru',5,8,'d'],['Rh',5,9,'d'],['Pd',5,10,'d'],['Ag',5,11,'d'],['Cd',5,12,'d'],['In',5,13,'p'],['Sn',5,14,'p'],['Sb',5,15,'p'],['Te',5,16,'p'],['I',5,17,'p'],['Xe',5,18,'p'],
  ['Cs',6,1,'s'],['Ba',6,2,'s'],['La-Lu',6,3,'f placeholder'],['Hf',6,4,'d'],['Ta',6,5,'d'],['W',6,6,'d'],['Re',6,7,'d'],['Os',6,8,'d'],['Ir',6,9,'d'],['Pt',6,10,'d'],['Au',6,11,'d'],['Hg',6,12,'d'],['Tl',6,13,'p'],['Pb',6,14,'p'],['Bi',6,15,'p'],['Po',6,16,'p'],['At',6,17,'p'],['Rn',6,18,'p'],
  ['Fr',7,1,'s'],['Ra',7,2,'s'],['Ac-Lr',7,3,'f placeholder'],['Rf',7,4,'d'],['Db',7,5,'d'],['Sg',7,6,'d'],['Bh',7,7,'d'],['Hs',7,8,'d'],['Mt',7,9,'d'],['Ds',7,10,'d'],['Rg',7,11,'d'],['Cn',7,12,'d'],['Nh',7,13,'p'],['Fl',7,14,'p'],['Mc',7,15,'p'],['Lv',7,16,'p'],['Ts',7,17,'p'],['Og',7,18,'p'],
  ['La',9,4,'f'],['Ce',9,5,'f'],['Pr',9,6,'f'],['Nd',9,7,'f'],['Pm',9,8,'f'],['Sm',9,9,'f'],['Eu',9,10,'f'],['Gd',9,11,'f'],['Tb',9,12,'f'],['Dy',9,13,'f'],['Ho',9,14,'f'],['Er',9,15,'f'],['Tm',9,16,'f'],['Yb',9,17,'f'],['Lu',9,18,'f'],
  ['Ac',10,4,'f'],['Th',10,5,'f'],['Pa',10,6,'f'],['U',10,7,'f'],['Np',10,8,'f'],['Pu',10,9,'f'],['Am',10,10,'f'],['Cm',10,11,'f'],['Bk',10,12,'f'],['Cf',10,13,'f'],['Es',10,14,'f'],['Fm',10,15,'f'],['Md',10,16,'f'],['No',10,17,'f'],['Lr',10,18,'f'],
];

function slugifyReaction(r) {
  const raw = String(r.reaction_name || r.equation || `reaction-${r.id}`).toLowerCase()
    .replace(/[₀₁₂₃₄₅₆₇₈₉]/g, (m) => '₀₁₂₃₄₅₆₇₈₉'.indexOf(m))
    .replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹]/g, (m) => '⁰¹²³⁴⁵⁶⁷⁸⁹'.indexOf(m))
    .replace(/→|⇌|->|<->|=>/g, '-')
    .replace(/[^a-zа-яё0-9]+/gi, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 90) || 'reaction';
  return `${r.id}-${raw}`;
}
function reactionUrl(r) { return `/reaction/${slugifyReaction(r)}`; }
function normalizeEquation(text = '') { return String(text).replace(/<->|⇄|↔|⇌/g, '⇌').replace(/=>|->|⟶|→/g, '→').replace(/[;,.:\s]+$/g, '').trim(); }

function splitNote(token) {
  const m = String(token).match(/^(.+?)\(([^()]+)\)$/);
  if (!m) return [token, ''];
  const note = m[2].trim();
  if (/^(конц\.?|разб\.?|\d+%|газ|тв\.?|ж\.?|р-р|aq|s|l|g|красный|белый|черный|чёрный|аморфный|крист\.?|ромбическая)$/i.test(note)) return [m[1], note];
  return [token, ''];
}

function ChemText({ text = '' }) {
  const s = String(text);
  const nodes = [];
  for (let i = 0; i < s.length; i += 1) {
    const ch = s[i];
    const prev = s[i - 1] || '';
    const next = s[i + 1] || '';
    if (/\d/.test(ch) && /[A-Za-zА-Яа-я\)\]]/.test(prev)) {
      let number = ch;
      while (i + 1 < s.length && /\d/.test(s[i + 1])) { i += 1; number += s[i]; }
      nodes.push(<sub className="chem-sub" key={i}>{number}</sub>);
    } else if ((ch === '+' || ch === '-' || ch === '−') && /[\]\)]|[A-Za-zА-Яа-я]|\d/.test(prev) && (next === ' ' || next === '' || next === ',' || next === ']')) {
      nodes.push(<sup className="chem-charge" key={i}>{ch}</sup>);
    } else {
      nodes.push(ch);
    }
  }
  return <>{nodes}</>;
}

function FormulaToken({ token }) {
  const [main, note] = splitNote(token);
  return <span className="formula-token"><span><ChemText text={main}/></span>{note && <small className="formula-note">{note}</small>}</span>;
}

function FormulaSide({ side = '' }) {
  return <>{String(side).split(/\s*\+\s*/).map((part, idx) => <React.Fragment key={idx}>{idx > 0 && <span className="plus"> + </span>}<FormulaToken token={part.trim()} /></React.Fragment>)}</>;
}

function allConditions(r) {
  return [r.temperature, r.pressure, r.conditions, r.catalysts && `кат. ${r.catalysts}`, r.solvents && `р-р ${r.solvents}`, r.states].filter(Boolean).join(', ');
}

function ReactionEquation({ reaction }) {
  const normalized = normalizeEquation(reaction.equation || '');
  const arrow = normalized.includes('⇌') ? '⇌' : (normalized.includes('≠') ? '≠' : '→');
  const parts = normalized.split(arrow);
  if (parts.length < 2) return <div className="equation"><ChemText text={normalized}/></div>;
  const cond = allConditions(reaction);
  return <div className="reaction-display"><div className="side left"><FormulaSide side={parts[0].trim()} /></div><div className="arrow-stack">{cond && <div className="arrow-cond">{cond}</div>}<div className="arrow-symbol">{arrow}</div></div><div className="side right"><FormulaSide side={parts.slice(1).join(arrow).trim()} /></div></div>;
}

function PeriodicTable({ onPick }) {
  return <section className="card periodic-card"><h2>Таблица Менделеева</h2><div className="legend"><span className="s">s-блок</span><span className="p">p-блок</span><span className="d">d-блок</span><span className="f">f-блок</span></div><div className="periodic-grid">{ELEMENTS.map(([sym,row,col,block]) => <button key={sym} className={`el ${block.split(' ')[0]} ${block.includes('placeholder') ? 'placeholder' : ''}`} style={{gridRow: row, gridColumn: col}} onClick={() => !block.includes('placeholder') && onPick(sym)}>{sym}</button>)}</div></section>;
}

function App() {
  const [q, setQ] = useState('');
  const [reactions, setReactions] = useState([]);
  const [ads, setAds] = useState([]);
  const [loading, setLoading] = useState(false);
  const hasQuery = useMemo(() => q.trim().length > 0, [q]);
  async function loadAds() { const data = await fetch(`${API}/ads?placement=top`).then((r) => r.json()).catch(() => []); setAds(Array.isArray(data) ? data : []); }
  useEffect(() => { loadAds(); }, []);
  useEffect(() => {
    const query = q.trim();
    if (!query) { setReactions([]); return; }
    const t = setTimeout(async () => { setLoading(true); const data = await fetch(`${API}/reactions?q=${encodeURIComponent(query)}`).then((r) => r.json()).catch(() => []); setReactions(Array.isArray(data) ? data : []); setLoading(false); }, 250);
    return () => clearTimeout(t);
  }, [q]);
  return <main className="page"><header className="hero"><div className="brand">ChemHub</div><h1>Поиск химических реакций</h1><p>Введите реагент(ы), продукт, условие, катализатор или название реакции.</p><input className="search" value={q} placeholder="Введите реагент(ы)" onChange={(e) => setQ(e.target.value)} autoFocus /></header>{ads.length ? ads.map((ad) => <section className="ad" key={ad.id} dangerouslySetInnerHTML={{__html: ad.html || ad.title}} />) : <section className="ad">Место для рекламы</section>}<PeriodicTable onPick={(sym) => setQ(sym)} /><section className="card"><h2>Найденные реакции</h2>{loading && <p>Поиск...</p>}{!hasQuery && <p>Начните вводить запрос, чтобы увидеть реакции.</p>}{hasQuery && !loading && reactions.length === 0 && <p>Ничего не найдено.</p>}{reactions.map((r) => <article className={`reaction-card ${r.hidden ? 'negative' : ''}`} key={r.id}><a className="reaction-link" href={reactionUrl(r)}>{r.reaction_name || (r.hidden ? 'Реакция не протекает' : 'Химическая реакция')}</a><ReactionEquation reaction={r}/>{r.hidden && <p className="negative-note">Эти вещества не реагируют между собой.</p>}{r.reaction_name && <div className="reaction-name">{r.reaction_name}</div>}<div className="meta"><span>Реагенты: <ChemText text={r.reactants}/></span><span>Продукты: <ChemText text={r.products}/></span></div></article>)}</section><footer>Создатель проекта: Telegram @brovler228. По рекламе, сотрудничеству и исправлениям реакций: @brovler228 · <a href="/sitemap.xml">sitemap.xml</a></footer></main>;
}

createRoot(document.getElementById('root')).render(<App />);
