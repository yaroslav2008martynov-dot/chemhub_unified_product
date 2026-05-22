import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = 'http://localhost:8000';

function normalizeEquation(text = '') {
  return String(text)
    .replace(/<->|⇄|↔|⇌/g, '⇌')
    .replace(/=>|->|⟶|→/g, '→')
    .replace(/[;,.:\s]+$/g, '')
    .trim();
}

function App() {
  const [file, setFile] = useState(null);
  const [job, setJob] = useState(null);
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState({});
  const [dirty, setDirty] = useState({});
  const [feedback, setFeedback] = useState({});
  const [err, setErr] = useState('');
  const dirtyRef = useRef({});
  const itemsRef = useRef([]);

  useEffect(() => { dirtyRef.current = dirty; }, [dirty]);
  useEffect(() => { itemsRef.current = items; }, [items]);

  async function upload(e) {
    e?.preventDefault();
    setErr('');
    if (!file) return alert('Выбери PDF');
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`${API}/agent/upload`, { method: 'POST', body: form });
      if (!res.ok) throw new Error(await res.text());
      const nextJob = await res.json();
      setJob(nextJob);
      setItems([]);
      setSelected({});
      setDirty({});
      dirtyRef.current = {};
      itemsRef.current = [];
    } catch (ex) {
      setErr('Ошибка загрузки PDF: ' + (ex?.message || ex));
    }
  }

  async function load() {
    if (!job?.id) return;
    try {
      const j = await fetch(`${API}/agent/jobs/${job.id}`).then((r) => r.json());
      const rs = await fetch(`${API}/agent/jobs/${job.id}/reactions`).then((r) => r.json()).catch(() => []);
      setJob(j);

      const dirtyNow = dirtyRef.current || {};
      const localById = Object.fromEntries((itemsRef.current || []).map((x) => [x.id, x]));
      setItems((Array.isArray(rs) ? rs : []).map((serverItem) => {
        if (dirtyNow[serverItem.id] && localById[serverItem.id]) return localById[serverItem.id];
        return serverItem;
      }));

      setSelected((prev) => {
        const next = { ...prev };
        (Array.isArray(rs) ? rs : []).forEach((x) => { if (next[x.id] === undefined) next[x.id] = true; });
        return next;
      });
      setErr('');
    } catch (ex) {
      setErr('Ошибка обновления статуса: ' + (ex?.message || ex));
    }
  }

  useEffect(() => {
    if (!job?.id) return;
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [job?.id]);

  function update(i, key, value) {
    setItems((prev) => {
      const copy = [...prev];
      copy[i] = { ...copy[i], [key]: key === 'equation' ? normalizeEquation(value) : value };
      const id = copy[i]?.id;
      if (id !== undefined) {
        const nextDirty = { ...dirtyRef.current, [id]: true };
        dirtyRef.current = nextDirty;
        setDirty(nextDirty);
      }
      return copy;
    });
  }

  async function saveReaction(r) {
    const body = {
      reaction_name: r.reaction_name || '',
      equation: normalizeEquation(r.equation || ''),
      reactants: r.reactants || '',
      products: r.products || '',
      conditions: r.conditions || '',
      catalysts: r.catalysts || '',
      solvents: r.solvents || '',
      temperature: r.temperature || '',
      pressure: r.pressure || '',
      states: r.states || '',
      selected: selected[r.id] ?? true,
    };
    const res = await fetch(`${API}/agent/job-reactions/${r.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) return alert(await res.text());
    const next = { ...dirtyRef.current };
    delete next[r.id];
    dirtyRef.current = next;
    setDirty(next);
    await load();
  }

  async function checkInternet(r) {
    const updated = await fetch(`${API}/agent/job-reactions/${r.id}/internet-check`, { method: 'POST' }).then((res) => res.json());
    setItems(items.map((x) => (x.id === r.id ? updated : x)));
  }

  async function publish(ids) {
    const cleanIds = ids.filter(Boolean);
    if (!cleanIds.length) return alert('Не выбраны реакции');
    await fetch(`${API}/agent/publish`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(cleanIds),
    });
    alert('Реакции отправлены на сайт');
    await load();
  }

  async function sendFeedback(r) {
    const comment = feedback[r.id] || '';
    if (!comment.trim()) return alert('Напиши замечание');
    await fetch(`${API}/agent/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reaction_id: r.id, scope: 'extraction', comment, before_text: r.equation, after_text: '' }),
    });
    setFeedback({ ...feedback, [r.id]: '' });
    alert('Замечание сохранено');
  }

  return (
    <div>
      <header className="header"><div className="header-inner"><b>ChemHub AI Agent</b><span>Извлечение реакций из PDF</span></div></header>
      <main className="container">
        <section className="card hero-card">
          <h1>AI-агент обработки PDF</h1>
          <form className="search-row" onSubmit={upload}>
            <input type="file" accept="application/pdf,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            <button type="submit">Загрузить PDF</button>
          </form>
          {err && <p className="badge warn">{err}</p>}
          {job && <div>
            <h2>Прогресс</h2>
            <p>{job.status}: {job.message}</p>
            <div className="progress"><div style={{ width: `${job.progress_percent || 0}%` }} /></div>
            <p>{job.progress_percent || 0}% · страниц: {job.processed_pages || 0}/{job.total_pages || 0}</p>
          </div>}
        </section>

        {items.length > 0 && <section className="card">
          <h2>Извлечённые реакции</h2>
          <button onClick={() => publish(items.map((x) => x.id))}>Загрузить на сайт все</button>
          <button onClick={() => publish(items.filter((x) => selected[x.id]).map((x) => x.id))}>Загрузить выбранные</button>
          {items.map((r, i) => (
            <section className="card" key={r.id}>
              <label><input type="checkbox" checked={!!selected[r.id]} onChange={(e) => setSelected({ ...selected, [r.id]: e.target.checked })} /> выбрать</label>
              <input value={r.reaction_name || ''} onChange={(e) => update(i, 'reaction_name', e.target.value)} placeholder="Название реакции" />
              <textarea value={r.equation || ''} onChange={(e) => update(i, 'equation', e.target.value)} placeholder="Уравнение" />
              <input value={r.reactants || ''} onChange={(e) => update(i, 'reactants', e.target.value)} placeholder="Реагенты" />
              <input value={r.products || ''} onChange={(e) => update(i, 'products', e.target.value)} placeholder="Продукты" />
              <textarea value={r.conditions || ''} onChange={(e) => update(i, 'conditions', e.target.value)} placeholder="Условия над стрелкой" />
              <input value={r.catalysts || ''} onChange={(e) => update(i, 'catalysts', e.target.value)} placeholder="Катализаторы" />
              <input value={r.solvents || ''} onChange={(e) => update(i, 'solvents', e.target.value)} placeholder="Растворители" />
              <input value={r.temperature || ''} onChange={(e) => update(i, 'temperature', e.target.value)} placeholder="Температура" />
              <input value={r.pressure || ''} onChange={(e) => update(i, 'pressure', e.target.value)} placeholder="Давление" />
              <input value={r.states || ''} onChange={(e) => update(i, 'states', e.target.value)} placeholder="Состояния: Na(s), H2O(l)" />
              <div className="dev-box">
                <b>Панель проверки</b>
                <p>Интернет-проверка: {r.internet_status || 'not_checked'}</p>
                {r.internet_note && <p>{r.internet_note}</p>}
                <button onClick={() => checkInternet(r)}>Проверить аналог в интернете</button>
                <textarea value={feedback[r.id] || ''} onChange={(e) => setFeedback({ ...feedback, [r.id]: e.target.value })} placeholder="Опиши ошибку AI-агента" />
                <button className="secondary" onClick={() => sendFeedback(r)}>Сохранить замечание для донастройки</button>
              </div>
              {dirty[r.id] && <span className="badge warn">есть несохранённые правки</span>}
              <button onClick={() => saveReaction(r)}>Сохранить правки</button>
              <button className="good" onClick={() => publish([r.id])}>Загрузить эту реакцию на сайт</button>
              {r.published && <span className="badge">уже на сайте</span>}
            </section>
          ))}
        </section>}
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
