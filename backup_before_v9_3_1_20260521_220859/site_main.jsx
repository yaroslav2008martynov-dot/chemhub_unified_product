import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = 'http://localhost:8000';

const ELEMENTS = [
 ['H',1],['He',18],['Li',1],['Be',2],['B',13],['C',14],['N',15],['O',16],['F',17],['Ne',18],
 ['Na',1],['Mg',2],['Al',13],['Si',14],['P',15],['S',16],['Cl',17],['Ar',18],['K',1],['Ca',2],
 ['Sc',3],['Ti',4],['V',5],['Cr',6],['Mn',7],['Fe',8],['Co',9],['Ni',10],['Cu',11],['Zn',12],
 ['Ga',13],['Ge',14],['As',15],['Se',16],['Br',17],['Kr',18],['Rb',1],['Sr',2],['Y',3],['Zr',4],
 ['Nb',5],['Mo',6],['Tc',7],['Ru',8],['Rh',9],['Pd',10],['Ag',11],['Cd',12],['In',13],['Sn',14],
 ['Sb',15],['Te',16],['I',17],['Xe',18],['Cs',1],['Ba',2],['La',3],['Ce',3],['Pr',3],['Nd',3],
 ['Pm',3],['Sm',3],['Eu',3],['Gd',3],['Tb',3],['Dy',3],['Ho',3],['Er',3],['Tm',3],['Yb',3],['Lu',3],
 ['Hf',4],['Ta',5],['W',6],['Re',7],['Os',8],['Ir',9],['Pt',10],['Au',11],['Hg',12],['Tl',13],
 ['Pb',14],['Bi',15],['Po',16],['At',17],['Rn',18],['Fr',1],['Ra',2],['Ac',3],['Th',3],['Pa',3],
 ['U',3],['Np',3],['Pu',3],['Am',3],['Cm',3],['Bk',3],['Cf',3],['Es',3],['Fm',3],['Md',3],
 ['No',3],['Lr',3],['Rf',4],['Db',5],['Sg',6],['Bh',7],['Hs',8],['Mt',9],['Ds',10],['Rg',11],
 ['Cn',12],['Nh',13],['Fl',14],['Mc',15],['Lv',16],['Ts',17],['Og',18]
];

function normalizeEquation(text = '') {
  return String(text)
    .replace(/<->|⇄|↔|⇌/g, '⇌')
    .replace(/=>|->|⟶|→/g, '→')
    .replace(/[;,.:\s]+$/g, '')
    .trim();
}

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

function splitAnnotation(species) {
  const m = String(species).trim().match(/^(.+?)\(([^()]*)\)$/);
  if (!m) return { base: species, note: '' };
  const inner = m[2].trim();
  if (!/[А-Яа-яA-Za-z]{3,}/.test(inner)) return { base: species, note: '' };
  if (/^(конц\.?|разб\.?|\d+\s*%|aq|s|l|g)$/i.test(inner)) return { base: species, note: '' };
  return { base: m[1].trim(), note: inner };
}

function ChemFormula({ text = '' }) {
  const s = String(text);
  const out = [];
  for (let i = 0; i < s.length; i += 1) {
    const ch = s[i];
    const prev = s[i - 1] || '';
    if (ch === '^') {
      let charge = '';
      while (i + 1 < s.length && /[0-9+\-−]/.test(s[i + 1])) { i += 1; charge += s[i]; }
      out.push(<sup className="chem-sup" key={i}>{charge.replace('-', '−')}</sup>);
      continue;
    }
    if ((ch === '+' || ch === '-' || ch === '−') && /[\]\)]|[A-Za-zА-Яа-я]|\d/.test(prev) && (i === s.length - 1 || /[\s,]/.test(s[i + 1] || ''))) {
      out.push(<sup className="chem-sup" key={i}>{ch === '-' ? '−' : ch}</sup>);
      continue;
    }
    if (/\d/.test(ch) && /[A-Za-zА-Яа-я\)\]]/.test(prev)) {
      let n = ch;
      while (i + 1 < s.length && /\d/.test(s[i + 1])) { i += 1; n += s[i]; }
      out.push(<sub className="chem-sub" key={i}>{n}</sub>);
      continue;
    }
    out.push(<span key={i}>{ch}</span>);
  }
  return <>{out}</>;
}

