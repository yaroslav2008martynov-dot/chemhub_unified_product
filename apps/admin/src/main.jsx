import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = 'http://localhost:8000';

const blank = () => ({
  reaction_name: '',
  equation: '',
  reactants: '',
  products: '',
  conditions: '',
  catalysts: '',
  solvents: '',
  temperature: '',
  pressure: '',
  states: '',
  source_pdf: '',
  source_page: 0,
  confidence_score: 1,
  validation_status: 'manual',
  approved: true,
  hidden: false,
});

function normEq(text = '') {
  return String(text)
    .replace(/<->|↔|⇄|⇌/g, '⇌')
    .replace(/=>|->|⟶|→/g, '→')
    .trim();
}

function Preview({ r }) {
  const eq = normEq(r.equation || '');
  const arrow = eq.includes('⇌') ? '⇌' : (eq.includes('≠') ? '≠' : '→');
  const parts = eq.split(arrow);
  const cond = [r.conditions, r.temperature, r.pressure, r.catalysts && `кат. ${r.catalysts}`, r.solvents && `раств. ${r.solvents}`]
    .filter(Boolean)
    .join(' · ');
  if (parts.length < 2) return <div className="preview">{eq || 'Предпросмотр реакции'}</div>;
  return (
    <div className="preview">
      <span>{parts[0].trim()}</span>
      <span className="arrow"><small>{cond}</small>{arrow}</span>
      <span>{parts.slice(1).join(arrow).trim()}</span>
    </div>
  );
}

