import React, { useEffect, useState } from 'react'
import { api, fmtDate } from '../api'
import { Badge, Card, EmptyState, ErrorBox, Loading, SectionTitle } from '../components/ui'

const STATUS_TONE = { pending: 'amber', sent: 'green', failed: 'red', skipped: 'slate' }
const STATUS_LABEL = { pending: '발송 대기', sent: '발송 완료', failed: '발송 실패', skipped: '건너뜀' }
const CHANNEL_LABEL = { email: '이메일', kakao: '카카오' }
const JOB_LABEL = { done: '완료', running: '실행 중', error: '오류', skipped: '중복 건너뜀' }

function ConfigBadge({ ok, label }) {
  return <Badge tone={ok ? 'green' : 'amber'}>{label}: {ok ? '설정됨' : '미설정'}</Badge>
}

export default function Ops() {
  const [ops, setOps] = useState(null)
  const [deliveries, setDeliveries] = useState(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [error, setError] = useState('')
  const [testChannel, setTestChannel] = useState('email')
  const [testAddress, setTestAddress] = useState('')
  const [testBusy, setTestBusy] = useState(false)
  const [testMsg, setTestMsg] = useState('')

  const sendTest = async (e) => {
    e.preventDefault()
    setTestBusy(true); setTestMsg(''); setError('')
    try {
      const r = await api('/api/ops/test-delivery', {
        method: 'POST', body: { channel: testChannel, address: testAddress } })
      setTestMsg(`큐 등록 완료 (#${r.id}) — ${r.note}`)
      setTestAddress('')
      api('/api/deliveries').then(setDeliveries).catch(() => {})
    } catch (err) { setError(err.message) }
    finally { setTestBusy(false) }
  }

  useEffect(() => {
    api('/api/ops/status').then(setOps).catch(e => setError(e.message))
  }, [])

  useEffect(() => {
    const qs = statusFilter ? `?status=${statusFilter}` : ''
    api(`/api/deliveries${qs}`).then(setDeliveries).catch(e => setError(e.message))
  }, [statusFilter])

  if (error) return <ErrorBox error={error} />
  if (!ops) return <Loading />

  const d = ops.deliveries
  const jobEntries = Object.entries(ops.analysis_jobs || {})

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-bold text-slate-900">운영 상태</h1>
        <p className="text-xs text-slate-500">
          스케줄러·수집기·발송 큐·LLM 사용량 현황 — 관리자 전용 ·
          환경 {ops.env} · 버전 {ops.version} · 서버시각 {fmtDate(ops.server_time)}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="p-5">
          <SectionTitle>알림 발송 큐</SectionTitle>
          <div className="flex gap-4 text-center">
            {[['pending', '대기'], ['sent', '완료'], ['failed', '실패'], ['skipped', '건너뜀']].map(([k, label]) => (
              <div key={k}>
                <div className="text-2xl font-bold text-slate-800">{d[k] ?? 0}</div>
                <div className="text-[11px] text-slate-500">{label}</div>
              </div>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <ConfigBadge ok={d.smtp_configured} label="SMTP(이메일)" />
            <ConfigBadge ok={d.kakao_configured} label="카카오" />
          </div>
          <p className="mt-2 text-[11px] text-slate-400">
            미설정 상태에서 등록된 발송 건은 '발송 대기'로 남고, 서버 환경변수(SMTP_*/KAKAO_*) 설정 후 자동 발송됩니다.
          </p>
          <form onSubmit={sendTest} className="mt-3 flex gap-2">
            <select value={testChannel} onChange={e => setTestChannel(e.target.value)}
              className="text-xs border border-slate-300 rounded-lg px-2 py-1.5">
              <option value="email">이메일</option>
              <option value="kakao">카카오</option>
            </select>
            <input value={testAddress} onChange={e => setTestAddress(e.target.value)} required
              placeholder={testChannel === 'email' ? '테스트 이메일 주소' : '테스트 전화번호'}
              className="flex-1 text-xs border border-slate-300 rounded-lg px-3 py-1.5" />
            <button disabled={testBusy}
              className="text-xs bg-slate-700 text-white rounded-lg px-3 py-1.5 hover:bg-slate-800 disabled:opacity-50">
              {testBusy ? '등록 중…' : '테스트 발송'}
            </button>
          </form>
          {testMsg && <p className="mt-1 text-[11px] text-emerald-600">{testMsg}</p>}
        </Card>

        <Card className="p-5">
          <SectionTitle>스케줄러 · 분석 작업</SectionTitle>
          <div className="text-sm text-slate-700 space-y-1">
            <div>스케줄러 주기: <b>{ops.scheduler_interval_sec}초</b></div>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {jobEntries.length === 0 && <span className="text-slate-400 text-xs">분석 작업 없음</span>}
              {jobEntries.map(([k, v]) => (
                <Badge key={k} tone={k === 'error' ? 'red' : k === 'running' ? 'blue' : 'slate'}>
                  {JOB_LABEL[k] || k} {v}건
                </Badge>
              ))}
            </div>
          </div>
        </Card>

        <Card className="p-5 md:col-span-2">
          <SectionTitle>데이터 수집기 — 활성 {ops.collectors.enabled} / 전체 {ops.collectors.total}</SectionTitle>
          {ops.collectors.list.length === 0 ? (
            <div className="text-xs text-slate-400">수집기 상태 없음 — 첫 스케줄러 실행 후 표시됩니다</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="text-slate-400">
                  <tr>{['수집기', '상태', '주기', '마지막 실행', '마지막 성공', '다음 실행', '오류'].map(h =>
                    <th key={h} className="px-2 py-1 text-left font-medium whitespace-nowrap">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {ops.collectors.list.map(c => (
                    <tr key={c.name}>
                      <td className="px-2 py-1.5 font-medium text-slate-700">{c.name}</td>
                      <td className="px-2 py-1.5">
                        <Badge tone={c.enabled ? 'green' : 'slate'}>{c.enabled ? '활성' : '비활성'}</Badge>
                      </td>
                      <td className="px-2 py-1.5 text-slate-500">{Math.round(c.interval_sec / 3600 * 10) / 10}h</td>
                      <td className="px-2 py-1.5 text-slate-500 whitespace-nowrap">{fmtDate(c.last_run_at)}</td>
                      <td className="px-2 py-1.5 text-slate-500 whitespace-nowrap">{fmtDate(c.last_success_at)}</td>
                      <td className="px-2 py-1.5 text-slate-500 whitespace-nowrap">{fmtDate(c.next_run_at)}</td>
                      <td className="px-2 py-1.5 text-rose-500 max-w-[180px] truncate">{c.last_error}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {ops.collectors.recent_errors.length > 0 && (
            <div className="mt-3 space-y-1">
              <div className="text-xs font-medium text-rose-600">최근 수집 실패 이력</div>
              {ops.collectors.recent_errors.map((e, i) => (
                <div key={i} className="text-[11px] text-slate-500">
                  {fmtDate(e.at)} · {e.collector} — {e.error}
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-5">
          <SectionTitle>LLM 사용량 (이번 달)</SectionTitle>
          <div className="flex gap-6 text-center">
            <div>
              <div className="text-2xl font-bold text-slate-800">{ops.llm_month.calls}</div>
              <div className="text-[11px] text-slate-500">호출</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-slate-800">{Number(ops.llm_month.tokens).toLocaleString()}</div>
              <div className="text-[11px] text-slate-500">토큰</div>
            </div>
          </div>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-3">
          <SectionTitle className="flex-1">발송 이력</SectionTitle>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg px-2 py-1.5">
            <option value="">전체 상태</option>
            {Object.entries(STATUS_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        {!deliveries ? <Loading /> : deliveries.items.length === 0 ? (
          <EmptyState title="발송 이력이 없습니다" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500">
                <tr>{['시각', '채널', '수신', '제목', '상태', '시도', '오류'].map(h =>
                  <th key={h} className="px-3 py-2 text-left font-medium whitespace-nowrap">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {deliveries.items.map(it => (
                  <tr key={it.id}>
                    <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap">{fmtDate(it.sent_at || it.created_at)}</td>
                    <td className="px-3 py-2">{CHANNEL_LABEL[it.channel] || it.channel}</td>
                    <td className="px-3 py-2 text-xs">{it.address}</td>
                    <td className="px-3 py-2 text-xs">{it.title}</td>
                    <td className="px-3 py-2"><Badge tone={STATUS_TONE[it.status] || 'slate'}>{STATUS_LABEL[it.status] || it.status}</Badge></td>
                    <td className="px-3 py-2 text-xs text-slate-500">{it.attempts}</td>
                    <td className="px-3 py-2 text-[11px] text-slate-400 max-w-[200px] truncate">{it.last_error}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
