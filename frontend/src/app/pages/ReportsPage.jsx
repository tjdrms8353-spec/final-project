import { useEffect, useState } from 'react';
import { FileText, Printer, RefreshCw } from 'lucide-react';
import { bi, won } from '../../services/biApi';
import { Alert, Badge, Button, cx, dateKo, dateTimeKo, Empty, Loading, PageHeader } from '../ui';
import { useWorkspace } from '../workspace';

const kst = () => new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
const shiftWeek = (iso, weeks) => { const d = new Date(`${iso}T00:00:00Z`); d.setUTCDate(d.getUTCDate() + weeks * 7); return d.toISOString().slice(0, 10); };
const shiftMonth = (ym, months) => { const [y, m] = ym.split('-').map(Number); const d = new Date(Date.UTC(y, m - 1 + months, 1)); return d.toISOString().slice(0, 7); };
const fmt = (v, unit) => v == null ? '-' : unit === 'KRW' ? won(v) : unit === '%' ? `${v.toFixed(2)}%` : `${v.toLocaleString('ko-KR')}${unit || ''}`;

function change(k) {
  if (k.value == null || k.previous == null) return { text: '-', tone: 'text-slate-400' };
  const diff = k.value - k.previous;
  if (Math.abs(diff) < 1e-9) return { text: '변동 없음', tone: 'text-slate-500' };
  const good = (diff > 0) === Boolean(k.higher_is_better);
  const text = k.unit === '%' ? `${diff > 0 ? '+' : ''}${diff.toFixed(2)}%p`
    : k.previous ? `${diff > 0 ? '+' : ''}${(diff / Math.abs(k.previous) * 100).toFixed(1)}%` : '-';
  return { text, tone: good ? 'text-emerald-700' : 'text-red-700' };
}

function summaryLines(r) {
  const lines = [];
  const kpi = Object.fromEntries(r.kpis.map(k => [k.code, k]));
  if (kpi.sales?.value != null) {
    const c = change(kpi.sales);
    lines.push(`${r.kpi_period} 매출은 ${fmt(kpi.sales.value, 'KRW')}${c.text !== '-' ? `(전월 대비 ${c.text})` : ''}입니다.`);
  }
  if (kpi.gross_margin_pct?.value != null) lines.push(`매출총이익률 ${fmt(kpi.gross_margin_pct.value, '%')}, 영업이익(추정) ${fmt(kpi.operating_profit?.value, 'KRW')}.`);
  const findings = r.analysis.flatMap(a => a.findings);
  if (findings.length) {
    const risks = findings.filter(f => f.kind === 'risk').length, opp = findings.filter(f => f.kind === 'opportunity').length;
    lines.push(`기간 중 AI 분석 ${r.analysis.length}회, 위험 ${risks}건·기회 ${opp}건·변화 ${findings.length - risks - opp}건이 발견되었습니다.`);
  } else lines.push('기간 중 실행된 AI 분석이 없습니다.');
  lines.push(r.decisions.length ? `관리자 결정 ${r.decisions.length}건(승인 ${r.decisions.filter(d => d.status === 'APPROVED').length}·보류 ${r.decisions.filter(d => d.status === 'ON_HOLD').length}·반려 ${r.decisions.filter(d => d.status === 'REJECTED').length})이 기록되었습니다.` : '기간 중 기록된 관리자 결정이 없습니다.');
  lines.push(`현재 미완료 후속조치는 ${r.open_actions_count}건입니다.`);
  return lines;
}

const Section = ({ n, title, children, note }) => <section className="break-inside-avoid border-t border-slate-200 pt-5">
  <h2 className="text-base font-bold text-slate-900"><span className="mr-2 text-brand-600">{n}.</span>{title}</h2>
  {note && <p className="mt-0.5 text-xs text-slate-500">{note}</p>}
  <div className="mt-3">{children}</div>
</section>;
const None = ({ children }) => <p className="text-sm text-slate-500">{children}</p>;
const Th = ({ children, right }) => <th className={cx('border-b border-slate-300 px-2 py-1.5 text-xs font-semibold text-slate-600', right ? 'text-right' : 'text-left')}>{children}</th>;
const Td = ({ children, right, className }) => <td className={cx('border-b border-slate-100 px-2 py-1.5 align-top', right && 'text-right tabular-nums', className)}>{children}</td>;

