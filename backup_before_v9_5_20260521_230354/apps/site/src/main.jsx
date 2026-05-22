import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = 'http://localhost:8000';

const ELEMENTS = [
  [1,'H','Водород',1,1,'s'],[2,'He','Гелий',1,18,'p'],
  [3,'Li','Литий',2,1,'s'],[4,'Be','Бериллий',2,2,'s'],[5,'B','Бор',2,13,'p'],[6,'C','Углерод',2,14,'p'],[7,'N','Азот',2,15,'p'],[8,'O','Кислород',2,16,'p'],[9,'F','Фтор',2,17,'p'],[10,'Ne','Неон',2,18,'p'],
  [11,'Na','Натрий',3,1,'s'],[12,'Mg','Магний',3,2,'s'],[13,'Al','Алюминий',3,13,'p'],[14,'Si','Кремний',3,14,'p'],[15,'P','Фосфор',3,15,'p'],[16,'S','Сера',3,16,'p'],[17,'Cl','Хлор',3,17,'p'],[18,'Ar','Аргон',3,18,'p'],
  [19,'K','Калий',4,1,'s'],[20,'Ca','Кальций',4,2,'s'],[21,'Sc','Скандий',4,3,'d'],[22,'Ti','Титан',4,4,'d'],[23,'V','Ванадий',4,5,'d'],[24,'Cr','Хром',4,6,'d'],[25,'Mn','Марганец',4,7,'d'],[26,'Fe','Железо',4,8,'d'],[27,'Co','Кобальт',4,9,'d'],[28,'Ni','Никель',4,10,'d'],[29,'Cu','Медь',4,11,'d'],[30,'Zn','Цинк',4,12,'d'],[31,'Ga','Галлий',4,13,'p'],[32,'Ge','Германий',4,14,'p'],[33,'As','Мышьяк',4,15,'p'],[34,'Se','Селен',4,16,'p'],[35,'Br','Бром',4,17,'p'],[36,'Kr','Криптон',4,18,'p'],
  [37,'Rb','Рубидий',5,1,'s'],[38,'Sr','Стронций',5,2,'s'],[39,'Y','Иттрий',5,3,'d'],[40,'Zr','Цирконий',5,4,'d'],[41,'Nb','Ниобий',5,5,'d'],[42,'Mo','Молибден',5,6,'d'],[43,'Tc','Технеций',5,7,'d'],[44,'Ru','Рутений',5,8,'d'],[45,'Rh','Родий',5,9,'d'],[46,'Pd','Палладий',5,10,'d'],[47,'Ag','Серебро',5,11,'d'],[48,'Cd','Кадмий',5,12,'d'],[49,'In','Индий',5,13,'p'],[50,'Sn','Олово',5,14,'p'],[51,'Sb','Сурьма',5,15,'p'],[52,'Te','Теллур',5,16,'p'],[53,'I','Иод',5,17,'p'],[54,'Xe','Ксенон',5,18,'p'],
  [55,'Cs','Цезий',6,1,'s'],[56,'Ba','Барий',6,2,'s'],[57,'La','Лантан',8,3,'f'],[58,'Ce','Церий',8,4,'f'],[59,'Pr','Празеодим',8,5,'f'],[60,'Nd','Неодим',8,6,'f'],[61,'Pm','Прометий',8,7,'f'],[62,'Sm','Самарий',8,8,'f'],[63,'Eu','Европий',8,9,'f'],[64,'Gd','Гадолиний',8,10,'f'],[65,'Tb','Тербий',8,11,'f'],[66,'Dy','Диспрозий',8,12,'f'],[67,'Ho','Гольмий',8,13,'f'],[68,'Er','Эрбий',8,14,'f'],[69,'Tm','Тулий',8,15,'f'],[70,'Yb','Иттербий',8,16,'f'],[71,'Lu','Лютеций',8,17,'f'],
  [72,'Hf','Гафний',6,4,'d'],[73,'Ta','Тантал',6,5,'d'],[74,'W','Вольфрам',6,6,'d'],[75,'Re','Рений',6,7,'d'],[76,'Os','Осмий',6,8,'d'],[77,'Ir','Иридий',6,9,'d'],[78,'Pt','Платина',6,10,'d'],[79,'Au','Золото',6,11,'d'],[80,'Hg','Ртуть',6,12,'d'],[81,'Tl','Таллий',6,13,'p'],[82,'Pb','Свинец',6,14,'p'],[83,'Bi','Висмут',6,15,'p'],[84,'Po','Полоний',6,16,'p'],[85,'At','Астат',6,17,'p'],[86,'Rn','Радон',6,18,'p'],
  [87,'Fr','Франций',7,1,'s'],[88,'Ra','Радий',7,2,'s'],[89,'Ac','Актиний',9,3,'f'],[90,'Th','Торий',9,4,'f'],[91,'Pa','Протактиний',9,5,'f'],[92,'U','Уран',9,6,'f'],[93,'Np','Нептуний',9,7,'f'],[94,'Pu','Плутоний',9,8,'f'],[95,'Am','Америций',9,9,'f'],[96,'Cm','Кюрий',9,10,'f'],[97,'Bk','Берклий',9,11,'f'],[98,'Cf','Калифорний',9,12,'f'],[99,'Es','Эйнштейний',9,13,'f'],[100,'Fm','Фермий',9,14,'f'],[101,'Md','Менделевий',9,15,'f'],[102,'No','Нобелий',9,16,'f'],[103,'Lr','Лоуренсий',9,17,'f'],
  [104,'Rf','Резерфордий',7,4,'d'],[105,'Db','Дубний',7,5,'d'],[106,'Sg','Сиборгий',7,6,'d'],[107,'Bh','Борий',7,7,'d'],[108,'Hs','Хассий',7,8,'d'],[109,'Mt','Мейтнерий',7,9,'d'],[110,'Ds','Дармштадтий',7,10,'d'],[111,'Rg','Рентгений',7,11,'d'],[112,'Cn','Коперниций',7,12,'d'],[113,'Nh','Нихоний',7,13,'p'],[114,'Fl','Флеровий',7,14,'p'],[115,'Mc','Московий',7,15,'p'],[116,'Lv','Ливерморий',7,16,'p'],[117,'Ts','Теннессин',7,17,'p'],[118,'Og','Оганесон',7,18,'p'],
];

