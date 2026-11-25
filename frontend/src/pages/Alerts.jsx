import React, { useEffect, useState } from 'react'
import { api, fmtDate } from '../api'
import { Badge, Card, EmptyState, ErrorBox, Loading, SectionTitle, SeverityBadge } from '../components/ui'

export default function Alerts() {
  const [tab, setTab] = useState('risk')
  const [alerts, setAlerts] = useState(null)
  const [notifs, setNotifs] = useState(null)
  const [events, setEvents] = useState(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState('')

  const load = () => {
    setLoading(true)
    Promise.all([
      api('/api/alerts'),
      api('/api/notifications'),
      api('/api/demo-events'),
    ]).then(([a, n, e]) => { setAlerts(a); setNotifs(n); setEvents(e) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const setAlertStatus = async (id, status) => {
    try { await api(`/api/alerts/${id}`, { method: 'PATCH', body: { status } }); load() }
    catch (e) { setError(e.message) }
  }
  const readNotif = async (id) => {
    try { await api(`/api/notifications/${id}/read`, { method: 'PATCH' }); load() } catch (e) { setError(e.message) }
  }
  const readAll = async () => {
    try { await api('/api/notifications/read-all', { method: 'POST' }); load() } catch (e) { setError(e.message) }
  }
  const runEvent = async (key) => {
    setRunning(key); setMsg(''); setError('')
    try {
      const r = await api(`/api/demo-events/${key}/run`, { method: 'POST' })
      setMsg(`이벤트 실행 완료 — ${r.steps.join(' → ')}`)
      load()
    } catch (e) { setError(e.message) } finally { setRunning('') }
  }

  const STATUS_LABEL = { unread: '미확인', read: '확인함', acknowledged: '인지함' }
  const NTYPE_LABEL = { risk: '위험', news: '뉴스', kpi: 'KPI', analysis: '분석', report: '보고서', email: '메일대기', weekly: '주간요약' }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-900">알림 센터 · 자동 모니터링</h1>
          <p className="text-xs text-slate-500">분석 실행 버튼 없이도 데이터 업로드·시장 변동·뉴스 등록 시 자동 분석이 실행됩니다</p>
        </div>
        <Badge tone="purple">자동 분석 주기: 2분 (데모)</Badge>
      </div>

      {/* 데모 이벤트 */}
      <Card className="p-4 border-amber-200 bg-amber-50/50">
        <SectionTitle right={<Badge tone="amber">데모 전용</Badge>}>시장환경 변동 재현 (테스트 이벤트)</SectionTitle>
        <p className="text-xs text-slate-500 mb-3">실제 금융 데이터가 아닌 테스트용 이벤트입니다. 실행하면 데이터 등록 → 분석 → 위험 판단 → 알림 → 대시보드 갱신이 실제로 수행됩니다.</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-2">
          {(events?.available || []).map(ev => (
            <button key={ev.key} onClick={() => runEvent(ev.key)} disabled={!!running}
              className="text-left border border-slate-200 bg-white rounded-lg p-3 hover:border-amber-400 hover:shadow-sm disabled:opacity-50">
              <div className="text-sm font-medium text-slate-800">{ev.label}</div>
              <div className="text-[11px] text-slate-500 mt-1 line-clamp-2">{ev.description}</div>
            </button>
          ))}
        </div>
        {msg && <div className="mt-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg px-3 py-2 text-xs">{msg}</div>}
        {events?.history?.length > 0 && (
          <div className="mt-3 text-[11px] text-slate-400">
            최근 이벤트: {events.history.slice(0, 3).map(h => `${h.event_key}(${h.created_at.slice(0, 16).replace('T', ' ')})`).join(', ')}
          </div>
        )}
      </Card>

      <div className="flex gap-2">
        {[['risk', '위험 알림'], ['notif', '알림 전체']].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === k ? 'bg-brand-600 text-white' : 'bg-white border border-slate-200 text-slate-600'}`}>
            {l}{k === 'risk' && alerts ? ` (${alerts.items.filter(a => a.status === 'unread').length})` : ''}
          </button>
        ))}
      </div>

      <ErrorBox error={error} />
      {loading ? <Loading /> : tab === 'risk' ? (
        <div className="space-y-2">
          {alerts?.items?.length === 0 && <EmptyState title="알림이 없습니다" desc="정상 상태이거나 아직 분석이 실행되지 않았습니다." />}
          {alerts?.items?.map(a => (
            <Card key={a.id} className={`p-4 ${a.status === 'unread' ? 'border-l-4 border-l-rose-400' : ''}`}>
              <div className="flex items-start gap-3">
                <SeverityBadge severity={a.severity} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-sm text-slate-900">{a.title}</span>
                    <Badge tone="slate">{a.category}</Badge>
                    <Badge tone={a.status === 'unread' ? 'red' : 'slate'}>{STATUS_LABEL[a.status]}</Badge>
                  </div>
                  <div className="text-sm text-slate-600 mt-1">{a.message}</div>
                  <div className="text-[11px] text-slate-400 mt-1">{fmtDate(a.created_at)}</div>
                </div>
                <div className="flex gap-1 shrink-0">
                  {a.status === 'unread' && <button onClick={() => setAlertStatus(a.id, 'read')} className="text-xs border border-slate-300 rounded-lg px-2 py-1 hover:bg-slate-50">확인</button>}
                  {a.status !== 'acknowledged' && <button onClick={() => setAlertStatus(a.id, 'acknowledged')} className="text-xs border border-slate-300 rounded-lg px-2 py-1 hover:bg-slate-50">인지 완료</button>}
                </div>
              </div>
            </Card>
          ))}
          {alerts?.severity_rules && (
            <Card className="p-4">
              <SectionTitle>위험 등급 판단 기준</SectionTitle>
              <div className="grid md:grid-cols-2 gap-1 text-xs text-slate-500">
                {Object.entries(alerts.severity_rules).map(([k, v]) => <div key={k}>· {k}: {v}</div>)}
              </div>
            </Card>
          )}
        </div>
      ) : (
        <Card className="p-4">
          <div className="flex justify-between items-center mb-3">
            <span className="text-sm text-slate-500">읽지 않은 알림 {notifs?.unread ?? 0}건</span>
            <button onClick={readAll} className="text-xs text-brand-600 hover:underline">모두 읽음</button>
          </div>
          <div className="space-y-1.5">
            {notifs?.items?.length === 0 && <EmptyState title="알림이 없습니다" />}
            {notifs?.items?.map(n => (
              <div key={n.id} className={`flex items-start gap-2 p-2.5 rounded-lg ${n.is_read ? 'bg-slate-50' : 'bg-brand-50/60'}`}>
                <Badge tone={n.ntype === 'risk' ? 'red' : n.ntype === 'news' ? 'blue' : n.ntype === 'email' ? 'purple' : 'slate'}>
                  {NTYPE_LABEL[n.ntype] || n.ntype}
                </Badge>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-800">{n.title}</div>
                  <div className="text-xs text-slate-500 mt-0.5 whitespace-pre-line">{n.message}</div>
                  <div className="text-[11px] text-slate-400 mt-1">{fmtDate(n.created_at)}</div>
                </div>
                {!n.is_read && <button onClick={() => readNotif(n.id)} className="text-[11px] text-brand-600 hover:underline shrink-0">읽음</button>}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