function ReportDocument({ r }) {
  let n = 0;
  const weekly = r.summary?.weekly;
  return <article className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-800 sm:p-10 print:rounded-none print:border-0 print:p-0">
    <header className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-slate-900 pb-4">
      <div>
        <p className="text-xs font-semibold tracking-wide text-brand-700">dayribbon {r.kind === 'monthly' ? '월간' : '주간'} 경영 보고서</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">{r.company.name}</h1>
        <p className="mt-1 text-slate-600">{r.period} · {r.company.industry_label}</p>
      </div>
      <dl className="text-right text-xs text-slate-500">
        <div>작성 {dateTimeKo(r.generated_at)}</div><div>작성자 {r.generated_by}</div>
        <div>KPI 기준월 {r.kpi_period || '데이터 없음'}</div>
      </dl>
    </header>

    <div className="mt-5 space-y-6">
      <Section n={++n} title="핵심 요약" note="아래 수치를 그대로 요약한 문장입니다 (AI 생성 아님).">
        <ul className="list-disc space-y-1 pl-5">{summaryLines(r).map(l => <li key={l}>{l}</li>)}</ul>
      </Section>

      {weekly && <Section n={++n} title="주간 실적" note={`${dateKo(r.start)} ~ ${dateKo(r.end)} 거래일 기준 업로드 데이터 합계`}>
        {weekly.record_count ? <table className="w-full max-w-lg"><tbody>
          {[['매출', weekly.sales], ['매입', weekly.purchase], ['지출', weekly.expense], ['영업이익(추정)', weekly.operating_profit], ['기말 재고', weekly.inventory]].map(([l, v]) =>
            <tr key={l}><Td>{l}</Td><Td right>{fmt(v, 'KRW')}</Td></tr>)}
          <tr><Td className="text-slate-500">거래 건수</Td><Td right>{weekly.record_count}건</Td></tr>
        </tbody></table> : <None>이 주에 해당하는 거래 데이터가 없습니다. (월 단위 장부는 월말 날짜로 집계되는 경우가 많습니다.)</None>}
      </Section>}

      <Section n={++n} title={`핵심 지표 (${r.kpi_period || '-'})`} note={`${r.template.label} 업종 템플릿 · 업로드된 ERP 데이터를 SQL·Polars로 계산`}>
        {r.kpis.length ? <div className="overflow-x-auto"><table className="w-full min-w-[480px]">
          <thead><tr><Th>지표</Th><Th right>당월</Th><Th right>전월</Th><Th right>변화</Th></tr></thead>
          <tbody>{r.kpis.map(k => { const c = change(k); return <tr key={k.code}>
            <Td>{k.label}</Td><Td right>{fmt(k.value, k.unit)}</Td><Td right className="text-slate-500">{fmt(k.previous, k.unit)}</Td>
            <Td right className={cx('font-medium', c.tone)}>{c.text}</Td></tr>; })}</tbody>
        </table></div> : <None>보고서 기간까지 업로드된 ERP 데이터가 없습니다.</None>}
        {r.monthly_rows.length > 1 && <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[480px]">
          <thead><tr><Th>월</Th><Th right>매출</Th><Th right>매입</Th><Th right>지출</Th><Th right>영업이익</Th></tr></thead>
          <tbody>{r.monthly_rows.map(m => <tr key={m.period}><Td>{m.period}</Td><Td right>{fmt(m.sales, 'KRW')}</Td><Td right>{fmt(m.purchase, 'KRW')}</Td>
            <Td right>{fmt(m.expense, 'KRW')}</Td><Td right>{fmt(m.operating_profit, 'KRW')}</Td></tr>)}</tbody>
        </table></div>}
      </Section>

      <Section n={++n} title="AI 기회·위험 분석" note="기간 중 실행된 분석과 각 항목의 현재 결정 상태">
        {r.analysis.length ? <div className="space-y-4">{r.analysis.map(a => <div key={a.id}>
          <p className="text-xs text-slate-500">{dateTimeKo(a.created_at)} 실행 · 분석 대상 {a.period} · {a.narrative_source === 'llm' ? 'LLM 요약(수치 검증 통과)' : '템플릿 요약'}</p>
          <table className="mt-1 w-full"><thead><tr><Th>구분</Th><Th>내용</Th><Th>영향</Th><Th>상태</Th></tr></thead>
            <tbody>{a.findings.map(f => <tr key={f.id}><Td><Badge value={f.kind} /></Td><Td>{f.title}<span className="block text-xs text-slate-500">권고: {f.recommendation}</span></Td>
              <Td><Badge value={f.severity} /></Td><Td><Badge value={f.status} /></Td></tr>)}</tbody></table>
        </div>)}</div> : <None>기간 중 실행된 분석이 없습니다.</None>}
      </Section>

      <Section n={++n} title="관리자 결정">
        {r.decisions.length ? <table className="w-full"><thead><tr><Th>일시</Th><Th>항목</Th><Th>결정</Th><Th>사유</Th><Th>결정자</Th></tr></thead>
          <tbody>{r.decisions.map(d => <tr key={d.id}><Td className="whitespace-nowrap text-xs">{dateTimeKo(d.decided_at)}</Td><Td>{d.finding_title}</Td>
            <Td><Badge value={d.status} /></Td><Td>{d.reason}</Td><Td className="whitespace-nowrap">{d.decided_by}</Td></tr>)}</tbody></table>
          : <None>기간 중 기록된 결정이 없습니다.</None>}
      </Section>

      <Section n={++n} title="후속조치" note={`기간 중 생성·변경된 조치 · 전체 미완료 ${r.open_actions_count}건`}>
        {r.actions.length ? <table className="w-full"><thead><tr><Th>조치</Th><Th>담당</Th><Th>기한</Th><Th>상태</Th></tr></thead>
          <tbody>{r.actions.map(a => <tr key={a.id}><Td>{a.title}</Td><Td>{a.assignee || '미지정'}</Td><Td>{a.due_date || '-'}</Td><Td><Badge value={a.status} /></Td></tr>)}</tbody></table>
          : <None>기간 중 변경된 후속조치가 없습니다.</None>}
      </Section>

      <Section n={++n} title="시장 지표">
        {r.indicators.length ? <table className="w-full max-w-lg"><thead><tr><Th>지표</Th><Th right>최근 값</Th><Th right>30일 변동</Th><Th>기준일</Th></tr></thead>
          <tbody>{r.indicators.map(i => <tr key={i.code}><Td>{i.code}</Td><Td right>{i.latest_value?.toLocaleString('ko-KR', { maximumFractionDigits: 2 }) ?? '-'}</Td>
            <Td right>{i.change_30d_pct == null ? '-' : `${i.change_30d_pct > 0 ? '+' : ''}${i.change_30d_pct}%`}</Td><Td className="text-xs text-slate-500">{i.latest_date || '-'}</Td></tr>)}</tbody></table>
          : <None>수집된 시장 지표가 없습니다.</None>}
        {r.indicators.length > 0 && <p className="mt-1 text-xs text-slate-500">출처: {[...new Set(r.indicators.map(i => i.source))].join(', ')}</p>}
      </Section>

      <Section n={++n} title="데이터 업로드 기록">
        {r.uploads.length ? <ul className="space-y-0.5">{r.uploads.map(u => <li key={u.id}>{dateTimeKo(u.uploaded_at)} · {u.file_name} · {u.row_count}행 저장{u.rejected_count ? `, ${u.rejected_count}행 제외` : ''}</li>)}</ul>
          : <None>기간 중 업로드가 없습니다.</None>}
      </Section>
    </div>

    <footer className="mt-8 border-t border-slate-200 pt-3 text-[11px] leading-relaxed text-slate-500">
      모든 수치는 업로드된 ERP 데이터와 저장된 시장 지표에서 계산했으며 AI가 생성한 수치는 없습니다. 결정 사유와 이력은 감사 추적 로그에 함께 기록됩니다.
    </footer>
  </article>;
}

