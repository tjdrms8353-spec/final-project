import React, { useEffect, useState } from 'react'
import { api, fmtNum } from '../api'
import { Badge, Card, EmptyState, ErrorBox, Loading, SectionTitle } from '../components/ui'

// KPI 상태별 표시 — 데이터 부족은 0이 아니라 명확한 상태로 표시한다 (정식 전환 C)
const STATUS_LABEL = {
  ok: { label: '정상', tone: 'green' },
  insufficient_data: { label: '데이터 부족', tone: 'amber' },
  not_computable: { label: '계산 불가', tone: 'amber' },
}
const GRADE_TONE = { 정상: 'green', 관심: 'slate', 주의: 'amber', 위험: 'rose', 심각: 'rose', '판단 보류': 'slate' }

function KpiValue({ k }) {
  if (k.status !== 'ok') {
    return <span className="text-sm text-amber-600 font-semibold">{STATUS_LABEL[k.status]?.label || k.status}</span>
  }
  const num = k.unit === '원' ? fmtNum(k.value, 0) : fmtNum(k.value, 2)
  return <span className="text-xl font-bold text-slate-900">{num}<span className="text-xs text-slate-400 font-normal ml-1">{k.unit}</span></span>
}

export default function Kpi() {
  const [kpi, setKpi] = useState(null)
  const [risk, setRisk] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState(null)

  useEffect(() => {
    Promise.all([api('/api/kpi/summary'), api('/api/kpi/risk')])
      .then(([k, r]) => { setKpi(k); setRisk(r) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading />
  if (error) return <ErrorBox error={error} />

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-bold text-slate-900">경영 KPI 분석</h1>
        <p className="text-xs text-slate-500">
          실제 기업 내부 데이터 기반 계산 · 기준월 {kpi.basis_month || '-'} · 데이터 {kpi.months_available}개월
          {kpi.insufficient_count > 0 && <span className="text-amber-600"> · 데이터 부족 {kpi.insufficient_count}개 지표</span>}
        </p>
      </div>

      {!kpi.has_data && <EmptyState title="등록된 월별 재무 데이터가 없습니다" desc="'내부 데이터 관리'에서 업로드하세요." />}

      {/* KPI 카드 */}
      <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3">
        {kpi.kpis.map(k => (
          <Card key={k.key} className="p-4 cursor-pointer" onClick={() => setExpanded(expanded === k.key ? null : k.key)}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-semibold text-slate-700">{k.name}</span>
              <Badge tone={STATUS_LABEL[k.status]?.tone || 'slate'}>{STATUS_LABEL[k.status]?.label || k.status}</Badge>
            </div>
            <KpiValue k={k} />
            {expanded === k.key && (
              <div className="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-500 space-y-0.5">
                <div>계산식: {k.formula}</div>
                <div>사용 데이터: {k.data_used}</div>
                <div>기준: {k.basis} · 기간: {k.period}</div>
                {k.note && <div className="text-amber-600">{k.note}</div>}
              </div>
            )}
          </Card>
        ))}
      </div>

      {/* 제품별 수익성·거래처 의존도 */}
      {(kpi.product_profitability?.length > 0 || kpi.customer_dependence?.top_customer) && (
        <div className="grid lg:grid-cols-2 gap-3">
          {kpi.product_profitability?.length > 0 && (
            <Card className="p-4">
              <SectionTitle>제품별 수익성 ({kpi.basis_month})</SectionTitle>
              <div className="space-y-1.5">
                {kpi.product_profitability.map(p => (
                  <div key={p.product} className="flex items-center justify-between text-sm">
                    <span className="text-slate-700">{p.product}</span>
                    {p.status === 'ok'
                      ? <span className={`font-semibold ${p.margin_pct >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>{p.margin_pct}%</span>
                      : <span className="text-xs text-amber-600">{STATUS_LABEL[p.status]?.label}</span>}
                  </div>
                ))}
              </div>
            </Card>
          )}
          {kpi.customer_dependence?.top_customer && (
            <Card className="p-4">
              <SectionTitle>거래처 의존도 ({kpi.customer_dependence.period})</SectionTitle>
              <div className="text-sm text-slate-700">
                최대 거래처 <b>{kpi.customer_dependence.top_customer}</b> — 매출 비중{' '}
                <b className="text-brand-700">{kpi.customer_dependence.share_pct}%</b>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* 위험 평가 */}
      {risk && (
        <Card className="p-4">
          <SectionTitle right={
            <Badge tone={GRADE_TONE[risk.overall_grade] || 'slate'}>
              종합 {risk.overall_grade}{risk.overall_score != null ? ` (${risk.overall_score}점)` : ''}
            </Badge>}>
            기업 맞춤 위험 평가
          </SectionTitle>
          <p className="text-[11px] text-slate-400 mb-3">
            수출입 구조: {({ export: '수출 중심', import: '수입 중심', balanced: '균형', unknown: '불명확' })[risk.company_context?.trade_direction] || '-'}
            {risk.insufficient_count > 0 && ` · 데이터 부족 ${risk.insufficient_count}개 항목(판단 보류)`}
          </p>
          <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-2">
            {risk.items.map(i => (
              <div key={i.category} className="border border-slate-100 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold text-slate-700">{i.category}</span>
                  <Badge tone={GRADE_TONE[i.grade] || 'slate'}>{i.grade}</Badge>
                </div>
                {i.score != null && <div className="text-lg font-bold text-slate-900 mb-1">{i.score}점</div>}
                {i.evidence && <div className="text-[11px] text-slate-500">{i.evidence}</div>}
                {i.note && <div className="text-[11px] text-amber-600 mt-1">{i.note}</div>}
                <div className="text-[10px] text-slate-300 mt-1">기준: {i.basis}</div>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-slate-400 mt-3">{risk.note}</p>
        </Card>
      )}
    </div>
  )
}
