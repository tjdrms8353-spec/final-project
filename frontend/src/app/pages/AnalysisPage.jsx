import { useEffect, useState } from 'react';
import { AlertTriangle, BookOpen, Building2, CheckSquare, ExternalLink, Lightbulb, Newspaper, Play, TrendingUp } from 'lucide-react';
import { bi } from '../../services/biApi';
import { Alert, Badge, Button, Card, cx, dateKo, dateTimeKo, Empty, Field, LABEL, Loading, PageHeader } from '../ui';
import { go, useWorkspace } from '../workspace';

const FILTERS = [['all', '전체'], ['risk', '위험'], ['opportunity', '기회'], ['change', '변화'], ['PENDING', '검토 대기']];
const EVIDENCE_ICON = { erp: Building2, news: Newspaper, market: TrendingUp };

function Section({ icon: Icon, title, tag, children, tone = 'plain' }) {
  return <section className={cx('rounded-lg p-4', tone === 'ai' ? 'border border-brand-200 bg-brand-50/60' : tone === 'warn' ? 'border border-amber-200 bg-amber-50' : 'border border-slate-200 bg-white')}>
    <h3 className="mb-2.5 flex items-center gap-2 text-sm font-semibold text-slate-900">
      <Icon className="h-4 w-4 text-slate-500" aria-hidden="true" />{title}{tag && <span className="text-xs font-normal text-slate-500">{tag}</span>}</h3>
    {children}
  </section>;
}