export default function ReportsPage() {
  const { company } = useWorkspace();
  const [kind, setKind] = useState('monthly');
  const [month, setMonth] = useState(() => kst().slice(0, 7));
  const [anchor, setAnchor] = useState(kst);
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let alive = true;
    setBusy(true); setError('');
    const q = kind === 'monthly' ? `kind=monthly&month=${month}` : `kind=weekly&anchor=${anchor}`;
    bi(`/companies/${company.id}/reports?${q}`).then(r => alive && setReport(r)).catch(e => alive && setError(e.message)).finally(() => alive && setBusy(false));
    return () => { alive = false; };
  }, [company.id, kind, month, anchor, nonce]);

  const step = (d) => kind === 'monthly' ? setMonth(shiftMonth(month, d)) : setAnchor(shiftWeek(anchor, d));

  return <div>
    <div className="print:hidden">
      <PageHeader title="주간·월간 보고서" description="기간을 고르면 KPI·AI 분석·결정·후속조치를 한 문서로 자동 정리합니다. 인쇄하거나 PDF로 저장해 공유하세요."
        actions={<><Button variant="secondary" icon={RefreshCw} onClick={() => setNonce(v => v + 1)} disabled={busy}>다시 생성</Button>
          <Button icon={Printer} onClick={() => window.print()} disabled={!report || busy}>인쇄 · PDF 저장</Button></>} />
      <div className="mb-5 flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
        <div role="group" aria-label="보고서 종류" className="inline-flex gap-0.5 rounded-lg bg-slate-100 p-0.5">
          {[['weekly', '주간'], ['monthly', '월간']].map(([v, l]) => <button key={v} type="button" aria-pressed={kind === v} onClick={() => setKind(v)}
            className={cx('rounded-md px-3 py-1.5 text-sm font-medium', kind === v ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900')}>{l}</button>)}
        </div>
        <div className="flex items-center gap-1.5">
          <Button variant="ghost" size="sm" onClick={() => step(-1)} aria-label="이전 기간">‹ 이전</Button>
          {kind === 'monthly'
            ? <input type="month" aria-label="보고서 월" value={month} onChange={e => e.target.value && setMonth(e.target.value)} className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm" />
            : <input type="date" aria-label="보고서 주 (아무 날짜)" value={anchor} onChange={e => e.target.value && setAnchor(e.target.value)} className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm" />}
          <Button variant="ghost" size="sm" onClick={() => step(1)} aria-label="다음 기간">다음 ›</Button>
        </div>
        {report && <span className="text-sm text-slate-600">{report.period}</span>}
        <span className="ml-auto text-xs text-slate-400">보고서 조회도 감사 로그에 기록됩니다</span>
      </div>
      <Alert>{error}</Alert>
    </div>
    {busy && !report ? <Loading label="보고서 생성 중..." /> : report ? <div className={cx(busy && 'opacity-60')}><ReportDocument r={report} /></div>
      : !error && <Empty icon={FileText} title="보고서를 불러오지 못했습니다" />}
  </div>;
}

