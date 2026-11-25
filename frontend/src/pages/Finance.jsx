import React, { useEffect, useState } from 'react'
import { LineChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from 'recharts'
import { api, fmtNum, pct } from '../api'
import { Badge, Card, EmptyState, ErrorBox, Loading, SectionTitle } from '../components/ui'

const GROUPS = {
  '환율·금리': ['USD_KRW', 'BASE_RATE', 'FED_RATE'],
  '주식 지수': ['KOSPI', 'NASDAQ', 'SEMI_ETF'],
  '원자재·에너지': ['WTI_OIL', 'COPPER', 'SILICON_WAFER'],
}

export default function Finance() {
  const [series, setSeries] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api('/api/finance/series').then(setSeries).catch(e => setError(e.message)).finally(() => setLoading(false))
  }, [])

  const openDetail = async (key) => {
    setSelected(key)
    try { setDetail(await api(`/api/finance/series/${key}`)) } catch (e) { setError(e.message) }
  }

  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />

  const byKey = Object.fromEntries(series.map(s => [s.series_key, s]))

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-bold text-slate-900">금융 · 경제 데이터</h1>
        <p className="text-xs text-slate-500">각 지표가 기업 경영에 미치는 영향을 함께 표시 · 모든 수치는 데모용 생성 데이터입니다</p>
      </div>

      {Object.entries(GROUPS).map(([gname, keys]) => (
        <div key={gname}>
          <div className="text-sm font-semibold text-slate-600 mb-2">{gname}</div>
          <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3">
            {keys.map(k => {
              const s = byKey[k]
              if (!s) return null
              const up = (s.change_pct ?? 0) >= 0
              return (
                <Card key={k} className="p-4 cursor-pointer hover:border-brand-300 transition-colors" onClick={() => openDetail(k)}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-semibold text-slate-800">{s.series_name}</span>
                    <span className={`text-xs font-bold ${up ? 'text-rose-500' : 'text-emerald-600'}`}>{pct(s.change_pct)}</span>
                  </div>
                  <div className="text-2xl font-bold text-slate-900">{fmtNum(s.latest, s.unit === 'pt' ? 0 : 2)}<span className="text-xs text-slate-400 font-normal ml-1">{s.unit}</span></div>
                  <div className="text-[11px] text-slate-400 mt-1">전월 {fmtNum(s.previous, s.unit === 'pt' ? 0 : 2)} · 기준 {s.points.at(-1)?.month}</div>
                  {/* 미니 스파크라인 */}
                  <div className="h-10 mt-2">
                    <ResponsiveContainer>
                      <LineChart data={s.points.slice(-12)}>
                        <Line dataKey="value" stroke="#5b72f2" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              )
            })}
          </div>
        </div>
      ))}

      {/* 상세 */}
      {selected && (
        <Card className="p-5">
          <SectionTitle right={<button onClick={() => setSelected(null)} className="text-xs text-slate-400 hover:text-slate-600">닫기 ✕</button>}>
            {detail?.series_name || selected} 상세
          </SectionTitle>
          {detail?.impact_note && (
            <div className="bg-brand-50 border border-brand-100 rounded-lg p-3 mb-3">
              <div className="text-xs font-semibold text-brand-700 mb-1">기업 경영에 미치는 영향</div>
              <div className="text-xs text-slate-700">{detail.impact_note}</div>
            </div>
          )}
          <div className="h-64">
            {detail ? (
              <ResponsiveContainer>
                <LineChart data={detail.points}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                  <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(v) => `${fmtNum(v, 2)} ${detail.unit}`} />
                  <Line dataKey="value" stroke="#5b72f2" strokeWidth={2} dot={{ r: 2 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : <Loading />}
          </div>
          <div className="mt-2 flex justify-between text-[11px] text-slate-400">
            <span>출처: {detail?.source} (데모 생성 데이터)</span>
            <span>최근 기준월: {detail?.points?.at(-1)?.month}</span>
          </div>
        </Card>
      )}
    </div>
  )
}