function slugifyReaction(r) {
  const raw = String(r.reaction_name || r.equation || `reaction-${r.id}`).toLowerCase()
    .replace(/→|⇌|->|<->|=>/g, '-').replace(/[^a-zа-яё0-9]+/gi, '-')
    .replace(/-+/g, '-').replace(/^-|-$/g, '').slice(0, 90) || 'reaction';
  return `${r.id}-${raw}`;
}
function reactionUrl(r) { return `/reaction/${slugifyReaction(r)}`; }
function normalizeEquation(text = '') {
  return String(text).replace(/<->|⇄|↔|⇌/g, '⇌').replace(/=>|->|⟶|→/g, '→').replace(/[;,.:\s]+$/g, '').trim();
}

function chemNodes(text = '') {
  const out = [];
  const s = String(text);
  for (let i=0; i<s.length; i++) {
    const ch = s[i], prev = s[i-1] || '', next = s[i+1] || '';
    if (/\d/.test(ch)) {
      let num = ch;
      while (i+1<s.length && /\d/.test(s[i+1])) { i++; num += s[i]; }
      const before = prev;
      const after = s[i+1] || '';
      if (before === '^' || after === '+' || after === '-' || after === '−') {
        if (before === '^' && out.length) out.pop();
        let sign = '';
        if (after === '+' || after === '-' || after === '−') { sign = after === '−' ? '−' : after; i++; }
        out.push(<sup className="chem-super" key={out.length}>{num}{sign}</sup>);
      } else if (/[A-Za-zА-Яа-я\]\)]/.test(before)) {
        out.push(<sub className="chem-sub" key={out.length}>{num}</sub>);
      } else {
        out.push(num);
      }
    } else if ((ch === '+' || ch === '-' || ch === '−') && (prev === ']' || /\d/.test(prev)) && (next === ' ' || next === '' || next === ',')) {
      out.push(<sup className="chem-super" key={out.length}>{ch === '−' ? '−' : ch}</sup>);
    } else {
      out.push(ch);
    }
  }
  return out;
}

function MoleculePart({ text }) {
  const raw = String(text || '').trim();
  const m = raw.match(/^(.+?)(?:\s*\(([^()]*)\)|\s+(конц\.|разб\.|тв\.|ж\.|газ|р-р|водн\.|красно-коричневый|белый|черный|чёрный|желтый|жёлтый))$/i);
  if (m) {
    return <span className="mol-note-wrap"><span>{chemNodes(m[1].trim())}</span><small>{m[2] || m[3]}</small></span>;
  }
  return <span>{chemNodes(raw)}</span>;
}

function ChemSide({ side }) {
  const parts = String(side || '').split(/\s+\+\s+/);
  return <span className="chem-side">{parts.map((p,i)=><React.Fragment key={i}>{i>0 && <span className="plus"> + </span>}<MoleculePart text={p}/></React.Fragment>)}</span>;
}

function buildArrowLabel(r) {
  const vals = [r.temperature, r.pressure, r.conditions, r.catalysts, r.solvents, r.states]
    .filter(Boolean).map(x=>String(x).trim()).filter(Boolean);
  return [...new Set(vals.join('; ').split(/\s*;\s*/).filter(Boolean))].join(', ');
}

