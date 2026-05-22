import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = 'http://localhost:8000';

function slugifyReaction(r) {
  const raw = String(r.reaction_name || r.equation || `reaction-${r.id}`).toLowerCase()
    .replace(/→|⇌|->|<->|=>|≠/g, '-')
    .replace(/[^a-zа-яё0-9]+/gi, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 90) || 'reaction';
  return `${r.id}-${raw}`;
}
function reactionUrl(r) { return `/reaction/${slugifyReaction(r)}`; }
function normalizeEquation(text = '') {
  return String(text).replace(/<->|⇄|↔|⇌|в‡Њ/g, '⇌').replace(/=>|->|⟶|→|в†’/g, '→').replace(/[;,.:\s]+$/g, '').trim();
}

function ChemText({ text = '' }) {
  const s = String(text || '').replace(/\^([0-9]*[+-])/g, '');
  const nodes = [];
  for (let i = 0; i < s.length; i += 1) {
    const ch = s[i];
    const prev = s[i - 1] || '';
    if (/\d/.test(ch) && /[A-Za-zА-Яа-я\)\]]/.test(prev)) {
      let n = ch;
      while (i + 1 < s.length && /\d/.test(s[i + 1])) { i += 1; n += s[i]; }
      nodes.push(<sub className="chem-index" key={nodes.length}>{n}</sub>);
    } else {
      nodes.push(<React.Fragment key={nodes.length}>{ch}</React.Fragment>);
    }
  }
  return <>{nodes}</>;
}

function collectAboveArrow(r) {
  return [r.conditions, r.temperature, r.pressure, r.catalysts, r.solvents]
    .filter(v => v && String(v).trim())
    .join(', ')
    .replace(/;\s*/g, ', ');
}
function ReactionEquation({ reaction }) {
  const normalized = normalizeEquation(reaction.equation || '');
  const arrow = normalized.includes('⇌') ? '⇌' : (normalized.includes('≠') ? '≠' : '→');
  const parts = normalized.split(arrow);
  if (parts.length < 2) return <div className="reaction-equation"><ChemText text={normalized}/></div>;
  const above = collectAboveArrow(reaction);
  return <div className="reaction-equation equation-layout">
    <div className="chem-side"><ChemText text={parts[0].trim()} /></div>
    <div className="arrow-stack">
      {above && <div className="arrow-condition">{above}</div>}
      <div className={`chem-arrow ${arrow === '⇌' ? 'reversible' : ''} ${arrow === '≠' ? 'negative' : ''}`}>{arrow}</div>
    </div>
    <div className="chem-side"><ChemText text={parts.slice(1).join(arrow).trim()} /></div>
  </div>;
}
function ReactionDetails({ reaction }) {
  const detailRows = [
    ['Пояснения', reaction.states],
    ['Источник', reaction.source_pdf ? `${reaction.source_pdf}${reaction.source_page ? ', стр. ' + reaction.source_page : ''}` : ''],
  ].filter(([, v]) => v && String(v).trim());
  if (!detailRows.length && !reaction.reaction_name) return null;
  return <div className="reaction-details">
    {reaction.reaction_name && <div className="reaction-name-bottom">{reaction.reaction_name}</div>}
    {detailRows.map(([k, v]) => <div className="tiny-note" key={k}><b>{k}:</b> {v}</div>)}
  </div>;
}

