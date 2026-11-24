import { useRef, useState } from 'react';
import { Bar, CartesianGrid, ComposedChart, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { bi, eok, formatKpi } from '../../services/biApi';
import { Alert, Button, Card } from './ui';

function KpiCard({ kpi }) {
  const diff = kpi.value != null && kpi.previous != null ? kpi.value - kpi.previous : null;
  const good = diff == null ? null : (diff >= 0) === kpi.higher_is_better;
  return <div className="rounded-xl border border-slate-200 bg-white p-4" title={kpi.description}>
    <p className="text-xs text-slate-500">{kpi.label}</p>
    <p className="mt-1 font-display text-lg font-semibold tabular-nums text-slate-900">{formatKpi(kpi.value, kpi.unit)}</p>
    {diff != null && <p className={`text-xs tabular-nums ${good ? 'text-emerald-700' : 'text-red-700'}`}>
      전월 {formatKpi(kpi.previous, kpi.unit)} 대비 {diff >= 0 ? '▲' : '▼'}</p>}
  </div>;
}

export function UploadPanel({ company, onUploaded }) {
  const input = useRef(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function upload(file) {
    if (!file) return;
    setBusy(true); setError(''); setResult(null);
    try { setResult(await bi(`/companies/${company.id}/erp/upload`, { method: 'POST', file })); onUploaded(); }
    catch (e) { setError(e.message); } finally { setBusy(false); if (input.current) input.current.value = ''; }
  }
  return <Card title="ERP 데이터 업로드 (Excel·CSV)">
    <p className="mb-3 text-sm text-slate-600">ERP가 없어도 매출·매입·지출·재고 장부를 CSV 또는 Excel로 올리면 KPI가 계산됩니다.
      필수 열: <code>date, category(매출/매입/지출/재고), item, amount</code> · 선택: <code>quantity, country</code></p>
    <div className="flex flex-wrap items-center gap-2">
      <input ref={input} type="file" accept=".csv,.xlsx" aria-label="ERP 파일 선택" disabled={busy || company.role === 'VIEWER'}
        onChange={e => upload(e.target.files?.[0])} className="text-sm" />
      <a className="text-sm text-blue-700 hover:underline" href="/api/bi/erp/template.csv">양식 다운로드</a>
      <a className="text-sm text-blue-700 hover:underline" href="/samples/semiconductor_erp_sample.csv" download>반도체 샘플 데이터</a>
    </div>
    <div className="mt-3 space-y-2">
      <Alert>{error}</Alert>
      {result && <Alert tone="ok">{result.accepted}행 저장{result.rejected ? `, ${result.rejected}행 제외 (${result.errors.join(' / ')})` : ''}</Alert>}
    </div>
  </Card>;
}

export default function BiDashboard({ data, onRefresh }) {
  const [fxMessage, setFxMessage] = useState('');
  const fxCodes = Object.keys(data.indicators);
  const [fxCode, setFxCode] = useState(fxCodes.find(c => data.indicators[c].series.length) || fxCodes[0]);
  const fx = data.indicators[fxCode];
  async function collectFx() {
    setFxMessage('수집 중...');
    try { const r = await bi('/market/fx/collect', { method: 'POST' }); setFxMessage(`환율 ${r.fetched}건 조회, 신규 ${r.inserted}건 저장`); onRefresh(); }
    catch (e) { setFxMessage(e.message); }
  }
  const chart = data.monthly.map(m => ({ ...m, salesE: m.sales / 1e8, purchaseE: m.purchase / 1e8, expenseE: m.expense / 1e8 }));
  return <div className="space-y-5">
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      {data.kpis.map(k => <KpiCard key={k.code} kpi={k} />)}
    </div>
    <div className="grid gap-5 xl:grid-cols-3">
      <Card title={`월별 매출·비용·이익률 ${data.period ? `(최근 ${data.period})` : ''}`} className="xl:col-span-2">
        {chart.length ? <div className="h-72"><ResponsiveContainer>
          <ComposedChart data={chart}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="period" fontSize={12} /><YAxis yAxisId="l" fontSize={12} unit="억" /><YAxis yAxisId="r" orientation="right" fontSize={12} unit="%" />
            <Tooltip formatter={(v, n) => n.includes('%') ? `${Number(v).toFixed(2)}%` : `${Number(v).toFixed(1)}억`} /><Legend />
            <Bar isAnimationActive={false} yAxisId="l" dataKey="salesE" name="매출(억)" fill="#2563eb" /><Bar isAnimationActive={false} yAxisId="l" dataKey="purchaseE" name="매입(억)" fill="#f59e0b" />
            <Bar isAnimationActive={false} yAxisId="l" dataKey="expenseE" name="지출(억)" fill="#94a3b8" />
            <Line isAnimationActive={false} yAxisId="r" dataKey="gross_margin_pct" name="매출총이익률(%)" stroke="#16a34a" strokeWidth={2} />
          </ComposedChart></ResponsiveContainer></div> : <p className="text-sm text-slate-500">업로드된 ERP 데이터가 없습니다.</p>}
      </Card>
      <Card title="환율·금융지표" actions={<Button variant="secondary" onClick={collectFx}>환율 최신화</Button>}>
        <select value={fxCode} onChange={e => setFxCode(e.target.value)} aria-label="지표 선택" className="mb-2 rounded border border-slate-300 px-2 py-1 text-sm">
          {fxCodes.map(c => <option key={c}>{c}</option>)}</select>
        {fx?.series.length ? <>
          <div className="h-44"><ResponsiveContainer><LineChart data={fx.series}><XAxis dataKey="date" hide /><YAxis domain={['auto', 'auto']} fontSize={11} width={50} />
            <Tooltip /><Line isAnimationActive={false} dataKey="value" name={fxCode} stroke="#7c3aed" dot={false} /></LineChart></ResponsiveContainer></div>
          {fx.change_30d && <p className="text-xs text-slate-600">30일 변동 {fx.change_30d.change_pct > 0 ? '+' : ''}{fx.change_30d.change_pct}% ({fx.change_30d.from_date} → {fx.change_30d.to_date}) · 출처: {fx.change_30d.source}</p>}
        </> : <p className="text-sm text-slate-500">저장된 지표가 없습니다. ‘환율 최신화’로 무료 ECB 기준환율을 가져올 수 있습니다.</p>}
        {fxMessage && <p className="mt-2 text-xs text-slate-600" role="status">{fxMessage}</p>}
      </Card>
    </div>
    <Card title={`관련 산업 뉴스 (최근 ${data.news.days || 14}일 ${data.news.recent_count}건)`}>
      {!data.news.available && <p className="text-sm text-amber-700">뉴스 DB에 연결할 수 없습니다.</p>}
      <p className="mb-2 text-xs text-slate-500">검색 키워드: {data.news.keywords.join(', ')}</p>
      {data.news.items.length ? <ul className="space-y-1 text-sm">{data.news.items.map(n => <li key={n.url}>
        <a href={n.url} target="_blank" rel="noreferrer" className="text-blue-700 hover:underline">{n.title}</a>
        <span className="ml-2 text-xs text-slate-500">{n.source} · {new Date(n.date).toLocaleDateString('ko-KR')}</span></li>)}</ul>
        : <p className="text-sm text-slate-500">일치하는 저장 기사가 없습니다. 뉴스 수집(Airflow) 데이터가 쌓이면 자동으로 연결됩니다.</p>}
    </Card>
    <p className="text-xs text-slate-500">최근 월 매출 {eok(data.monthly.at(-1)?.sales)} · 모든 수치는 업로드 데이터를 SQL/Polars로 계산한 값입니다.</p>
  </div>;
}