function App() {
  const [password, setPassword] = useState('');
  const [token, setToken] = useState(localStorage.getItem('adminToken') || '');
  const [form, setForm] = useState(blank());
  const [reactions, setReactions] = useState([]);
  const [sources, setSources] = useState([]);
  const [selectedPdf, setSelectedPdf] = useState('');
  const [err, setErr] = useState('');
  const equationRef = useRef(null);
  const headers = useMemo(() => ({ 'Content-Type': 'application/json', 'x-admin-token': token }), [token]);

  async function login(e) {
    e?.preventDefault();
    setErr('');
    try {
      const res = await fetch(`${API}/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) throw new Error('Неверный пароль');
      const data = await res.json();
      localStorage.setItem('adminToken', data.token);
      setToken(data.token);
    } catch (ex) {
      setErr(ex.message || String(ex));
    }
  }

  async function load() {
    const data = await fetch(`${API}/reactions?include_hidden=true`).then(r => r.json()).catch(() => []);
    setReactions(Array.isArray(data) ? data : []);
    const src = await fetch(`${API}/admin/source-pdfs`, { headers: { 'x-admin-token': token } }).then(r => r.json()).catch(() => []);
    setSources(Array.isArray(src) ? src : []);
  }

  useEffect(() => { if (token) load(); }, [token]);

  function insertArrow(a) {
    const inp = equationRef.current;
    const sep = ` ${a} `;
    const start = inp?.selectionStart ?? form.equation.length;
    const end = inp?.selectionEnd ?? form.equation.length;
    const next = form.equation.slice(0, start) + sep + form.equation.slice(end);
    setForm({ ...form, equation: next });
    setTimeout(() => {
      inp?.focus();
      inp?.setSelectionRange(start + sep.length, start + sep.length);
    }, 0);
  }

  async function save(e) {
    e?.preventDefault();
    if (!form.equation.trim()) return alert('Введите уравнение');
    const method = form.id ? 'PUT' : 'POST';
    const url = form.id ? `${API}/admin/reactions/${form.id}` : `${API}/admin/reactions`;
    const res = await fetch(url, {
      method,
      headers,
      body: JSON.stringify({
        ...form,
        equation: normEq(form.equation),
        source_page: Number(form.source_page || 0),
        confidence_score: Number(form.confidence_score || 0),
      }),
    });
    if (!res.ok) return alert(await res.text());
    setForm(blank());
    await load();
  }

  async function del(id) {
    if (!confirm('Удалить реакцию?')) return;
    await fetch(`${API}/admin/reactions/${id}`, { method: 'DELETE', headers: { 'x-admin-token': token } });
    await load();
  }

  async function deleteByPdf() {
    if (!selectedPdf) return alert('Выбери PDF-файл');
    const row = sources.find(x => x.source_pdf === selectedPdf);
    const count = row?.count ?? '?';
    if (!confirm(`Удалить все реакции из PDF "${selectedPdf}"? Количество: ${count}. Это действие нельзя отменить одной кнопкой.`)) return;
    const res = await fetch(`${API}/admin/delete-by-source-pdf`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ source_pdf: selectedPdf }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return alert(JSON.stringify(data));
    alert(`Удалено реакций: ${data.deleted || 0}`);
    setSelectedPdf('');
    await load();
  }

  if (!token) {
    return (
      <main className="page">
        <section className="card login">
          <h1>Скрытая админ-панель ChemHub</h1>
          <form onSubmit={login}>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Пароль администратора" autoFocus />
            <button type="submit">Войти</button>
          </form>
          {err && <p className="error">{err}</p>}
        </section>
      </main>
    );
  }

  return (
    <main className="page">
      <header>
        <h1>Owner Admin</h1>
        <button onClick={() => { localStorage.removeItem('adminToken'); setToken(''); }}>Выйти</button>
      </header>

      <section className="card">
        <h2>Удалить реакции из PDF</h2>
        <p>Используй это, если PDF был обработан криво и нужно убрать все опубликованные реакции из этого файла.</p>
        <div className="grid">
          <select value={selectedPdf} onChange={e => setSelectedPdf(e.target.value)}>
            <option value="">Выбери PDF</option>
            {sources.map(s => <option key={s.source_pdf} value={s.source_pdf}>{s.source_pdf} — {s.count}</option>)}
          </select>
          <button className="danger" type="button" onClick={deleteByPdf}>Удалить все реакции из выбранного PDF</button>
        </div>
      </section>

      <section className="card">
        <h2>{form.id ? 'Редактировать реакцию' : 'Добавить реакцию вручную'}</h2>
        <form onSubmit={save}>
          <label>Название реакции</label>
          <input value={form.reaction_name} onChange={e => setForm({ ...form, reaction_name: e.target.value })} />

          <label>Уравнение</label>
          <div>
            <button type="button" onClick={() => insertArrow('→')}>→</button>
            <button type="button" onClick={() => insertArrow('⇌')}>⇌</button>
            <button type="button" onClick={() => insertArrow('⚡→')}>⚡→</button>
          </div>
          <textarea ref={equationRef} value={form.equation} onChange={e => setForm({ ...form, equation: e.target.value })} placeholder="2Na + 2H2O → 2NaOH + H2↑" />
          <Preview r={form} />

          <div className="grid">
            <input value={form.reactants} onChange={e => setForm({ ...form, reactants: e.target.value })} placeholder="Реагенты" />
            <input value={form.products} onChange={e => setForm({ ...form, products: e.target.value })} placeholder="Продукты" />
            <input value={form.conditions} onChange={e => setForm({ ...form, conditions: e.target.value })} placeholder="Условия" />
            <input value={form.catalysts} onChange={e => setForm({ ...form, catalysts: e.target.value })} placeholder="Катализатор" />
            <input value={form.temperature} onChange={e => setForm({ ...form, temperature: e.target.value })} placeholder="Температура" />
            <input value={form.pressure} onChange={e => setForm({ ...form, pressure: e.target.value })} placeholder="Давление" />
            <input value={form.source_pdf} onChange={e => setForm({ ...form, source_pdf: e.target.value })} placeholder="PDF-источник" />
          </div>

          <label><input type="checkbox" checked={!!form.approved} onChange={e => setForm({ ...form, approved: e.target.checked })} /> Опубликовать</label>
          <label><input type="checkbox" checked={!!form.hidden} onChange={e => setForm({ ...form, hidden: e.target.checked })} /> Скрыть</label>
          <button type="submit">Сохранить реакцию</button>
          <button type="button" onClick={() => setForm(blank())}>Очистить</button>
        </form>
      </section>

      <section className="card">
        <h2>Все реакции</h2>
        {reactions.map(r => (
          <article key={r.id} className="reaction">
            <b>{r.reaction_name || r.equation}</b>
            <Preview r={r} />
            {r.source_pdf && <small>PDF: {r.source_pdf}{r.source_page ? `, стр. ${r.source_page}` : ''}</small>}
            <div>
              <button onClick={() => setForm({ ...blank(), ...r })}>Редактировать</button>
              <button className="danger" onClick={() => del(r.id)}>Удалить</button>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);
