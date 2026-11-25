import React, { useEffect, useState } from 'react'
import { api, fmtWon } from '../api'
import { useAuth } from '../auth'
import { Badge, Card, EmptyState, ErrorBox, Loading, SectionTitle } from '../components/ui'

export default function Reports() {
  const { user } = useAuth()
  const canWrite = ['OWNER', 'ADMIN', 'MEMBER'].includes(user?.role)
  const [data, setData] = useState(null)
  const [period, setPeriod] = useState('')
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(true)
  const [genning, setGenning] = useState(false)

  const load = () => {
    setLoading(true)
    api('/api/reports').then(d => {
      setData(d)
      if (!period && d.available_months?.length) setPeriod(d.available_months.at(-1))
    }).catch(e => setError(e.message)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const generate = async () => {
    if (!period) return
    setGenning(true); setError(''); setMsg('')
    try {
      await api(`/api/reports/generate?period=${period}`, { method: 'POST' })
      setMsg(`${period} 보고서가 생성되었습니다.`)
      load()
    } catch (e) { setError(e.message) } finally { setGenning(false) }
  }

  const openDetail = async (id) => {
    try { setDetail(await api(`/api/reports/${id}`)) } catch (e) { setError(e.message) }
  }

  const downloadPdf = async (id) => {
    try {
      const blob = await api(`/api/reports/${id}/pdf`)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = `report_${id}.pdf`; a.click()
      URL.revokeObjectURL(url)
    } catch (e) { setError(e.message) }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-lg font-bold text-slate-900">월간 경영 보고서</h1>
          <p className="text-xs text-slate-500">등록된 데이터와 분석 결과를 기반으로 자동 생성 · 내부 검토용 문서이며 공식 재무제표가 아닙니다</p>
        </div>
        {canWrite && (
          <div className="flex gap-2 items-center">
            <select value={period} onChange={e => setPeriod(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm">
              {(data?.available_months || []).map(m => <option key={m} value={m}>{m}</option>)}
            </select>
            <button onClick={generate} disabled={genning}
              className="bg-brand-600 text-white text-sm rounded-lg px-4 py-2 hover:bg-brand-700 disabled:opacity-50">
              {genning ? '생성 중…' : '보고서 생성'}
            </button>
          </div>
        )}
      </div>

      {msg && <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg px-4 py-2 text-sm">{msg}</div>}
      <ErrorBox error={error} />

      {loading ? <Loading /> : (
        <div className="grid lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-1 p-4">
            <SectionTitle>보고서 목록</SectionTitle>
            <div className="space-y-2">
              {(data?.items || []).map(r => (
                <button key={r.id} onClick={() => openDetail(r.id)}
                  className={`w-full text-left border rounded-lg p-3 transition-colors ${detail?.id === r.id ? 'border-brand-400 bg-brand-50/50' : 'border-slate-200 hover:border-brand-300'}`}>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-slate-800">{r.period}</span>
                    <Badge tone="purple">데모</Badge>
                  </div>
                  <div className="text-xs text-slate-500 mt-1 line-clamp-2">{r.title}</div>
                  <div className="text-[11px] text-slate-400 mt-1">{r.created_by} · {r.created_at.slice(0, 16).replace('T', ' ')} · PDF {r.has_pdf ? '✓' : '✗'}</div>
                </button>
              ))}
              {data?.items?.length === 0 && <EmptyState title="생성된 보고서가 없습니다" desc="기간을 선택하고 보고서를 생성하세요." />}
            </div>
          </Card>

          <Card className="lg:col-span-2 p-5">
            {!detail ? <EmptyState title="보고서를 선택하세요" /> : (
              <>
                <div className="flex items-start justify-between gap-3 mb-4">
                  <div>
                    <h2 className="font-bold text-slate-900">{detail.title}</h2>
                    <div className="text-xs text-slate-400 mt-0.5">생성 {detail.created_by} · {detail.created_at.slice(0, 16).replace('T', ' ')}</div>
                  </div>
                  <button onClick={() => downloadPdf(detail.id)}
                    className="bg-slate-800 text-white text-xs rounded-lg px-3 py-2 hover:bg-slate-700 shrink-0">
                    PDF 다운로드
                  </button>
                </div>
                <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs rounded-lg p-3 mb-4">{detail.disclaimer}</div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                  {[
                    ['매출', fmtWon(detail.content?.kpi_summary?.revenue)],
                    ['영업이익', fmtWon(detail.content?.kpi_summary?.operating_profit)],
                    ['영업이익률', `${detail.content?.kpi_summary?.op_margin ?? '-'}%`],
                    ['매출 YoY', `${detail.content?.kpi_summary?.revenue_yoy ?? '-'}%`],
                  ].map(([l, v]) => (
                    <div key={l} className="bg-slate-50 rounded-lg p-3">
                      <div className="text-[11px] text-slate-500">{l}</div>
                      <div className="text-sm font-bold text-slate-800">{v}</div>
                    </div>
                  ))}
                </div>

                {[
                  ['주요 뉴스', (detail.content?.top_news || []).map((n, i) => (
                    <div key={i} className="text-xs text-slate-600 py-1">· [{n.category}/{n.sentiment}] {n.title}</div>))],
                  ['분석 결과', (detail.content?.analyses || []).map((a, i) => (
                    <div key={i} className="text-xs text-slate-600 py-1">· [{a.type}] {a.title} — {a.summary.slice(0, 80)}…</div>))],
                  ['위험 알림', (detail.content?.alerts || []).length ? detail.content.alerts.map((a, i) => (
                    <div key={i} className="text-xs text-slate-600 py-1">· [{a.severity}] {a.title}</div>)) : <div className="text-xs text-slate-400">없음</div>],
                  ['의사결정 · 후속 조치', (() => {
                    const rows = [
                      ...(detail.content?.decisions || []).map((d, i) => <div key={'d' + i} className="text-xs text-slate-600 py-1">· 결정: {d.title} → {d.status} {d.decision}</div>),
                      ...(detail.content?.followups || []).map((f, i) => <div key={'f' + i} className="text-xs text-slate-600 py-1">· 후속: {f.title} [{f.status}] {f.assignee}</div>),
                    ]
                    return rows.length ? rows : <div className="text-xs text-slate-400">없음</div>
                  })()],
                ].map(([title, nodes]) => (
                  <div key={title} className="mb-4">
                    <div className="text-xs font-semibold text-slate-600 mb-1">■ {title}</div>
                    <div className="bg-slate-50 rounded-lg p-3">{nodes}</div>
                  </div>
                ))}
              </>
            )}
          </Card>
        </div>
      )}
    </div>
  )
}
