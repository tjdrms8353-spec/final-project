import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { api } from '../api'
import { ErrorBox } from '../components/ui'

const DEMO_ACCOUNTS = [
  { role: 'OWNER', email: 'owner@dayribbon.demo', desc: '기업 대표 — 전체 권한' },
  { role: 'ADMIN', email: 'admin@dayribbon.demo', desc: '경영관리자 — 분석 검토/결정 권한' },
  { role: 'MEMBER', email: 'member@dayribbon.demo', desc: '실무 담당자 — 데이터 등록/수정 권한' },
  { role: 'VIEWER', email: 'viewer@dayribbon.demo', desc: '외부 감사 — 읽기 전용' },
]

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [isDemo, setIsDemo] = useState(false)

  useEffect(() => {
    api('/api/health').then(h => setIsDemo(h.mode?.includes('demo'))).catch(() => {})
  }, [])

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true); setError('')
    try {
      await login(email, password)
      nav('/app/dashboard')
    } catch (err) {
      setError(err.message || '로그인에 실패했습니다.')
    } finally { setBusy(false) }
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl grid md:grid-cols-2 gap-6">
        {/* 소개 패널 */}
        <div className="bg-brand-950 text-white rounded-2xl p-8 flex flex-col justify-between">
          <div>
            <div className="text-2xl font-bold mb-2">dayribbon</div>
            <div className="text-brand-200 text-sm mb-6">AI 기반 중소기업형 맞춤형 BI · 데모</div>
            <ul className="space-y-3 text-sm text-brand-100">
              <li>✓ 내부 재무 데이터 + 외부 시장 데이터 자동 결합</li>
              <li>✓ 성장 가능성 · 사업 방향성 · 위험 요소 분석</li>
              <li>✓ 위험 자동 감지 및 알림</li>
              <li>✓ 시나리오 기반 영향 시뮬레이션</li>
              <li>✓ 월간 경영 보고서 · 감사 추적</li>
            </ul>
          </div>
          <div className="text-xs text-brand-300 mt-8">※ 데모 데이터는 모두 가상이며 규칙 기반 분석 결과입니다.</div>
        </div>

        {/* 로그인 폼 */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
          <h1 className="text-xl font-bold text-slate-900 mb-1">로그인</h1>
          <p className="text-sm text-slate-500 mb-6">{isDemo ? '데모 계정 (비밀번호 공통: demo1234)' : '계정으로 로그인하세요'}</p>
          <ErrorBox error={error} />
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-xs font-medium text-slate-600">이메일</label>
              <input value={email} onChange={e => setEmail(e.target.value)} required
                className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600">비밀번호</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
                className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500" />
            </div>
            <button disabled={busy}
              className="w-full bg-brand-600 text-white rounded-lg py-2.5 text-sm font-semibold hover:bg-brand-700 disabled:opacity-50">
              {busy ? '로그인 중…' : '로그인'}
            </button>
          </form>
          {isDemo && (
            <div className="mt-6">
              <div className="text-xs font-medium text-slate-500 mb-2">권한별 데모 계정</div>
              <div className="space-y-1.5">
                {DEMO_ACCOUNTS.map(a => (
                  <button key={a.email} type="button"
                    onClick={() => { setEmail(a.email); setPassword('demo1234') }}
                    className="w-full text-left border border-slate-200 rounded-lg px-3 py-2 hover:border-brand-400 hover:bg-brand-50/50 transition-colors">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-slate-800">{a.role} · {a.email}</span>
                      <span className="text-[11px] text-slate-400">{a.desc}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
          <div className="mt-6 text-center text-xs text-slate-400 space-x-3">
            <span>계정이 없으신가요? <Link to="/signup" className="text-brand-600 hover:underline">회원가입</Link></span>
            <Link to="/" className="hover:text-brand-600">← 서비스 소개</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
