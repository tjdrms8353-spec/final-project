import { useState } from 'react';
import { Play, RotateCcw } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { bi, eok } from '../../services/biApi';
import { Alert, Button, Card, CHART, cx, Empty, PageHeader } from '../ui';
import { useWorkspace } from '../workspace';

const INPUTS = [
  ['fx_pct', '원/달러 환율', -20, 20, '수출 매출·외화 매입에 적용'], ['purchase_price_pct', '원자재 매입단가', -30, 50, '매입 금액에 적용'],
  ['sales_pct', '판매단가', -30, 30, '매출 금액에 적용'], ['volume_pct', '판매량', -50, 50, '매출·매입에 같은 비율로 적용'],
];
const ZERO = { fx_pct: 0, purchase_price_pct: 0, sales_pct: 0, volume_pct: 0 };
const PRESETS = [
  ['원화 약세 (+10%)', { ...ZERO, fx_pct: 10 }], ['원자재 급등 (+20%)', { ...ZERO, purchase_price_pct: 20 }],
  ['수요 둔화 (판매량 -15%)', { ...ZERO, volume_pct: -15 }], ['복합 악화', { fx_pct: 5, purchase_price_pct: 15, sales_pct: -5, volume_pct: -10 }],
];
const NAMES = { sales: '매출', cost: '비용', profit: '이익' };
const axis = { fontSize: 12, stroke: CHART.axis, tickLine: false, axisLine: false };

export default function SimulationPage() {
  const { company } = useWorkspace();
  const [form, setForm] = useState(ZERO);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function run(values = form) {
    setBusy(true); setError('');
    try { setResult(await bi(`/companies/${company.id}/simulate`, { method: 'POST', body: values })); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  const chart = result ? Object.keys(NAMES).map(k => ({ name: NAMES[k], before: result.before[k] / 1e8, after: result.after[k] / 1e8 })) : [];
  return <div>
    <PageHeader title="시나리오 시뮬레이션" description="환율·원자재·판매 조건이 바뀔 때 최근 월 손익이 어떻게 달라지는지 계산합니다. 2차 기능(베타)이며 예측이 아닌 단순 민감도 계산입니다." />
    <div className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
      <Card title="조건 설정">
        <div className="mb-5 flex flex-wrap gap-1.5">{PRESETS.map(([label, v]) => <button key={label} type="button" onClick={() => { setForm(v); run(v); }}
          className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200">{label}</button>)}</div>
        <div className="space-y-5">{INPUTS.map(([key, label, min, max, hint]) => <label key={key} className="block text-sm">
          <span className="flex items-center justify-between"><span className="font-medium text-slate-700">{label}</span>
            <b className={cx('tabular-nums', form[key] > 0 ? 'text-red-700' : form[key] < 0 ? 'text-brand-700' : 'text-slate-500')}>{form[key] > 0 ? '+' : ''}{form[key]}%</b></span>
          <input type="range" min={min} max={max} step={1} value={form[key]} onChange={e => setForm({ ...form, [key]: Number(e.target.value) })} className="mt-2 w-full accent-brand-600" />
          <span className="flex justify-between text-[11px] text-slate-400"><span>{min}%</span><span>{hint}</span><span>+{max}%</span></span>
        </label>)}</div>
        <div className="mt-6 flex gap-2"><Button icon={Play} onClick={() => run()} disabled={busy} className="flex-1">{busy ? '계산 중...' : '시뮬레이션 실행'}</Button>
          <Button variant="secondary" icon={RotateCcw} onClick={() => { setForm(ZERO); setResult(null); }}>초기화</Button></div>
        <div className="mt-3"><Alert>{error}</Alert></div>
      </Card>
      <Card title="결과" subtitle={result ? `기준: ${result.period} 실적` : undefined}>
        {result ? <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">{Object.keys(NAMES).map(k => <div key={k} className="rounded-lg border border-slate-200 p-3">
            <p className="text-xs text-slate-500">{NAMES[k]}</p>
            <p className="mt-1 text-lg font-bold tabular-nums text-slate-900">{eok(result.after[k])}</p>
            <p className={cx('text-xs font-medium tabular-nums', (k === 'cost' ? -result.delta[k] : result.delta[k]) >= 0 ? 'text-emerald-700' : 'text-red-700')}>
              {result.delta[k] >= 0 ? '+' : ''}{eok(result.delta[k])} <span className="font-normal text-slate-400">(기준 {eok(result.before[k])})</span></p>
          </div>)}</div>
          <div className="h-64"><ResponsiveContainer><BarChart data={chart} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke={CHART.grid} /><XAxis dataKey="name" {...axis} /><YAxis unit="억" {...axis} />
            <Tooltip formatter={v => `${Number(v).toFixed(2)}억`} /><Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
            <Bar isAnimationActive={false} dataKey="before" name="기준" fill={CHART.slate} radius={[3, 3, 0, 0]} />
            <Bar isAnimationActive={false} dataKey="after" name="시나리오" fill={CHART.brand} radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></div>
          <div><p className="text-xs font-semibold text-slate-600">계산 가정</p>
            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-xs text-slate-500">{result.assumptions.map(a => <li key={a}>{a}</li>)}</ul></div>
        </div> : <Empty icon={Play} title="조건을 정하고 시뮬레이션을 실행하세요" description="왼쪽의 예시 시나리오를 눌러 바로 결과를 볼 수도 있습니다." />}
      </Card>
    </div>
  </div>;
}
