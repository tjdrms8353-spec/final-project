import React, { useEffect, useState } from 'react'
import { api, fmtDate } from '../api'
import { useAuth } from '../auth'
import { Badge, Card, EmptyState, ErrorBox, Loading, SectionTitle } from '../components/ui'

const TABS = [
  ['growth', '미래 성장 가능성'],
  ['direction', '사업 방향성'],
  ['risk', '위험 요소 관리'],
]
const STATUS_TONES = { '검토 대기': 'slate', '검토 중': 'blue', '수용': 'green', '보류': 'amber', '미수용': 'red', '처리 완료': 'green' }

export default function AiAnalysis() {
  const { user } = useAuth()
  const canReview = ['OWNER', 'ADMIN'].includes(user?.role)
  const canRun = ['OWNER', 'ADMIN', 'MEMBER'].includes(user?.role)
  const [tab, setTab] = useState('growth')
  const [data, setData] = useState(null)
  const [open, setOpen] = useState(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)

  const load = () => {
    setLoading(true)
    api(`/api/analysis?analysis_type=${tab}`)
      .then(setData).catch(e => setError(e.message)).finally(() => setLoading(false))
  }
  useEffect(load, [tab])

  const runAnalysis = async () => {
    setRunning(true); setError(''); setMsg('')
    try {
      const r = await api('/api/analysis/run', { method: 'POST' })
      setMsg(`분석 완료: 신규 분석 ${r.new_analyses}건, 위험 알림 ${r.new_alerts}건 생성`)
      load()
    } catch (e) { setError(e.message) } finally { setRunning(false) }
  }

  const review = async (id, status) => {
    try {
      await api(`/api/analysis/${id}/review`, { method: 'PATCH', body: { status, note: '' } })
      load()
    } catch (e) { setError(e.message) }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-lg font-bold text-slate-900">AI 경영 분석</h1>
          <p className="text-xs text-slate-500">
            규칙 기반 데모 분석 엔진 · 실제 LLM이 아니며 모든 결과는 "데모 분석"입니다 · 최종 의사결정은 관리자가 수행
          </p>
        </div>
        {canRun && (
          <button onClick={runAnalysis} disabled={running}
            className="bg-brand-600 text-white text-sm rounded-lg px-4 py-2 hover:bg-brand-700 disabled:opacity-50">
            {running ? '분석 실행 중…' : '지금 분석 실행'}
          </button>
        )}
      </div>

      {msg && <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg px-4 py-2.5 text-sm">{msg}</div>}
      <ErrorBox error={error} />

      <div className="flex gap-2">
        {TABS.map(([k, l]) => (
          <button key={k} onClick={() => { setTab(k); setOpen(null) }}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === k ? 'bg-brand-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:border-brand-300'}`}>
            {l}
          </button>
        ))}
      </div>

      {loading ? <Loading /> : (
        <div className="space-y-3">
          {(data?.items || []).map(a => (
            <Card key={a.id} className="p-5">
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    <Badge tone="purple">{a.engine_label}</Badge>
                    <Badge tone={STATUS_TONES[a.status] || 'slate'}>{a.status}</Badge>
                    <span className="text-[11px] text-slate-400">{fmtDate(a.created_at)} · 트리거: {a.trigger}</span>
                  </div>
                  <div className="font-semibold text-slate-900">{a.title}</div>
                  <div className="text-sm text-slate-600 mt-1 leading-relaxed">{a.summary}</div>
                </div>
                <button onClick={() => setOpen(open === a.id ? null : a.id)}
                  className="text-xs text-brand-600 border border-brand-200 rounded-lg px-3 py-1.5 hover:bg-brand-50 shrink-0">
                  {open === a.id ? '접기' : '상세 근거 보기'}
                </button>
              </div>

              {open === a.id && (
                <div className="mt-4 border-t border-slate-100 pt-4 space-y-3">
                  <div className="grid md:grid-cols-2 gap-3">
                    <div className="bg-slate-50 rounded-lg p-3">
                      <div className="text-xs font-semibold text-slate-600 mb-1">분석에 사용한 데이터</div>
                      <div className="text-xs text-slate-600">{a.data_sources}</div>
                    </div>
                    <div className="bg-slate-50 rounded-lg p-3">
                      <div className="text-xs font-semibold text-slate-600 mb-1">분석 기준일</div>
                      <div className="text-xs text-slate-600">{a.basis_date}</div>
                    </div>
                  </div>
                  {a.details?.metrics && (
                    <div className="bg-slate-50 rounded-lg p-3">
                      <div className="text-xs font-semibold text-slate-600 mb-2">주요 수치</div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                        {Object.entries(a.details.metrics).map(([k, v]) => (
                          <div key={k} className="text-xs">
                            <div className="text-slate-400">{k}</div>
                            <div className="font-semibold text-slate-800">{v}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {a.details?.active_alerts && (
                    <div className="bg-slate-50 rounded-lg p-3">
                      <div className="text-xs font-semibold text-slate-600 mb-1">활성 위험 알림</div>
                      {a.details.active_alerts.length === 0
                        ? <div className="text-xs text-slate-500">없음</div>
                        : a.details.active_alerts.map((x, i) => (
                          <div key={i} className="text-xs text-slate-600">· [{x.severity}] {x.title}</div>
                        ))}
                    </div>
                  )}
                  <div className="grid md:grid-cols-3 gap-3">
                    <div className="bg-amber-50 border border-amber-100 rounded-lg p-3">
                      <div className="text-xs font-semibold text-amber-700 mb-1">기업에 미치는 영향</div>
                      <div className="text-xs text-slate-700">{a.impact}</div>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                      <div className="text-xs font-semibold text-slate-600 mb-1">불확실성 · 가정</div>
                      <div className="text-xs text-slate-700">{a.uncertainty}</div>
                    </div>
                    <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-3">
                      <div className="text-xs font-semibold text-emerald-700 mb-1">AI 대응 제안 (검토용)</div>
                      <div className="text-xs text-slate-700">{a.suggestions}</div>
                    </div>
                  </div>
                  <div className="text-[11px] text-slate-400 bg-slate-50 rounded-lg p-2">
                    {a.details?.disclaimer || ''}
                  </div>
                  {canReview && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">관리자 검토:</span>
                      {['검토 중', '수용', '보류', '미수용', '처리 완료'].map(s => (
                        <button key={s} onClick={() => review(a.id, s)}
                          className={`text-xs rounded-lg px-2.5 py-1 border ${a.status === s ? 'bg-brand-600 text-white border-brand-600' : 'border-slate-300 text-slate-600 hover:bg-slate-50'}`}>
                          {s}
                        </button>
                      ))}
                      {a.reviewed_by && <span className="text-[11px] text-slate-400">({a.reviewed_by} 검토)</span>}
                    </div>
                  )}
                </div>
              )}
            </Card>
          ))}
          {data?.items?.length === 0 && <EmptyState title="분석 결과가 없습니다" desc="'지금 분석 실행'을 누르거나 데이터를 업로드하세요." />}
        </div>
      )}
    </div>
  )
}
