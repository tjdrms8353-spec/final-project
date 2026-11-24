import { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { Bar, CartesianGrid, ComposedChart, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { bi, eok } from '../../services/biApi';
import { Button, Card, CHART, Delta, Empty, kpiText, kpiTitle, Loading, PageHeader } from '../ui';
import { go, useWorkspace } from '../workspace';

const axis = { fontSize: 12, stroke: CHART.axis, tickLine: false, axisLine: false };

function KpiTile({ kpi, series }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-4" title={kpi.description}>
    <p className="text-xs font-medium text-slate-500">{kpi.label}</p>
    <div className="mt-1.5 flex items-end justify-between gap-2">
      <p className="text-lg font-bold tabular-nums text-slate-900" title={kpiTitle(kpi.value, kpi.unit)}>{kpiText(kpi.value, kpi.unit)}</p>
      {series.length > 1 && <div className="h-8 w-20" aria-hidden="true"><ResponsiveContainer>
        <LineChart data={series}><Line isAnimationActive={false} dataKey="v" dot={false} strokeWidth={1.75} stroke={CHART.brand} /></LineChart></ResponsiveContainer></div>}
    </div>
    <div className="mt-1"><Delta value={kpi.value} previous={kpi.previous} higherIsBetter={kpi.higher_is_better} unit={kpi.unit} /></div>
    <p className="mt-1.5 text-[11px] text-slate-400">{kpi.description}</p>
  </div>;
}

function ProfitBreakdown({ month }) {
  const rows = [['매입(원재료)', month.purchase, 'bg-amber-400'], ['지출(판관비)', month.expense, 'bg-slate-400'], ['영업이익(추정)', month.operating_profit, 'bg-brand-600']];
  return <div>
    <p className="text-xs text-slate-500">{month.period} 매출</p>
    <p className="text-2xl font-bold tabular-nums text-slate-900">{eok(month.sales)}</p>
    <div className="mt-4 flex h-3 overflow-hidden rounded-full bg-slate-100" aria-hidden="true">
      {rows.map(([l, v, c]) => <span key={l} className={c} style={{ width: `${Math.max(0, v / month.sales * 100)}%` }} />)}
    </div>
    <ul className="mt-4 space-y-2.5">{rows.map(([l, v, c]) => <li key={l} className="flex items-center gap-2 text-sm">
      <span className={`h-2.5 w-2.5 rounded-sm ${c}`} aria-hidden="true" /><span className="flex-1 text-slate-600">{l}</span>
      <span className="font-medium tabular-nums text-slate-900">{eok(v)}</span><span className="w-14 text-right text-xs tabular-nums text-slate-500">{(v / month.sales * 100).toFixed(1)}%</span>
    </li>)}</ul>
    <p className="mt-4 text-xs text-slate-500">수출 매출 {eok(month.export_sales)} · 외화 매입 {eok(month.fx_purchase)} · 월말 재고 {eok(month.inventory)}</p>
  </div>;
}

export default function DashboardPage() {
  const { company, dashboard, reload, can } = useWorkspace();
  const codes = dashboard ? Object.keys(dashboard.indicators) : [];
  const [fxCode, setFxCode] = useState(null);
  const [msg, setMsg] = useState('');
  if (!dashboard) return <Loading />;
  const code = fxCode || codes.find(c => dashboard.indicators[c].series.length) || codes[0];
  const fx = dashboard.indicators[code];
  const monthly = dashboard.monthly;
  const chart = monthly.map(m => ({ ...m, salesE: m.sales / 1e8, purchaseE: m.purchase / 1e8, expenseE: m.expense / 1e8 }));

  async function collect() {
    setMsg('환율 수집 중...');
    try { const r = await bi('/market/fx/collect', { method: 'POST' }); setMsg(`ECB 기준환율 ${r.fetched}건 조회 · 신규 ${r.inserted}건 저장`); reload(); }
    catch (e) { setMsg(e.message); }
  }

  return <div>
    <PageHeader title="BI 대시보드" description={`${company.industry_label} 업종 템플릿 · ${dashboard.period ? `최근 ${dashboard.period}` : '데이터 없음'} · 모든 수치는 업로드한 ERP 데이터를 SQL·Polars로 계산한 값입니다.`}
      actions={<Button variant="secondary" icon={RefreshCw} onClick={reload}>새로고침</Button>} />
    {!monthly.length ? <Empty title="업로드된 ERP 데이터가 없습니다" description="매출·매입·지출·재고 장부를 CSV 또는 Excel로 올리면 KPI가 자동 계산됩니다."
      action={can.write && <Button onClick={() => go('data')}>데이터 업로드</Button>} /> : <div className="space-y-6">
      <section aria-label="업종 KPI" className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        {dashboard.kpis.map(k => <KpiTile key={k.code} kpi={k} series={monthly.filter(m => m[k.code] != null).map(m => ({ v: m[k.code] }))} />)}
      </section>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card title="월별 매출·비용·이익률" subtitle="단위: 억 원 / 매출총이익률 %" className="xl:col-span-2">
          <div className="h-80"><ResponsiveContainer>
            <ComposedChart data={chart} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke={CHART.grid} />
              <XAxis dataKey="period" {...axis} /><YAxis yAxisId="l" {...axis} unit="억" /><YAxis yAxisId="r" orientation="right" {...axis} unit="%" />
              <Tooltip formatter={(v, n) => n.includes('%') ? `${Number(v).toFixed(2)}%` : `${Number(v).toFixed(1)}억`} />
              <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
              <Bar isAnimationActive={false} yAxisId="l" dataKey="salesE" name="매출" fill={CHART.brand} radius={[3, 3, 0, 0]} />
              <Bar isAnimationActive={false} yAxisId="l" dataKey="purchaseE" name="매입" fill={CHART.amber} radius={[3, 3, 0, 0]} />
              <Bar isAnimationActive={false} yAxisId="l" dataKey="expenseE" name="지출" fill={CHART.slate} radius={[3, 3, 0, 0]} />
              <Line isAnimationActive={false} yAxisId="r" dataKey="gross_margin_pct" name="매출총이익률(%)" stroke={CHART.green} strokeWidth={2.5} dot={{ r: 3 }} />
            </ComposedChart></ResponsiveContainer></div>
        </Card>
        <Card title="이번 달 수익 구조"><ProfitBreakdown month={monthly.at(-1)} /></Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="재고 보유일수·원재료 매입 비중" subtitle="재고 기준선 60일">
          <div className="h-64"><ResponsiveContainer>
            <LineChart data={monthly} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke={CHART.grid} /><XAxis dataKey="period" {...axis} />
              <YAxis yAxisId="l" {...axis} unit="일" /><YAxis yAxisId="r" orientation="right" {...axis} unit="%" />
              <Tooltip /><Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
              <Line isAnimationActive={false} yAxisId="l" dataKey="inventory_days" name="재고 보유일수(일)" stroke={CHART.red} strokeWidth={2.5} dot={{ r: 3 }} />
              <Line isAnimationActive={false} yAxisId="r" dataKey="purchase_ratio_pct" name="매입 비중(%)" stroke={CHART.amber} strokeWidth={2} dot={{ r: 3 }} />
            </LineChart></ResponsiveContainer></div>
        </Card>
        <Card title="환율·금융지표" subtitle={fx?.change_30d ? `출처: ${fx.change_30d.source}` : '관심 지표'}
          actions={<>
            <select value={code} onChange={e => setFxCode(e.target.value)} aria-label="지표 선택" className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm">
              {codes.map(c => <option key={c}>{c}</option>)}</select>
            <Button variant="secondary" size="sm" icon={RefreshCw} onClick={collect}>환율 최신화</Button></>}>
          {fx?.series.length ? <>
            <div className="h-52"><ResponsiveContainer><LineChart data={fx.series} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke={CHART.grid} /><XAxis dataKey="date" {...axis} minTickGap={40} tickFormatter={d => d.slice(5)} />
              <YAxis domain={['auto', 'auto']} {...axis} width={56} /><Tooltip />
              <Line isAnimationActive={false} dataKey="value" name={code} stroke={CHART.violet} strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div>
            {fx.change_30d && <p className="mt-2 text-sm text-slate-600">30일 변동 <b className="tabular-nums">{fx.change_30d.change_pct > 0 ? '+' : ''}{fx.change_30d.change_pct}%</b>
              <span className="text-xs text-slate-500"> ({fx.change_30d.from_date} → {fx.change_30d.to_date})</span></p>}
          </> : <Empty title={`${code} 데이터가 없습니다`} description={code === 'KR_BASE_RATE' ? '기준금리는 아직 자동 수집하지 않습니다. 관리자가 지표 API로 직접 입력할 수 있습니다.' : '‘환율 최신화’로 무료 ECB 기준환율을 가져올 수 있습니다.'} />}
          {msg && <p className="mt-2 text-xs text-slate-600" role="status">{msg}</p>}
        </Card>
      </div>
    </div>}
  </div>;
}