function Species({ text }) {
  const { base, note } = splitAnnotation(text);
  return <span className="species"><span><ChemFormula text={base} /></span>{note && <small className="species-note">{note}</small>}</span>;
}

function ReactionSide({ side = '' }) {
  const parts = String(side).split(/\s*\+\s*/).filter(Boolean);
  return <span className="side">{parts.map((p, i) => <React.Fragment key={`${p}-${i}`}>{i > 0 && <span className="plus"> + </span>}<Species text={p} /></React.Fragment>)}</span>;
}

function reactionConditions(r) {
  const vals = [];
  for (const v of [r.temperature, r.conditions, r.catalysts, r.solvents, r.pressure, r.states]) {
    const s = String(v || '').trim();
    if (s && !vals.includes(s)) vals.push(s);
  }
  return vals.join(', ');
}

function ReactionEquation({ reaction }) {
  const normalized = normalizeEquation(reaction.equation || '');
  const arrow = normalized.includes('⇌') ? '⇌' : (normalized.includes('≠') ? '≠' : '→');
  const parts = normalized.split(arrow);
  if (parts.length < 2) return <div className="equation"><ChemFormula text={normalized} /></div>;
  return <div className="rxn-line">
    <ReactionSide side={parts[0]} />
    <span className="arrow-box"><span className="arrow-cond">{reactionConditions(reaction)}</span><span className="arrow">{arrow}</span></span>
    <ReactionSide side={parts.slice(1).join(arrow)} />
  </div>;
}

function ReactionCard({ r }) {
  return <article className="reaction-card">
    {r.reaction_name && <h3><a href={reactionUrl(r)}>{r.reaction_name}</a></h3>}
    <ReactionEquation reaction={r} />
    {!r.reaction_name && <a className="reaction-link" href={reactionUrl(r)}>Открыть страницу реакции</a>}
    {r.impossible_note && <p className="warning">{r.impossible_note}</p>}
  </article>;
}

function PeriodicTable({ onPick }) {
  return <section className="card periodic-card"><h2>Таблица Менделеева</h2><div className="periodic-grid">
    {ELEMENTS.map(([sym, group], idx) => <button key={sym} style={{ gridColumn: group }} onClick={() => onPick(sym)} title={`Найти реакции ${sym}`}>{idx + 1}<b>{sym}</b></button>)}
  </div></section>;
}

function App() {
  const [q, setQ] = useState('');
  const [reactions, setReactions] = useState([]);
  const [ads, setAds] = useState([]);
  const [loading, setLoading] = useState(false);
  const hasQuery = useMemo(() => q.trim().length > 0, [q]);

  useEffect(() => { fetch(`${API}/ads?placement=top`).then(r => r.json()).then(d => setAds(Array.isArray(d) ? d : [])).catch(() => []); }, []);
  useEffect(() => {
    const query = q.trim();
    if (!query) { setReactions([]); return; }
    const t = setTimeout(async () => {
      setLoading(true);
      const data = await fetch(`${API}/reactions?q=${encodeURIComponent(query)}`).then(r => r.json()).catch(() => []);
      setReactions(Array.isArray(data) ? data : []);
      setLoading(false);
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  return <main className="page">
    <header className="hero"><div className="brand">ChemHub</div><h1>Поиск химических реакций</h1><p>Введите реагент(ы), продукт, условие, катализатор или название реакции.</p>
      <input className="search" placeholder="Введите реагент(ы)" value={q} onChange={e => setQ(e.target.value)} autoFocus />
    </header>
    <PeriodicTable onPick={setQ} />
    <section className="ad-slot">{ads.length ? ads.map(ad => <div key={ad.id} dangerouslySetInnerHTML={{ __html: ad.html || ad.title }} />) : 'Место для рекламы'}</section>
    <section className="card"><h2>Найденные реакции</h2>{loading && <p>Поиск...</p>}{!hasQuery && <p>Начните вводить запрос, чтобы увидеть реакции.</p>}{hasQuery && !loading && reactions.length === 0 && <p>Ничего не найдено.</p>}{reactions.map(r => <ReactionCard key={r.id} r={r} />)}</section>
    <footer>Создатель проекта: Telegram @brovler228. По рекламе, сотрудничеству и исправлениям реакций: @brovler228 · <a href="/sitemap.xml">sitemap.xml</a></footer>
  </main>;
}

createRoot(document.getElementById('root')).render(<App />);
