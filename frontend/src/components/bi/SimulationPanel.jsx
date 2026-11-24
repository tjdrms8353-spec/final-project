import { useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { bi, eok } from '../../services/biApi';
import { Alert, Button, Card } from './ui';

const INPUTS = [
  ['fx_pct', '원/달러 환율 변동', -20, 20], ['purchase_price_pct', '원자재 매입단가 변동', -30, 50],
  ['sales_pct', '판매단가(매출) 변동', -30, 30], ['volume_pct', '판매량 변동', -50, 50],
];
const NAMES = { sales: '매출', cost: '비용', profit: '이익' };

export default function SimulationPanel({ company }) {
  const [form, setForm] = useState({ fx_pct: 0, purchase_price_pct: 0, sales_pct: 0, volume_pct: 0 });
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  async function run() {
    setError('');
    try { setResult(await bi(`/companies/${company.id}/simulate`, { method: 'POST', body: form })); } catch (e) { setError(e.message); }
  }
  const chart = result ? Object.keys(NAMES).map(k => ({ name: NAMES[k], before: result.before[k] / 1e8, after: result.after[k] / 1e8 })) : [];
  return <Card title="시나리오 시뮬레이션 (2차 기능 · 베타)">
    <div className="grid gap-4 md:grid-cols-2">
      {INPUTS.map(([key, label, min, max]) => <label key={key} className="text-sm">
        <span className="flex justify-between"><span>{label}</span><b className="tabular-nums">{form[key] > 0 ? '+' : ''}{form[key]}%</b></span>
        <input type="range" min={min} max={max} step={1} value={form[key]} onChange={e => setForm({ ...form, [key]: Number(e.target.value) })} className="w-full" />
      </label>)}
    </div>
    <Button className="mt-3" onClick={run}>시뮬레이션 실행</Button>
    <div className="mt-3"><Alert>{error}</Alert></div>
    {result && <div className="mt-4 grid gap-4 lg:grid-cols-2">
      <div className="h-60"><ResponsiveContainer><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="name" fontSize={12} /><YAxis unit="억" fontSize={12} /><Tooltip formatter={v => `${Number(v).toFixed(2)}억`} /><Legend />
        <Bar isAnimationActive={false} dataKey="before" name={`기준 (${result.period})`} fill="#94a3b8" /><Bar isAnimationActive={false} dataKey="after" name="시나리오" fill="#2563eb" /></BarChart></ResponsiveContainer></div>
      <div className="text-sm">
        <ul className="space-y-1">{Object.keys(NAMES).map(k => <li key={k}>{NAMES[k]}: {eok(result.before[k])} → <b>{eok(result.after[k])}</b>
          <span className={result.delta[k] >= 0 ? 'text-emerald-700' : 'text-red-700'}> ({result.delta[k] >= 0 ? '+' : ''}{eok(result.delta[k])})</span></li>)}</ul>
        <p className="mt-3 text-xs font-medium text-slate-600">계산 가정</p>
        <ul className="list-disc pl-5 text-xs text-slate-500">{result.assumptions.map(a => <li key={a}>{a}</li>)}</ul>
      </div>
    </div>}
  </Card>;
}
