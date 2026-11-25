import React, { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, fmtWon } from '../api'
import { Badge, Card, ErrorBox, Loading, SectionTitle, SeverityBadge } from '../components/ui'

const SEV_TONE = { '정상': 'green', '관심': 'blue', '주의': 'amber', '위험': 'red', '심각': 'red' }

export default function Simulation() {
  const [presets, setPresets] = useState(null)
  const [params, setParams] = useState({
    fx_change_pct: 3.2, rate_change_pct: 0.5, material_change_pct: 5.0,
    annual_import_cost: 5000000000, debt_amount: 10000000000, revenue_change_pct: -3.0,
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api('/api/simulation/presets').then(p => {
      setPresets(p)
      setParams(p.defaults)
    }).catch(e => setError(e.message))
  }, [])

  const run = async (p = params) => {
    setLoading(true); setError(''); setResult(null)
    try { setResult(await api('/api/simulation/run', { method: 'POST', body: p })) }
    catch (e) { setError(e.message) } finally { setLoading(false) }
  }

  const set = (k, v) => setParams({ ...params, [k]: Number(v) })

  const chartData = result ? [
    { name: '수입비용 증가', value: result.results.환율_상승에_따른_수입비용_증가 / 1e8, fill: '#f59e0b' },
    { name: '금융비용 증가', value: result.results.금리_상승에_따른_금융비용_증가 / 1e8, fill: '#8b5cf6' },
    { name: '원가 증가', value: result.results.원자재가_상승에_따른_제조원가_증가 / 1e8, fill: '#f43f5e' },
    { name: '매출영업이익 변동', value: result.results.매출_변동에_따른_영업이익_변동 / 1e8, fill: result.results.매출_변동에_따른_영업이익_변동 >= 0 ? '#10b981' : '#f43f5e' },
  ] : []

  const FIELDS = [
    ['fx_change_pct', '환율 변동률 (%)'],
    ['rate_change_pct', '금리 변동폭 (%p)'],
    ['material_change_pct', '원자재 가격 변동률 (%)'],
    ['annual_import_cost', '연간 수입 비용 (원)'],
    ['debt_amount', '차입금 규모 (원)'],
    ['revenue_change_pct', '매출 변동률 (%)'],
  ]

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-bold text-slate-900">위험 영향 시뮬레이션</h1>
        <p className="text-xs text-slate-500">변수를 바꾸면 기업 내부 데이터와 결합해 영향이 즉시 계산됩니다 · 결과는 "조건 동일 가정"의 시나리오입니다</p>
      </div>
      <ErrorBox error={error} />

      <div className="grid lg:grid-cols-5 gap-4">
        {/* 입력 패널 */}
        <Card className="lg:col-span-2 p-5">
          <SectionTitle>시나리오 변수</SectionTitle>
          {presets && (
            <div className="flex flex-wrap gap-1.5 mb-4">
              {presets.presets.map(p => (
                <button key={p.name} onClick={() => { setParams({ ...params, ...p.params }); }}
                  className="text-[11px] bg-slate-100 hover:bg-brand-50 hover:text-brand-700 rounded-lg px-2 py-1 text-slate-600">
                  {p.name}
                </button>
              ))}
            </div>
          )}
          <div className="space-y-3">
            {FIELDS.map(([k, label]) => (
              <label key={k} className="block">
                <div className="flex justify-between text-xs text-slate-600 mb-1">
                  <span>{label}</span>
                  <span className="font-semibold text-slate-800">{params[k].toLocaleString()}</span>
                </div>
                <input type="range"
                  min={k.includes('cost') || k === 'debt_amount' ? (k === 'debt_amount' ? 0 : 1e9) : -15}
                  max={k.includes('cost') || k === 'debt_amount' ? (k === 'annual_import_cost' ? 2e10 : k === 'debt_amount' ? 5e10 : 3e10) : 15}
                  step={k.includes('cost') || k === 'debt_amount' ? (k === 'annual_import_cost' ? 1e8 : 5e8) : 0.1}
                  value={params[k]} onChange={e => set(k, e.target.value)}
                  className="w-full" />
                <input type="number" value={params[k]} onChange={e => set(k, e.target.value)}
                  className="mt-1 w-full border border-slate-200 rounded px-2 py-1 text-xs" />
              </label>
            ))}
          </div>
          <button onClick={() => run()} disabled={loading}
            className="mt-4 w-full bg-brand-600 text-white rounded-lg py-2.5 text-sm font-semibold hover:bg-brand-700 disabled:opacity-50">
            {loading ? '계산 중…' : '시뮬레이션 실행'}
          </button>
          {presets?.severity_rules && (
            <div className="mt-4 bg-slate-50 rounded-lg p-3">
              <div className="text-xs font-semibold text-slate-600 mb-1">위험 등급 판단 기준</div>
              {Object.entries(presets.severity_rules).map(([k, v]) => (
                <div key={k} className="text-[11px] text-slate-500">· {k}: {v}</div>
              ))}
            </div>
          )}
        </Card>

        {/* 결과 패널 */}
        <Card className="lg:col-span-3 p-5">
          {!result ? (
            <EmptyResult />
          ) : (
            <>
              <div className="flex items-center gap-3 mb-4">
                <span className="text-sm text-slate-600">종합 위험 등급:</span>
                <SeverityBadge severity={result.severity} />
                <span className="text-xs text-slate-400">{result.severity_reason}</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
                {[
                  ['수입비용 증가', result.formatted.환율_수입비용증가],
                  ['금융비용 증가', result.formatted.금융비용증가],
                  ['원가 증가', result.formatted.원자재원가증가],
                  ['매출영업이익 변동', result.formatted.매출영업이익변동],
                  ['순 영향 추정', result.formatted.순영향],
                ].map(([l, v]) => (
                  <div key={l} className="bg-slate-50 rounded-lg p-3">
                    <div className="text-[11px] text-slate-500">{l}</div>
                    <div className={`text-sm font-bold ${String(v).startsWith('-') || String(v).startsWith('−') ? 'text-rose-600' : 'text-slate-800'}`}>{v}</div>
                  </div>
                ))}
              </div>
              <div className="h-52 mb-3">
                <ResponsiveContainer>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 10 }} unit="억" />
                    <Tooltip formatter={(v) => `${v}억원`} />
                    <Legend />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {chartData.map((c, i) => <Cell key={i} fill={c.fill} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 mb-3">
                ⚠ {result.assumptions.시나리오_주의}
              </div>
              <div className="text-xs text-slate-500 space-y-1">
                <div>· 변동비율 근사치: {result.assumptions.변동비율_근사치} ({result.assumptions.변동비율_설명})</div>
                <div>· 연간 매출 기준: {fmtWon(result.assumptions.연간_매출_기준)} / 연간 영업이익 추정: {fmtWon(result.assumptions.연간_영업이익_추정)}</div>
                <div>· {result.calculation_example}</div>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  )
}

function EmptyResult() {
  return (
    <div className="h-full flex flex-col items-center justify-center text-slate-400 py-16">
      <div className="text-4xl mb-3">🎛️</div>
      <div className="text-sm">변수를 조정한 뒤 "시뮬레이션 실행"을 누르세요</div>
      <div className="text-xs mt-1">프리셋 버튼으로 주요 시나리오를 바로 테스트할 수 있습니다</div>
    </div>
  )
}
