import React, { useEffect, useState } from 'react'
import { api, fmtDate } from '../api'
import { useAuth } from '../auth'
import { Badge, Card, EmptyState, ErrorBox, Loading, SectionTitle } from '../components/ui'

const STATUS_TONE = { '검토 대기': 'slate', '검토 중': 'blue', '수용': 'green', '보류': 'amber', '미수용': 'red', '처리 완료': 'green' }
const FU_TONE = { '등록': 'slate', '진행 중': 'blue', '완료': 'green' }

export default function Decisions() {
  const { user } = useAuth()
  const isAdmin = ['OWNER', 'ADMIN'].includes(user?.role)
  const canWrite = ['OWNER', 'ADMIN', 'MEMBER'].includes(user?.role)
  const [data, setData] = useState(null)
  const [analyses, setAnalyses] = useState([])
  const [form, setForm] = useState({ analysis_result_id: '', status: '검토 중', decision: '', reason: '', assignee: '', due_date: '' })
  const [fuForm, setFuForm] = useState({ decision_id: '', title: '', assignee: '', due_date: '' })
  const [showForm, setShowForm] = useState(false)
  const [showFu, setShowFu] = useState(false)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    Promise.all([
      api('/api/decisions'),
      api('/api/analysis'),
    ]).then(([d, a]) => { setData(d); setAnalyses(a.items) })
      .catch(e => setError(e.message)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const createDecision = async (e) => {
    e.preventDefault(); setError(''); setMsg('')
    try {
      await api('/api/decisions', { method: 'POST', body: {
        analysis_result_id: form.analysis_result_id ? Number(form.analysis_result_id) : null,
        status: form.status, decision: form.decision, reason: form.reason,
        assignee: form.assignee, due_date: form.due_date,
      }})
      setMsg('의사결정이 등록되었습니다.'); setShowForm(false)
      setForm({ analysis_result_id: '', status: '검토 중', decision: '', reason: '', assignee: '', due_date: '' })
      load()
    } catch (err) { setError(err.message) }
  }

  const updateDecision = async (id, patch) => {
    try { await api(`/api/decisions/${id}`, { method: 'PATCH', body: patch }); load() }
    catch (e) { setError(e.message) }
  }

  const createFu = async (e) => {
    e.preventDefault(); setError('')
    try {
      await api('/api/follow-ups', { method: 'POST', body: {
        decision_id: fuForm.decision_id ? Number(fuForm.decision_id) : null,
        title: fuForm.title, assignee: fuForm.assignee, due_date: fuForm.due_date,
      }})
      setMsg('후속 조치가 등록되었습니다.'); setShowFu(false)
      setFuForm({ decision_id: '', title: '', assignee: '', due_date: '' })
      load()
    } catch (err) { setError(err.message) }
  }

  const updateFu = async (id, status) => {
    try { await api(`/api/follow-ups/${id}`, { method: 'PATCH', body: { status } }); load() }
    catch (e) { setError(e.message) }
  }

  const allFollowUps = (data?.items || []).flatMap(d =>
    d.follow_ups.map(f => ({ ...f, decisionTitle: d.analysis_title })))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-900">의사결정 · 후속 조치 관리</h1>
          <p className="text-xs text-slate-500">AI 분석 결과에 대한 최종 결정은 항상 사람이 수행합니다 · 결정 이력이 감사 로그에 기록됩니다</p>
        </div>
        {isAdmin && (
          <div className="flex gap-2">
            <button onClick={() => setShowFu(!showFu)} className="border border-slate-300 text-sm rounded-lg px-3 py-2 hover:bg-slate-50">+ 후속 조치</button>
            <button onClick={() => setShowForm(!showForm)} className="bg-brand-600 text-white text-sm rounded-lg px-3 py-2 hover:bg-brand-700">+ 의사결정 등록</button>
          </div>
        )}
      </div>

      {msg && <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg px-4 py-2 text-sm">{msg}</div>}
      <ErrorBox error={error} />

      {showForm && isAdmin && (
        <Card className="p-5">
          <SectionTitle>새 의사결정 등록</SectionTitle>
          <form onSubmit={createDecision} className="grid md:grid-cols-3 gap-3">
            <label className="text-xs text-slate-500">연결 분석 결과
              <select value={form.analysis_result_id} onChange={e => setForm({ ...form, analysis_result_id: e.target.value })}
                className="mt-1 w-full border border-slate-300 rounded-lg px-2 py-2 text-sm">
                <option value="">(선택) 분석 연결 안 함</option>
                {analyses.map(a => <option key={a.id} value={a.id}>[{a.analysis_type_label}] {a.title.slice(0, 40)}</option>)}
              </select></label>
            <label className="text-xs text-slate-500">상태
              <select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}
                className="mt-1 w-full border border-slate-300 rounded-lg px-2 py-2 text-sm">
                {['검토 대기', '검토 중', '수용', '보류', '미수용', '처리 완료'].map(s => <option key={s}>{s}</option>)}
              </select></label>
            <label className="text-xs text-slate-500">결정
              <select value={form.decision} onChange={e => setForm({ ...form, decision: e.target.value })}
                className="mt-1 w-full border border-slate-300 rounded-lg px-2 py-2 text-sm">
                <option value="">(선택)</option><option>수용</option><option>보류</option><option>미수용</option>
              </select></label>
            <label className="text-xs text-slate-500 md:col-span-3">결정 사유
              <textarea value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} rows={2}
                className="mt-1 w-full border border-slate-300 rounded-lg px-2 py-2 text-sm" placeholder="판단 근거와 사유를 기록하세요" /></label>
            <label className="text-xs text-slate-500">담당자
              <input value={form.assignee} onChange={e => setForm({ ...form, assignee: e.target.value })}
                className="mt-1 w-full border border-slate-300 rounded-lg px-2 py-2 text-sm" placeholder="예: 박관리" /></label>
            <label className="text-xs text-slate-500">처리 기한
              <input type="date" value={form.due_date} onChange={e => setForm({ ...form, due_date: e.target.value })}
                className="mt-1 w-full border border-slate-300 rounded-lg px-2 py-2 text-sm" /></label>
            <div className="flex items-end"><button className="bg-brand-600 text-white text-sm rounded-lg px-4 py-2">등록</button></div>
          </form>
        </Card>
      )}

      {showFu && canWrite && (
        <Card className="p-5">
          <SectionTitle>새 후속 조치 등록</SectionTitle>
          <form onSubmit={createFu} className="grid md:grid-cols-4 gap-3">
            <label className="text-xs text-slate-500 md:col-span-2">조치 내용
              <input required value={fuForm.title} onChange={e => setFuForm({ ...fuForm, title: e.target.value })}
                className="mt-1 w-full border border-slate-300 rounded-lg px-2 py-2 text-sm" placeholder="예: 환헤지 조건 협의" /></label>
            <label className="text-xs text-slate-500">연결 의사결정
              <select value={fuForm.decision_id} onChange={e => setFuForm({ ...fuForm, decision_id: e.target.value })}
                className="mt-1 w-full border border-slate-300 rounded-lg px-2 py-2 text-sm">
                <option value="">(선택)</option>
                {(data?.items || []).map(d => <option key={d.id} value={d.id}>#{d.id} {d.analysis_title.slice(0, 30)}</option>)}
              </select></label>
            <label className="text-xs text-slate-500">담당자 / 기한
              <div className="flex gap-1 mt-1">
                <input value={fuForm.assignee} onChange={e => setFuForm({ ...fuForm, assignee: e.target.value })}
                  className="w-1/2 border border-slate-300 rounded-lg px-2 py-2 text-sm" placeholder="담당자" />
                <input type="date" value={fuForm.due_date} onChange={e => setFuForm({ ...fuForm, due_date: e.target.value })}
                  className="w-1/2 border border-slate-300 rounded-lg px-2 py-2 text-sm" />
              </div></label>
            <div className="md:col-span-4"><button className="bg-brand-600 text-white text-sm rounded-lg px-4 py-2">등록</button></div>
          </form>
        </Card>
      )}

      {loading ? <Loading /> : (
        <>
          {/* 의사결정 목록 */}
          <Card className="overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 text-sm font-semibold text-slate-700">의사결정 목록</div>
            {(data?.items || []).length === 0 ? <EmptyState title="등록된 의사결정이 없습니다" desc="관리자가 분석 결과에 대해 결정을 등록하세요." /> : (
              <div className="divide-y divide-slate-100">
                {data.items.map(d => (
                  <div key={d.id} className="p-4">
                    <div className="flex items-start justify-between gap-3 flex-wrap">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge tone={STATUS_TONE[d.status] || 'slate'}>{d.status}</Badge>
                          {d.decision && <Badge tone={d.decision === '수용' ? 'green' : d.decision === '미수용' ? 'red' : 'amber'}>결정: {d.decision}</Badge>}
                          <span className="text-xs text-slate-400">#{d.id} · {fmtDate(d.created_at)} · 등록 {d.created_by}</span>
                        </div>
                        <div className="text-sm font-medium text-slate-800 mt-1">{d.analysis_title}</div>
                        {d.reason && <div className="text-xs text-slate-500 mt-1">사유: {d.reason}</div>}
                        <div className="text-[11px] text-slate-400 mt-1">담당 {d.assignee || '-'} · 기한 {d.due_date || '-'}</div>
                      </div>
                      {isAdmin && (
                        <div className="flex gap-1 shrink-0">
                          {['검토 중', '처리 완료'].map(s => (
                            <button key={s} onClick={() => updateDecision(d.id, { status: s })}
                              className="text-[11px] border border-slate-300 rounded px-2 py-1 hover:bg-slate-50">{s}</button>
                          ))}
                        </div>
                      )}
                    </div>
                    {d.follow_ups.length > 0 && (
                      <div className="mt-2 ml-3 space-y-1">
                        {d.follow_ups.map(f => (
                          <div key={f.id} className="flex items-center gap-2 text-xs">
                            <Badge tone={FU_TONE[f.status] || 'slate'}>{f.status}</Badge>
                            <span className="text-slate-700">{f.title}</span>
                            <span className="text-slate-400">담당 {f.assignee || '-'} · 기한 {f.due_date || '-'}</span>
                            {canWrite && f.status !== '완료' && (
                              <button onClick={() => updateFu(f.id, '완료')} className="text-brand-600 hover:underline">완료 처리</button>
                            )}
                            {canWrite && f.status === '등록' && (
                              <button onClick={() => updateFu(f.id, '진행 중')} className="text-slate-500 hover:underline">진행 중</button>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* 독립 후속조치 */}
          {allFollowUps.filter(f => !data.items.some(d => d.follow_ups.some(x => x.id === f.id))).length > 0 && (
            <Card className="p-4">
              <SectionTitle>기타 후속 조치</SectionTitle>
              {allFollowUps.map(f => (
                <div key={f.id} className="text-xs text-slate-600 py-1">· [{f.status}] {f.title} — {f.assignee} ({f.due_date})</div>
              ))}
            </Card>
          )}
        </>
      )}
    </div>
  )
}
