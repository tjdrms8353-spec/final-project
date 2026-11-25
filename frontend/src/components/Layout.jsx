import React, { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { api, fmtDate } from '../api'
import { Badge, ErrorBoundary } from './ui'

const NAV = [
  { to: 'dashboard', label: '경영 대시보드', icon: '📊' },
  { to: 'news', label: '뉴스 · 산업 동향', icon: '📰' },
  { to: 'finance', label: '금융 · 경제 지표', icon: '📈' },
  { to: 'data', label: '내부 데이터 관리', icon: '🗄️' },
  { to: 'kpi', label: '경영 KPI 분석', icon: '🎯' },
  { to: 'analysis', label: 'AI 경영 분석', icon: '🤖' },
  { to: 'simulation', label: '위험 시뮬레이션', icon: '🎛️' },
  { to: 'alerts', label: '알림 센터', icon: '🔔' },
  { to: 'decisions', label: '의사결정 · 후속 조치', icon: '✅' },
  { to: 'reports', label: '월간 경영 보고서', icon: '📄' },
  { to: 'settings', label: '기업 설정', icon: '⚙️' },
  { to: 'audit', label: '감사 추적 로그', icon: '🧾' },
]

const ROLE_LABEL = { OWNER: '대표/최고관리자', ADMIN: '관리자', MEMBER: '실무 담당자', VIEWER: '읽기 전용(감사)' }

export default function Layout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const [unread, setUnread] = useState(0)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let alive = true
    const load = () => api('/api/notifications')
      .then(d => alive && setUnread(d.unread))
      .catch(() => {})
    load()
    const t = setInterval(load, 30000)
    return () => { alive = false; clearInterval(t) }
  }, [])

  const isViewer = user?.role === 'VIEWER'

  return (
    <div className="h-screen flex bg-slate-100">
      {/* 사이드바 */}
      <aside className={`fixed md:static inset-y-0 left-0 z-40 w-60 bg-brand-950 text-white flex flex-col transform transition-transform md:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="px-5 py-5 border-b border-white/10">
          <div className="text-xl font-bold tracking-tight">dayribbon</div>
          <div className="text-[11px] text-brand-200 mt-0.5">AI 맞춤형 경영 분석 · 데모</div>
        </div>
        <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-0.5">
          {NAV.map(n => (
            <NavLink key={n.to} to={n.to} onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? 'bg-white/15 text-white font-medium' : 'text-brand-200 hover:bg-white/10 hover:text-white'
                }`}>
              <span className="w-5 text-center">{n.icon}</span>
              <span className="flex-1">{n.label}</span>
              {n.to === 'alerts' && unread > 0 && (
                <span className="bg-rose-500 text-white text-[10px] font-bold rounded-full px-1.5 py-0.5">{unread}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-white/10 text-[11px] text-brand-300">
          규칙 기반 데모 분석 · 실제 금융 데이터 아님
        </div>
      </aside>
      {open && <div className="fixed inset-0 bg-black/30 z-30 md:hidden" onClick={() => setOpen(false)} />}

      {/* 메인 */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-white border-b border-slate-200 flex items-center px-4 gap-3">
          <button className="md:hidden text-slate-500" onClick={() => setOpen(true)}>☰</button>
          <div className="flex-1" />
          {isViewer && <Badge tone="amber">읽기 전용 권한</Badge>}
          <div className="text-sm text-slate-600 hidden sm:block">
            {user?.company_name} · {user?.name} <span className="text-slate-400">({ROLE_LABEL[user?.role]})</span>
          </div>
          <button onClick={logout}
            className="text-sm text-slate-500 hover:text-rose-600 border border-slate-200 rounded-lg px-3 py-1.5">
            로그아웃
          </button>
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
