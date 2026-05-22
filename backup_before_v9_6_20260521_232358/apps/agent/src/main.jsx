import React, {useEffect, useMemo, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './styles.css';

const API = 'http://localhost:8000';

function normalizeEquation(value){
  return String(value || '')
    .replaceAll('->','→')
    .replaceAll('=>','→')
    .replaceAll('<->','⇌')
    .replaceAll('<=>','⇌')
    .replace(/\s+/g,' ')
    .replace(/\s*([+→⇌])\s*/g,' $1 ')
    .trim();
}

function pageLabel(r){
  return r?.source_page ? `стр. ${r.source_page}` : '';
}

function ReactionCard({r, i, selected, onSelected, onUpdate, onSave, onPublish}){
  return <article className="reaction" key={r.id || i}>
    <div className="reaction-head">
      <label className="check"><input type="checkbox" checked={!!selected} onChange={e=>onSelected(e.target.checked)}/> выбрать</label>
      <span className="badge">{pageLabel(r)}</span>
      {r.confidence_score !== undefined && <span className="badge">confidence {Number(r.confidence_score).toFixed(2)}</span>}
    </div>
    <input value={r.reaction_name || ''} onChange={e=>onUpdate('reaction_name', e.target.value)} placeholder="Название реакции"/>
    <textarea value={r.equation || ''} onChange={e=>onUpdate('equation', normalizeEquation(e.target.value))} placeholder="Уравнение"/>
    <div className="grid">
      <input value={r.temperature || ''} onChange={e=>onUpdate('temperature', e.target.value)} placeholder="Температура"/>
      <input value={r.catalysts || ''} onChange={e=>onUpdate('catalysts', e.target.value)} placeholder="Катализаторы"/>
      <input value={r.conditions || ''} onChange={e=>onUpdate('conditions', e.target.value)} placeholder="Условия"/>
      <input value={r.pressure || ''} onChange={e=>onUpdate('pressure', e.target.value)} placeholder="Давление"/>
    </div>
    <div className="actions">
      <button onClick={onSave}>Сохранить правки</button>
      <button onClick={onPublish}>Загрузить эту реакцию</button>
    </div>
  </article>;
}

function App(){
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [job, setJob] = useState(null);
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState({});

  async function upload(e){
    e?.preventDefault();
    setErr('');
    if(!file){ setErr('Выбери PDF-файл'); return; }
    try{
      setBusy(true);
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`${API}/agent/upload`, {method:'POST', body:form});
      if(!res.ok) throw new Error(await res.text());
      const j = await res.json();
      setJob(j);
      setItems([]);
      setSelected({});
    }catch(ex){
      setErr('Ошибка загрузки PDF: ' + (ex?.message || ex));
    }finally{
      setBusy(false);
    }
  }

  async function load(){
    if(!job?.id) return;
    try{
      const [jRes, rRes] = await Promise.all([
        fetch(`${API}/agent/jobs/${job.id}`),
        fetch(`${API}/agent/jobs/${job.id}/reactions`)
      ]);
      if(jRes.ok){
        const j = await jRes.json();
        setJob(j);
      }
      if(rRes.ok){
        const rs = await rRes.json();
        const arr = Array.isArray(rs) ? rs : [];
        setItems(arr);
        setSelected(prev=>{
          const next = {...prev};
          arr.forEach(x=>{ if(next[x.id] === undefined) next[x.id] = true; });
          return next;
        });
      }
    }catch(ex){
      setErr('Ошибка обновления статуса: ' + (ex?.message || ex));
    }
  }

  useEffect(()=>{
    if(!job?.id) return;
    load();
    const timer = setInterval(load, 1500);
    return ()=>clearInterval(timer);
  }, [job?.id]);

  function upd(i,k,v){
    const next = [...items];
    next[i] = {...next[i], [k]: k === 'equation' ? normalizeEquation(v) : v};
    setItems(next);
  }

  async function save(r){
    await fetch(`${API}/agent/job-reactions/${r.id}`, {
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({...r, equation:normalizeEquation(r.equation), selected:selected[r.id] ?? true})
    });
    await load();
  }

  async function publish(ids){
    const clean = ids.filter(Boolean);
    if(!clean.length) return alert('Не выбраны реакции');
    await fetch(`${API}/agent/publish`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(clean)
    });
    alert('Реакции отправлены на сайт');
    await load();
  }

  const selectedIds = useMemo(()=>items.filter(x=>selected[x.id]).map(x=>x.id), [items, selected]);
  const isProcessing = job && !['completed','failed'].includes(job.status);

  return <main className="page">
    <section className="card">
      <h1>AI-агент обработки PDF</h1>
      <form onSubmit={upload} className="upload">
        <input type="file" accept="application/pdf,.pdf" onChange={e=>setFile(e.target.files?.[0] || null)}/>
        <button type="submit" disabled={busy}>{busy ? 'Загрузка...' : 'Загрузить PDF'}</button>
      </form>
      {err && <p className="error">{err}</p>}
      {job && <div className="status">
        <h2>Прогресс</h2>
        <p><b>{job.status}</b>: {job.message}</p>
        <progress value={job.progress_percent || 0} max="100"/>
        <p>{job.progress_percent || 0}% · страниц: {job.processed_pages || 0}/{job.total_pages || 0} · найдено реакций: {items.length}</p>
        {isProcessing && <p className="hint">Результаты обновляются автоматически каждые 1.5 секунды.</p>}
      </div>}
    </section>

    {items.length > 0 && <section className="card">
      <div className="list-head">
        <h2>Извлечённые реакции в реальном времени</h2>
        <div>
          <button onClick={()=>publish(selectedIds)}>Загрузить выбранные</button>
          <button onClick={()=>publish(items.map(x=>x.id))}>Загрузить все</button>
        </div>
      </div>
      {items.map((r,i)=><ReactionCard
        key={r.id || i}
        r={r}
        i={i}
        selected={!!selected[r.id]}
        onSelected={checked=>setSelected({...selected, [r.id]: checked})}
        onUpdate={(k,v)=>upd(i,k,v)}
        onSave={()=>save(r)}
        onPublish={()=>publish([r.id])}
      />)}
    </section>}
  </main>;
}

createRoot(document.getElementById('root')).render(<App/>);
