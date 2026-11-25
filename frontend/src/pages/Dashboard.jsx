import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api, fmtDate, fmtNum, fmtWon, pct } from '../api'
import { useAuth } from '../auth'
import { Badge, Card, EmptyState, ErrorBox, Loading, SectionTitle, SentimentBadge, SeverityBadge, Stat } from '../components/ui'

const PIE_COLORS = ['#5b72f2', '#10b981', '#f59e0b', '#f43f5e', '#8b5cf6']

function KpiDelta({ v, suffix = '%' }) {
  if (v === null || v === undefined) return null
  const neg = v < 0
  return (
    <span className={`text-xs font-medium ${neg ? 'text-rose-500' : 'text-emerald-600'}`}>
      {neg ? '▼' : '▲'} {pct(Math.abs(v))}
    </span>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    api('/api/dashboard')
      .then(setData).catch(e => setError(e.message)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />
  if (!data?.has_data) return <EmptyState title="등록된 재무 데이터가 없습니다" desc="내부 데이터 관리 메뉴에서 Excel/CSV를 업로드하세요." />

  const k = data.kpis
  const monthly = data.monthly.map(m => ({
    ...m,
    revenue_eok: +(m.revenue / 1e8).toFixed(1),
    op_eok: +(m.operating_profit / 1e8).toFixed(1),
  }))
  const costData = data.cost_mix.map(c => ({ name: c.name, value: +(c.value / 1e8).toFixed(1) }))
  const severityEntries = Object.entries(data.risk_summary).filter(([, v]) => v > 0)

  return (
    <div className="space-y-5">
      {/* AI 경영 요약 배너 */}
      <Card className="p-5 bg-gradient-to-r from-brand-900 to-brand-700 text-white border-0">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs text-brand-200 mb-1">AI 경영 요약 · 규칙 기반 데모 분석</div>
            <div className="text-sm leading-relaxed">
              {k.revenue_yoy !== null && k.revenue_yoy < 0
                ? `최근 매출은 전년동기 대비 ${pct(k.revenue_yoy)}입니다. 수출 비중 ${k.export_ratio}% 환경에서 환율 +${k.fx_mom_pct_series ?? '-'}% 변동과 원자재 비중 ${k.raw_material_ratio}%가 수익성에 영향 중입니다.`
                : `매출 ${fmtWon(k.revenue)} · 영업이익률 ${k.op_margin}%. 주요 시장 지표와 위험 알림을 함께 확인하세요.`}
            </div>
          </div>
          <Link to="/app/analysis" className="shrink-0 bg-white/15 hover:bg-white/25 rounded-lg px-3 py-2 text-xs">분석 보기 →</Link>
        </div>
      </Card>

      {/* KPI 스트립 */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <Stat label="매출" value={fmtWon(k.revenue)} sub={<KpiDelta v={k.revenue_mom} />} />
        <Stat label="영업이익" value={fmtWon(k.operating_profit)} sub={<KpiDelta v={k.op_mom} />} />
        <Stat label="영업이익률" value={`${k.op_margin}%`} sub={`전년동월 ${k.op_margin_yoy !== null ? pct(k.op_margin_yoy).replace('%','%p') : '-'}`} />
        <Stat label="매출 성장률(YoY)" value={pct(k.revenue_yoy)} tone={k.revenue_yoy < 0 ? 'red' : 'green'} />
        <Stat label="환율(USD/KRW)" value={fmtNum(k.fx_avg_rate, 0)} sub={`전월 ${pct(k.fx_mom_pct_series)}`} tone={k.fx_mom_pct_series > 0 ? 'amber' : 'slate'} />
        <Stat label="미확인 위험 알림" value={data.unread_alerts} tone={data.unread_alerts > 0 ? 'red' : 'green'} sub={`후속조치 ${data.open_followups}건 진행중`} />
      </div>

      {/* 차트 1행 */}
      <div className="grid lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 p-4">
          <SectionTitle right={<Link to="/app/data" className="text-xs text-brand-600">데이터 관리 →</Link>}>
            월별 매출 · 영업이익 추이 (억원)
          </SectionTitle>
          <div className="h-64">
            <ResponsiveContainer>
              <ComposedChart data={monthly}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v, n) => [`${v}억`, n === 'revenue_eok' ? '매출' : '영업이익']} />
                <Legend formatter={(v) => (v === 'revenue_eok' ? '매출' : '영업이익')} />
                <Bar dataKey="revenue_eok" fill="#c5d6ff" radius={[3, 3, 0, 0]} />
                <Line dataKey="op_eok" stroke="#5b72f2" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card className="p-4">
          <SectionTitle>비용 구성 (최근월)</SectionTitle>
          <div className="h-64">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={costData} dataKey="value" nameKey="name" innerRadius={45} outerRadius={75} paddingAngle={2}>
                  {costData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => `${v}억`} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* 차트 2행 */}
      <div className="grid lg:grid-cols-3 gap-4">
        <Card className="p-4">
          <SectionTitle>환율 추이 (USD/KRW)</SectionTitle>
          <div className="h-52">
            <ResponsiveContainer>
              <LineChart data={data.fx_series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v) => `${v}원`} />
                <Line dataKey="value" stroke="#f59e0b" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card className="p-4">
          <SectionTitle>제품별 수익률 (최근 3개월)</SectionTitle>
          <div className="space-y-3 mt-2">
            {data.product_margin.length === 0 && <EmptyState title="제품 데이터 없음" />}
            {data.product_margin.map(p => (
              <div key={p.name}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-700 font-medium">{p.name}</span>
                  <span className={p.margin < 10 ? 'text-rose-600 font-semibold' : 'text-emerald-600 font-semibold'}>{p.margin}%</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${p.margin < 10 ? 'bg-rose-400' : 'bg-emerald-500'}`}
                    style={{ width: `${Math.min(100, p.margin * 5)}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-4">
          <SectionTitle>거래처 집중도 (최근 3개월)</SectionTitle>
          <div className="space-y-2 mt-2">
            {data.customer_concentration.length === 0 && <EmptyState title="거래처 데이터 없음" />}
            {data.customer_concentration.map((c, i) => (
              <div key={c.name} className="flex items-center gap-2">
                <span className="text-xs text-slate-500 w-4">{i + 1}</span>
                <div className="flex-1">
                  <div className="flex justify-between text-xs mb-0.5">
                    <span className="text-slate-700 truncate">{c.name}</span>
                    <span className="text-slate-500">{c.share}%</span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full">
                    <div className={`h-full rounded-full ${c.share >= 40 ? 'bg-rose-400' : c.share >= 30 ? 'bg-amber-400' : 'bg-brand-400'}`}
                      style={{ width: `${c.share}%` }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* 하단 리스트 */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card className="p-4">
          <SectionTitle right={<Link to="/app/news" className="text-xs text-brand-600">전체 보기 →</Link>}>관련 중요 뉴스</SectionTitle>
          <div className="space-y-2">
            {data.recent_news.map(n => (
              <Link key={n.id} to="/app/news" className="flex items-start gap-2 p-2 rounded-lg hover:bg-slate-50">
                <SeverityBadge severity={n.importance} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-800 truncate">{n.title}</div>
                  <div className="text-[11px] text-slate-400">{n.category} · 관련성 {n.relevance_score}점 · {n.published_at.slice(0, 10)}</div>
                </div>
                <SentimentBadge s={n.sentiment} />
              </Link>
            ))}
          </div>
        </Card>

        <Card className="p-4">
          <SectionTitle right={<Link to="/app/alerts" className="text-xs text-brand-600">알림 센터 →</Link>}>위험 알림 현황</SectionTitle>
          <div className="flex flex-wrap gap-2 mb-3">
            {severityEntries.length === 0 && <span className="text-sm text-slate-400">현재 감지된 위험 없음</span>}
            {severityEntries.map(([s, c]) => (
              <span key={s} className="inline-flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs">
                <SeverityBadge severity={s} /> <span className="text-slate-500">{c}건</span>
              </span>
            ))}
          </div>
          <div className="space-y-2">
            {data.notifications.map(n => (
              <div key={n.id} className="flex items-start gap-2 p-2 rounded-lg bg-slate-50">
                <Badge tone={n.ntype === 'risk' ? 'red' : n.ntype === 'news' ? 'blue' : 'slate'}>
                  {n.ntype === 'risk' ? '위험' : n.ntype === 'news' ? '뉴스' : n.ntype === 'kpi' ? 'KPI' : n.ntype === 'email' ? '메일대기' : '알림'}
                </Badge>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-800 truncate">{n.title}</div>
                  <div className="text-[11px] text-slate-400">{fmtDate(n.created_at)}</div>
                </div>
                {!n.is_read && <span className="w-2 h-2 rounded-full bg-brand-500 mt-1.5 shrink-0" />}
              </div>
            ))}
          </div>
          <div className="mt-3 flex gap-2">
            <Link to="/app/decisions" className="flex-1 text-center text-xs border border-slate-200 rounded-lg py-2 text-slate-600 hover:bg-slate-50">
              검토 대기 의사결정 {data.pending_decisions}건
            </Link>
            <Link to="/app/reports" className="flex-1 text-center text-xs border border-slate-200 rounded-lg py-2 text-slate-600 hover:bg-slate-50">
              최근 보고서 {data.recent_reports.length}건
            </Link>
          </div>
        </Card>
      </div>

      <div className="text-[11px] text-slate-400">{data.demo_disclaimer}</div>
    </div>
  )
}