function DecisionForm({ finding, onDone }) {
  const { company, members, can } = useWorkspace();
  const [form, setForm] = useState({ status: 'APPROVED', reason: '', assignee_id: '', follow_up: finding.recommendation, due_date: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => setForm(f => ({ ...f, follow_up: finding.recommendation, reason: '' })), [finding.id, finding.recommendation]);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  if (!can.decide) return <Alert tone="info">결정은 대표(OWNER)·승인권자(APPROVER)만 기록할 수 있습니다. 현재 권한: {LABEL[company.role]}</Alert>;
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      await bi(`/companies/${company.id}/findings/${finding.id}/decisions`, { method: 'POST', body: {
        status: form.status, reason: form.reason, assignee_id: form.assignee_id ? Number(form.assignee_id) : null,
        follow_up: form.status === 'REJECTED' ? null : form.follow_up, due_date: form.due_date || null } });
      onDone();
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <form onSubmit={submit} className="space-y-3">
    <div role="radiogroup" aria-label="관리자 결정" className="grid grid-cols-3 gap-2">
      {[['APPROVED', 'border-emerald-500 bg-emerald-50 text-emerald-800'], ['ON_HOLD', 'border-slate-500 bg-slate-100 text-slate-800'], ['REJECTED', 'border-red-500 bg-red-50 text-red-800']].map(([s, on]) =>
        <label key={s} className={cx('cursor-pointer rounded-lg border px-3 py-2 text-center text-sm font-medium transition', form.status === s ? on : 'border-slate-200 text-slate-600 hover:bg-slate-50')}>
          <input type="radio" className="sr-only" name={`status-${finding.id}`} value={s} checked={form.status === s} onChange={set('status')} />{LABEL[s]}</label>)}
    </div>
    <Field as="textarea" label="결정 사유 (필수)" required rows={2} value={form.reason} onChange={set('reason')} placeholder="근거를 확인한 결과와 판단 이유를 남겨주세요." />
    {form.status !== 'REJECTED' && <div className="grid gap-3 md:grid-cols-3">
      <Field label="후속조치" className="md:col-span-3" value={form.follow_up} onChange={set('follow_up')} />
      <Field as="select" label="담당자" value={form.assignee_id} onChange={set('assignee_id')}>
        <option value="">미지정</option>{members.map(m => <option key={m.id} value={m.id}>{m.name} ({LABEL[m.role]})</option>)}</Field>
      <Field label="기한" type="date" value={form.due_date} onChange={set('due_date')} />
    </div>}
    <Alert>{error}</Alert>
    <Button type="submit" disabled={busy}>{busy ? '저장 중...' : '결정 기록'}</Button>
  </form>;
}

function FindingDetail({ finding, onDone }) {
  const { decisions } = useWorkspace();
  const history = decisions.filter(d => d.finding_id === finding.id);
  return <div className="space-y-4">
    <div>
      <div className="flex flex-wrap items-center gap-1.5"><Badge value={finding.kind} /><Badge value={finding.severity} prefix="영향 " /><Badge value={finding.status} /></div>
      <h2 className="mt-2 text-xl font-bold text-slate-900">{finding.title}</h2>
    </div>
    <Section icon={CheckSquare} title="확인된 사실" tag="· 업로드 데이터와 수집 지표로 계산한 수치">
      <div className="overflow-x-auto"><table className="w-full text-sm">
        <thead><tr className="border-b border-slate-200 text-left text-xs text-slate-500"><th className="py-1.5 font-medium">항목</th><th className="py-1.5 text-right font-medium">값</th><th className="py-1.5 pl-4 font-medium">기간</th><th className="py-1.5 pl-4 font-medium">출처</th></tr></thead>
        <tbody>{finding.facts.map((f, i) => <tr key={i} className="border-b border-slate-100 last:border-0">
          <td className="py-2 text-slate-700">{f.label}</td><td className="py-2 text-right font-semibold tabular-nums text-slate-900">{f.display}</td>
          <td className="py-2 pl-4 text-xs tabular-nums text-slate-500">{f.period || '-'}</td><td className="py-2 pl-4 text-xs text-slate-500">{f.source}</td></tr>)}</tbody>
      </table></div>
    </Section>
    <Section icon={Lightbulb} title="AI 추론" tag="· 사실이 아닌 해석입니다. 원인 확인이 필요합니다." tone="ai">
      <p className="text-sm leading-relaxed text-slate-800">{finding.inference}</p>
    </Section>
    <Section icon={BookOpen} title={`근거·출처 (${finding.evidence.length})`}>
      <ul className="space-y-2">{finding.evidence.map((e, i) => {
        const Icon = EVIDENCE_ICON[e.type] || BookOpen;
        return <li key={i} className="flex items-start gap-2.5 text-sm">
          <Icon className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" aria-hidden="true" />
          <span className="min-w-0">
            {e.url ? <a href={e.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-brand-700 hover:underline">{e.title}<ExternalLink className="h-3 w-3" aria-hidden="true" /></a> : <span className="text-slate-800">{e.title}</span>}
            <span className="block text-xs text-slate-500">{e.source} · {e.date?.length > 7 ? dateKo(e.date) : e.date}</span>
          </span>
        </li>;
      })}</ul>
    </Section>
    <Section icon={AlertTriangle} title="불확실성" tone="warn"><p className="text-sm text-amber-900">{finding.uncertainty}</p></Section>
    <div className="grid gap-4 md:grid-cols-2">
      <Section icon={CheckSquare} title="관리자 검토사항">
        <ul className="space-y-1.5">{finding.review_points.map(r => <li key={r} className="flex gap-2 text-sm text-slate-700"><span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400" aria-hidden="true" />{r}</li>)}</ul>
      </Section>
      <Section icon={Lightbulb} title="권고사항"><p className="text-sm text-slate-700">{finding.recommendation}</p></Section>
    </div>
    <Card title="관리자 결정" subtitle="승인·보류·반려와 사유는 이력으로 남습니다.">
      {history.length > 0 && <ul className="mb-4 space-y-2 border-b border-slate-100 pb-4">{history.map(d => <li key={d.id} className="text-sm">
        <div className="flex flex-wrap items-center gap-2"><Badge value={d.status} /><span className="text-xs text-slate-500">{d.decided_by} · {dateTimeKo(d.decided_at)}{d.assignee ? ` · 담당 ${d.assignee}` : ''}</span></div>
        <p className="mt-1 text-slate-700">{d.reason}</p></li>)}</ul>}
      <DecisionForm finding={finding} onDone={onDone} />
    </Card>
  </div>;
}

export default function AnalysisPage({ params }) {
  const ws = useWorkspace();
  const { company, runs, can, reload } = ws;
  const [runId, setRunId] = useState(null);
  const [other, setOther] = useState(null);
  const [filter, setFilter] = useState('all');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const run = runId && other?.id === runId ? other : ws.run;
  const selectedId = Number(params.f) || null;

  useEffect(() => {
    if (!runId || runId === ws.run?.id) return;
    bi(`/companies/${company.id}/analyses/${runId}`).then(setOther).catch(e => setError(e.message));
  }, [runId, company.id, ws.run?.id, ws.decisions]);

  async function analyze() {
    setBusy(true); setError('');
    try { await bi(`/companies/${company.id}/analyses`, { method: 'POST' }); setRunId(null); go('analysis'); reload(); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  if (!ws.dashboard) return <Loading />;
  const findings = (run?.findings || []).filter(f => filter === 'all' || f.kind === filter || f.status === filter);
  const selected = run?.findings.find(f => f.id === selectedId) || findings[0];

  return <div>
    <PageHeader title="AI 기회·위험 분석" description="수치는 SQL·Polars·scikit-learn으로 계산하고, AI는 검증된 수치만 설명합니다. 사실·추론·근거·불확실성을 분리해 보여줍니다."
      actions={<>
        {runs.length > 1 && <select aria-label="분석 이력" value={run?.id || ''} onChange={e => { setRunId(Number(e.target.value)); go('analysis'); }} className="rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm">
          {runs.map(r => <option key={r.id} value={r.id}>#{r.id} · {r.period} · {dateTimeKo(r.created_at)}</option>)}</select>}
        <Button icon={Play} onClick={analyze} disabled={busy || !can.write} title={can.write ? undefined : '조회자는 분석을 실행할 수 없습니다'}>{busy ? '분석 중...' : '새 분석 실행'}</Button>
      </>} />
    <div className="mb-4"><Alert>{error}</Alert></div>
    {!run ? <Empty icon={Play} title="아직 분석 결과가 없습니다" description="ERP 데이터를 업로드한 뒤 분석을 실행하세요." /> : <>
      <Card className="mb-6" title={`${run.period} 분석 요약`} subtitle={`${dateTimeKo(run.created_at)} · 요약 생성: ${run.narrative_source === 'llm' ? 'LLM (검증된 수치만 사용, 새 수치가 포함되면 자동 폐기)' : '템플릿 (LLM 미설정)'}`}>
        <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700">{run.narrative}</p>
      </Card>
      <div className="grid gap-6 lg:grid-cols-[340px_minmax(0,1fr)]">
        <div>
          <div className="mb-3 flex flex-wrap gap-1.5" role="group" aria-label="분석 항목 필터">
            {FILTERS.map(([id, label]) => <button key={id} type="button" onClick={() => setFilter(id)} aria-pressed={filter === id}
              className={cx('rounded-full px-3 py-1 text-xs font-medium transition', filter === id ? 'bg-slate-900 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50')}>{label}</button>)}
          </div>
          <ul className="space-y-2">{findings.map(f => <li key={f.id}>
            <a href={`#/analysis?f=${f.id}`} aria-current={selected?.id === f.id ? 'true' : undefined}
              className={cx('block rounded-xl border bg-white p-3.5 transition', selected?.id === f.id ? 'border-brand-500 ring-2 ring-brand-100' : 'border-slate-200 hover:border-slate-300')}>
              <div className="flex flex-wrap items-center gap-1.5"><Badge value={f.kind} /><Badge value={f.severity} prefix="영향 " /><span className="ml-auto"><Badge value={f.status} /></span></div>
              <p className="mt-2 text-sm font-semibold text-slate-900">{f.title}</p>
              <p className="mt-1 line-clamp-2 text-xs text-slate-500">{f.recommendation}</p>
            </a></li>)}
            {!findings.length && <li><Empty title="조건에 맞는 항목이 없습니다" /></li>}
          </ul>
        </div>
        <div>{selected ? <FindingDetail key={selected.id} finding={selected} onDone={() => { reload(); if (runId) setOther(null); }} /> : null}</div>
      </div>
    </>}
  </div>;
}
