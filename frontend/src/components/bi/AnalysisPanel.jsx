import { useEffect, useState } from 'react';
import { bi } from '../../services/biApi';
import { Alert, Badge, Button, Card, LABEL } from './ui';

function DecisionForm({ company, finding, members, onDecided }) {
  const [form, setForm] = useState({ status: 'APPROVED', reason: '', assignee_id: '', follow_up: finding.recommendation, due_date: '' });
  const [error, setError] = useState('');
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  async function submit(event) {
    event.preventDefault();
    setError('');
    try {
      await bi(`/companies/${company.id}/findings/${finding.id}/decisions`, { method: 'POST', body: {
        status: form.status, reason: form.reason, assignee_id: form.assignee_id ? Number(form.assignee_id) : null,
        follow_up: form.status === 'REJECTED' ? null : form.follow_up, due_date: form.due_date || null } });
      onDecided();
    } catch (e) { setError(e.message); }
  }
  if (!['OWNER', 'APPROVER'].includes(company.role)) return <p className="text-xs text-slate-500">결정은 OWNER·APPROVER 권한이 필요합니다. (현재: {company.role})</p>;
  return <form onSubmit={submit} className="mt-3 grid gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 md:grid-cols-2">
    <div className="flex gap-3 md:col-span-2" role="radiogroup" aria-label="관리자 결정">
      {['APPROVED', 'ON_HOLD', 'REJECTED'].map(s => <label key={s} className="flex items-center gap-1 text-sm">
        <input type="radio" name={`status-${finding.id}`} value={s} checked={form.status === s} onChange={set('status')} />{LABEL[s]}</label>)}
    </div>
    <label className="text-sm md:col-span-2">결정 사유
      <textarea required value={form.reason} onChange={set('reason')} rows={2} className="mt-1 w-full rounded border border-slate-300 px-2 py-1" /></label>
    <label className="text-sm">담당자
      <select value={form.assignee_id} onChange={set('assignee_id')} className="mt-1 w-full rounded border border-slate-300 px-2 py-1">
        <option value="">지정 안 함</option>{members.map(m => <option key={m.id} value={m.id}>{m.name} ({m.role})</option>)}</select></label>
    <label className="text-sm">기한<input type="date" value={form.due_date} onChange={set('due_date')} className="mt-1 w-full rounded border border-slate-300 px-2 py-1" /></label>
    {form.status !== 'REJECTED' && <label className="text-sm md:col-span-2">후속 조치
      <input value={form.follow_up} onChange={set('follow_up')} className="mt-1 w-full rounded border border-slate-300 px-2 py-1" /></label>}
    <div className="md:col-span-2"><Alert>{error}</Alert></div>
    <div><Button type="submit">결정 저장</Button></div>
  </form>;
}

function FindingCard({ company, finding, members, onDecided }) {
  const [open, setOpen] = useState(false);
  return <article className="rounded-xl border border-slate-200 bg-white p-4">
    <div className="flex flex-wrap items-center gap-2"><Badge value={finding.kind} /><Badge value={finding.status} />
      <span className="text-xs text-slate-500">중요도 {LABEL[finding.severity]}</span></div>
    <h4 className="mt-2 font-semibold text-slate-900">{finding.title}</h4>
    <ul className="mt-2 grid gap-1 text-sm sm:grid-cols-3">{finding.facts.map(f => <li key={f.label} className="rounded bg-slate-50 px-2 py-1">
      <span className="block text-xs text-slate-500">{f.label} · {f.period}</span><b className="tabular-nums">{f.display}</b>
      <span className="block text-[11px] text-slate-400">확인된 사실 · {f.source}</span></li>)}</ul>
    <p className="mt-2 text-sm text-slate-700"><b className="text-amber-700">AI 추론</b> {finding.inference}</p>
    <p className="text-sm text-slate-700"><b>AI 권고</b> {finding.recommendation}</p>
    <Button variant="secondary" className="mt-2" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? '근거 닫기' : '근거·검토사항 보기'}</Button>
    {open && <div className="mt-3 space-y-2 text-sm">
      <div><b>분석 근거 및 출처</b><ul className="list-disc pl-5">{finding.evidence.map((e, i) => <li key={i}>
        [{e.type === 'erp' ? 'ERP' : e.type === 'market' ? '금융' : '뉴스'}] {e.url ? <a href={e.url} target="_blank" rel="noreferrer" className="text-blue-700 hover:underline">{e.title}</a> : e.title}
        <span className="text-xs text-slate-500"> · {e.source} · {e.date?.slice(0, 10)}</span></li>)}</ul></div>
      <p><b>불확실성</b> {finding.uncertainty}</p>
      <div><b>관리자 검토 사항</b><ul className="list-disc pl-5">{finding.review_points.map(r => <li key={r}>{r}</li>)}</ul></div>
      <DecisionForm company={company} finding={finding} members={members} onDecided={onDecided} />
    </div>}
  </article>;
}

export default function AnalysisPanel({ company, members, onChanged }) {
  const [runs, setRuns] = useState([]);
  const [run, setRun] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const load = async (id) => {
    const list = await bi(`/companies/${company.id}/analyses`);
    setRuns(list);
    const target = id || list[0]?.id;
    setRun(target ? await bi(`/companies/${company.id}/analyses/${target}`) : null);
  };
  useEffect(() => { load().catch(e => setError(e.message)); }, [company.id]);
  async function analyze() {
    setBusy(true); setError('');
    try { const r = await bi(`/companies/${company.id}/analyses`, { method: 'POST' }); await load(r.id); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  return <div className="space-y-4">
    <Card title="AI 기회·위험 분석" actions={<div className="flex gap-2">
      {runs.length > 1 && <select aria-label="분석 이력" value={run?.id || ''} onChange={e => load(Number(e.target.value))} className="rounded border border-slate-300 px-2 text-sm">
        {runs.map(r => <option key={r.id} value={r.id}>#{r.id} · {r.period} · {new Date(r.created_at).toLocaleString('ko-KR')}</option>)}</select>}
      <Button onClick={analyze} disabled={busy || company.role === 'VIEWER'}>{busy ? '분석 중...' : '새 분석 실행'}</Button></div>}>
      <Alert>{error}</Alert>
      {run ? <>
        <p className="whitespace-pre-line text-sm text-slate-700">{run.narrative}</p>
        <p className="mt-2 text-xs text-slate-500">요약 생성: {run.narrative_source === 'llm' ? 'LLM (검증된 수치만 사용, 신규 수치 포함 시 자동 폐기)' : '템플릿 (LLM 미설정)'} · 수치 계산: SQL/Polars/scikit-learn</p>
      </> : <p className="text-sm text-slate-500">아직 분석 결과가 없습니다. ERP 데이터를 업로드한 뒤 분석을 실행하세요.</p>}
    </Card>
    {run?.findings.map(f => <FindingCard key={f.id} company={company} finding={f} members={members}
      onDecided={() => { load(run.id); onChanged(); }} />)}
  </div>;
}