const elements = [
 ['H',1,1,'s'],['He',18,1,'p'],['Li',1,2,'s'],['Be',2,2,'s'],['B',13,2,'p'],['C',14,2,'p'],['N',15,2,'p'],['O',16,2,'p'],['F',17,2,'p'],['Ne',18,2,'p'],
 ['Na',1,3,'s'],['Mg',2,3,'s'],['Al',13,3,'p'],['Si',14,3,'p'],['P',15,3,'p'],['S',16,3,'p'],['Cl',17,3,'p'],['Ar',18,3,'p'],
 ['K',1,4,'s'],['Ca',2,4,'s'],['Sc',3,4,'d'],['Ti',4,4,'d'],['V',5,4,'d'],['Cr',6,4,'d'],['Mn',7,4,'d'],['Fe',8,4,'d'],['Co',9,4,'d'],['Ni',10,4,'d'],['Cu',11,4,'d'],['Zn',12,4,'d'],['Ga',13,4,'p'],['Ge',14,4,'p'],['As',15,4,'p'],['Se',16,4,'p'],['Br',17,4,'p'],['Kr',18,4,'p'],
 ['Rb',1,5,'s'],['Sr',2,5,'s'],['Y',3,5,'d'],['Zr',4,5,'d'],['Nb',5,5,'d'],['Mo',6,5,'d'],['Tc',7,5,'d'],['Ru',8,5,'d'],['Rh',9,5,'d'],['Pd',10,5,'d'],['Ag',11,5,'d'],['Cd',12,5,'d'],['In',13,5,'p'],['Sn',14,5,'p'],['Sb',15,5,'p'],['Te',16,5,'p'],['I',17,5,'p'],['Xe',18,5,'p'],
 ['Cs',1,6,'s'],['Ba',2,6,'s'],['La-Lu',3,6,'f'],['Hf',4,6,'d'],['Ta',5,6,'d'],['W',6,6,'d'],['Re',7,6,'d'],['Os',8,6,'d'],['Ir',9,6,'d'],['Pt',10,6,'d'],['Au',11,6,'d'],['Hg',12,6,'d'],['Tl',13,6,'p'],['Pb',14,6,'p'],['Bi',15,6,'p'],['Po',16,6,'p'],['At',17,6,'p'],['Rn',18,6,'p'],
 ['Fr',1,7,'s'],['Ra',2,7,'s'],['Ac-Lr',3,7,'f'],['Rf',4,7,'d'],['Db',5,7,'d'],['Sg',6,7,'d'],['Bh',7,7,'d'],['Hs',8,7,'d'],['Mt',9,7,'d'],['Ds',10,7,'d'],['Rg',11,7,'d'],['Cn',12,7,'d'],['Nh',13,7,'p'],['Fl',14,7,'p'],['Mc',15,7,'p'],['Lv',16,7,'p'],['Ts',17,7,'p'],['Og',18,7,'p'],
];
const lan = ['La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu'];
const act = ['Ac','Th','Pa','U','Np','Pu','Am','Cm','Bk','Cf','Es','Fm','Md','No','Lr'];
function PeriodicTable({ onPick }) {
  return <section className="card periodic-card"><h2>Интерактивная таблица Менделеева</h2>
    <div className="periodic-grid">{elements.map(([s, g, p, block]) => <button key={s} className={`el el-${block}`} style={{gridColumn:g, gridRow:p}} onClick={() => onPick(s.includes('-') ? s.split('-')[0] : s)}>{s}</button>)}</div>
    <div className="f-block"><span>Лантаноиды</span>{lan.map(s => <button key={s} className="el el-f" onClick={() => onPick(s)}>{s}</button>)}</div>
    <div className="f-block"><span>Актиноиды</span>{act.map(s => <button key={s} className="el el-f" onClick={() => onPick(s)}>{s}</button>)}</div>
    <div className="legend"><span className="el-s">s-блок</span><span className="el-p">p-блок</span><span className="el-d">d-блок</span><span className="el-f">f-блок</span></div>
  </section>;
}

function App() {
  const [q, setQ] = useState('');
  const [reactions, setReactions] = useState([]);
  const [ads, setAds] = useState([]);
  const [loading, setLoading] = useState(false);
  const hasQuery = useMemo(() => q.trim().length > 0, [q]);
  async function loadAds() { const data = await fetch(`${API}/ads?placement=top`).then(r => r.json()).catch(() => []); setAds(Array.isArray(data) ? data : []); }
  useEffect(() => { loadAds(); }, []);
  useEffect(() => {
    const query = q.trim();
    if (!query) { setReactions([]); return; }
    const t = setTimeout(async () => {
      setLoading(true);
      const data = await fetch(`${API}/reactions?q=${encodeURIComponent(query)}`).then(r => r.json()).catch(() => []);
      setReactions(Array.isArray(data) ? data : []); setLoading(false);
    }, 250);
    return () => clearTimeout(t);
  }, [q]);
  return <>
    <header className="header"><div className="header-inner"><b>ChemHub</b><span>Поиск химических реакций</span></div></header>
    <main className="container">
      <section className="card hero-card"><h1>Химический справочник реакций</h1><p>Введите реагент(ы), продукт, условие, катализатор или название реакции.</p><div className="search-row"><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Введите реагент(ы)" autoFocus /></div></section>
      <PeriodicTable onPick={(s)=>setQ(s)} />
      {ads.length ? ads.map(ad => <div className="ad" key={ad.id} dangerouslySetInnerHTML={{__html: ad.html || ad.title}} />) : <div className="ad">Место для рекламы</div>}
      <section className="card"><h2>Найденные реакции</h2>{loading && <p>Поиск...</p>}{!hasQuery && <p>Начните вводить запрос, чтобы увидеть реакции.</p>}{hasQuery && !loading && reactions.length === 0 && <p>Ничего не найдено.</p>}{reactions.map(r => <article className="reaction-card" key={r.id}><div className="reaction-card-head"><h3><a className="reaction-link" href={reactionUrl(r)}>{r.reaction_name || 'Химическая реакция'}</a></h3>{r.confidence_score !== undefined && <span className="score">Точность: {Math.round((r.confidence_score || 0) * 100)}%</span>}</div><a className="equation-link" href={reactionUrl(r)}><ReactionEquation reaction={r}/></a><ReactionDetails reaction={r}/><div className="grid muted"><div><b>Реагенты:</b> {r.reactants}</div><div><b>Продукты:</b> {r.products || (r.impossible_note || '')}</div></div></article>)}</section>
    </main><footer className="footer">Создатель проекта: Telegram @brovler228. По рекламе, сотрудничеству и исправлениям реакций: @brovler228 · <a href="/sitemap.xml">sitemap.xml</a></footer>
  </>;
}

createRoot(document.getElementById('root')).render(<App />);