function ReactionEquation({ reaction }) {
  const normalized = normalizeEquation(reaction.equation || '');
  const arrow = normalized.includes('⇌') ? '⇌' : (normalized.includes('≠') ? '≠' : '→');
  const parts = normalized.split(arrow);
  if (parts.length < 2) return <div className="reaction-equation"><ChemSide side={normalized}/></div>;
  const label = buildArrowLabel(reaction);
  return (
    <div className="reaction-equation">
      <ChemSide side={parts[0]} />
      <span className="arrow-stack">
        {label && <span className="arrow-label">{label}</span>}
        <span className={`chem-arrow ${arrow==='⇌'?'reversible':''}`}>{arrow}</span>
      </span>
      <ChemSide side={parts.slice(1).join(arrow)} />
    </div>
  );
}

function PeriodicTable({ onPick }) {
  return <section className="card"><h2>Интерактивная таблица Менделеева</h2>
    <div className="pt-legend"><span className="block-s">s-блок</span><span className="block-p">p-блок</span><span className="block-d">d-блок</span><span className="block-f">f-блок</span></div>
    <div className="periodic-table">
      {ELEMENTS.map(([num,sym,name,row,col,block]) => (
        <button key={num} title={`${num}. ${name}`} className={`element block-${block}`} style={{gridRow: row, gridColumn: col}} onClick={()=>onPick(sym)}>
          <small>{num}</small><b>{sym}</b>
        </button>
      ))}
      <div className="series-label lanth" style={{gridRow:8, gridColumn:'1 / span 2'}}>Лантаноиды</div>
      <div className="series-label act" style={{gridRow:9, gridColumn:'1 / span 2'}}>Актиноиды</div>
    </div>
  </section>
}

function App() {
  const [q, setQ] = useState('');
  const [reactions, setReactions] = useState([]);
  const [ads, setAds] = useState([]);
  const [loading, setLoading] = useState(false);
  const hasQuery = useMemo(() => q.trim().length > 0, [q]);

  useEffect(() => { fetch(`${API}/ads?placement=top`).then(r=>r.json()).then(d=>setAds(Array.isArray(d)?d:[])).catch(()=>setAds([])); }, []);
  useEffect(() => {
    const query = q.trim();
    if (!query) { setReactions([]); return; }
    const t = setTimeout(async () => {
      setLoading(true);
      const data = await fetch(`${API}/reactions?q=${encodeURIComponent(query)}`).then(r=>r.json()).catch(()=>[]);
      setReactions(Array.isArray(data) ? data.filter(x=>!x.hidden) : []);
      setLoading(false);
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  return <main>
    <header className="header"><div className="header-inner"><strong>ChemHub</strong><span>Поиск химических реакций</span></div></header>
    <div className="container">
      <section className="card hero-card">
        <h1>Поиск химических реакций</h1>
        <p className="hint">Введите реагент(ы), продукт, условие, катализатор или название реакции.</p>
        <div className="search-row"><input value={q} placeholder="Введите реагент(ы)" onChange={e=>setQ(e.target.value)} autoFocus /></div>
      </section>

      <PeriodicTable onPick={(sym)=>setQ(sym)} />

      {ads.length ? ads.map((ad)=><div className="ad" key={ad.id}>{ad.text || ad.title}</div>) : <div className="ad">Место для рекламы</div>}

      <section className="card">
        <h2>Найденные реакции</h2>
        {loading && <p>Поиск...</p>}
        {!hasQuery && <p className="hint">Начните вводить запрос, чтобы увидеть реакции.</p>}
        {hasQuery && !loading && reactions.length === 0 && <p className="hint">Ничего не найдено.</p>}
        {reactions.map((r)=>(
          <article className="reaction-card" key={r.id}>
            <div className="reaction-card-head">
              <a className="reaction-link" href={reactionUrl(r)}><h3>{r.reaction_name || 'Химическая реакция'}</h3></a>
              {r.confidence_score !== undefined && <span className="score">Точность: {Math.round((r.confidence_score || 0) * 100)}%</span>}
            </div>
            <a className="equation-link" href={reactionUrl(r)}><ReactionEquation reaction={r}/></a>
            {r.reaction_name && <div className="reaction-name-bottom">Название реакции: <b>{r.reaction_name}</b></div>}
            {r.impossible_note && <div className="warn badge">{r.impossible_note}</div>}
          </article>
        ))}
      </section>
    </div>
    <footer className="footer">Создатель проекта: Telegram @brovler228. По рекламе, сотрудничеству и исправлениям реакций: @brovler228 · <a href="/sitemap.xml">sitemap.xml</a></footer>
  </main>
}

createRoot(document.getElementById('root')).render(<App />);
