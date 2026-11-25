import React, { useEffect, useState } from 'react'
import { api, fmtDate } from '../api'
import { Badge, Card, EmptyState, ErrorBox, Loading, SectionTitle, SentimentBadge, SeverityBadge } from '../components/ui'

export default function News() {
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const [filters, setFilters] = useState({ category: '', sentiment: '', importance: '', min_relevance: 0, days: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    const qs = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => { if (v !== '' && v !== 0) qs.set(k, v) })
    api(`/api/news?${qs}`)
      .then(setData).catch(e => setError(e.message)).finally(() => setLoading(false))
  }
  useEffect(load, [filters])

  const openDetail = async (id) => {
    try { setSelected(await api(`/api/news/${id}`)) } catch (e) { setError(e.message) }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-900">뉴스 · 산업 동향</h1>
          <p className="text-xs text-slate-500">기업 관련성 점수가 높은 뉴스만 선별 제공 · 실수집 기사는 출처와 원문 링크가 표시됩니다</p>
        </div>
        {data && <Badge tone="purple">총 {data.total}건</Badge>}
      </div>

      {/* 필터 */}
      <Card className="p-3 flex flex-wrap gap-2 items-center">
        <select value={filters.category} onChange={e => setFilters({ ...filters, category: e.target.value })}
          className="text-sm border border-slate-300 rounded-lg px-2 py-1.5">
          <option value="">전체 카테고리</option>
          {(data?.categories || []).map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={filters.sentiment} onChange={e => setFilters({ ...filters, sentiment: e.target.value })}
          className="text-sm border border-slate-300 rounded-lg px-2 py-1.5">
          <option value="">전체 영향</option>
          <option value="positive">긍정적</option>
          <option value="negative">부정적</option>
          <option value="neutral">중립</option>
        </select>
        <select value={filters.importance} onChange={e => setFilters({ ...filters, importance: e.target.value })}
          className="text-sm border border-slate-300 rounded-lg px-2 py-1.5">
          <option value="">전체 중요도</option>
          <option value="높음">중요도 높음</option>
          <option value="보통">보통</option>
          <option value="낮음">낮음</option>
        </select>
        <select value={filters.days} onChange={e => setFilters({ ...filters, days: e.target.value })}
          className="text-sm border border-slate-300 rounded-lg px-2 py-1.5">
          <option value="">전체 기간</option>
          <option value="7">최근 7일</option>
          <option value="30">최근 30일</option>
          <option value="90">최근 90일</option>
        </select>
        <label className="text-xs text-slate-500 flex items-center gap-1">
          관련성 ≥
          <input type="range" min="0" max="100" step="10" value={filters.min_relevance}
            onChange={e => setFilters({ ...filters, min_relevance: +e.target.value })}
            className="w-24" />
          <span className="w-8">{filters.min_relevance}</span>
        </label>
      </Card>

      <ErrorBox error={error} />
      {loading ? <Loading /> : (
        <div className="grid lg:grid-cols-2 gap-3">
          {(data?.items || []).map(n => (
            <Card key={n.id} className="p-4 cursor-pointer hover:border-brand-300 transition-colors" onClick={() => openDetail(n.id)}>
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <Badge tone="blue">{n.category}</Badge>
                <SeverityBadge severity={n.importance} />
                <SentimentBadge s={n.sentiment} />
                <span className="text-[11px] text-slate-400 ml-auto">관련성 {n.relevance_score}점</span>
              </div>
              <div className="font-semibold text-slate-900 text-sm leading-snug mb-1.5">{n.title}</div>
              <div className="text-xs text-slate-500 line-clamp-2 mb-2">{n.summary}</div>
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>{n.source}</span>
                <span>{n.published_at.slice(0, 10)}</span>
              </div>
            </Card>
          ))}
          {data?.items?.length === 0 && <div className="lg:col-span-2"><EmptyState title="조건에 맞는 뉴스가 없습니다" /></div>}
        </div>
      )}

      {/* 상세 모달 */}
      {selected && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setSelected(null)}>
          <Card className="max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6" >
            <div onClick={e => e.stopPropagation()}>
              <div className="flex items-center gap-2 mb-3 flex-wrap">
                <Badge tone="blue">{selected.category}</Badge>
                <SeverityBadge severity={selected.importance} />
                <SentimentBadge s={selected.sentiment} />
                {selected.is_demo ? <Badge tone="purple">데모 기사</Badge> : <Badge tone="green">실수집</Badge>}
              </div>
              <h2 className="text-lg font-bold text-slate-900 mb-3">{selected.title}</h2>
              <div className="text-xs text-slate-400 mb-4">{selected.source} · {selected.published_at.slice(0, 16).replace('T', ' ')}</div>
              <p className="text-sm text-slate-700 leading-relaxed mb-4">{selected.full_summary || selected.summary}</p>
              <div className="grid md:grid-cols-2 gap-3">
                <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-3">
                  <div className="text-xs font-semibold text-emerald-700 mb-1">기업에 미치는 영향</div>
                  <div className="text-xs text-slate-700">{selected.impact_on_company}</div>
                </div>
                <div className="bg-brand-50 border border-brand-100 rounded-lg p-3">
                  <div className="text-xs font-semibold text-brand-700 mb-1">왜 중요한가 (관련성 근거)</div>
                  <div className="text-xs text-slate-700">{selected.why_relevant}</div>
                </div>
              </div>
              {selected.link && (
                <a href={selected.link} target="_blank" rel="noopener noreferrer"
                  className="inline-block mt-3 text-xs text-brand-600 hover:underline">원문 보기 ↗</a>
              )}
              <div className="mt-3 text-[11px] text-slate-400">
                관련성 점수 {selected.relevance_score}점은 기업 프로필(업종·제품·거래처·관심 위험)과의 규칙 기반 매칭으로 산출된 값입니다.
              </div>
              <button onClick={() => setSelected(null)} className="mt-4 text-sm text-brand-600 hover:underline">닫기</button>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
