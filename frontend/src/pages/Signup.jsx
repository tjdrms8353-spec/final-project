import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { ErrorBox } from '../components/ui'

export default function Signup() {
  const { signup } = useAuth()
  const nav = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [password2, setPassword2] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (password !== password2) { setError('비밀번호가 서로 다릅니다.'); return }
    setBusy(true)
    try {
      await signup(email, password, name)
      nav('/onboarding')
    } catch (err) {
      setError(err.message || '회원가입에 실패했습니다.')
    } finally { setBusy(false) }
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
        <div className="text-2xl font-bold text-brand-950 mb-1">dayribbon</div>
        <h1 className="text-lg font-bold text-slate-900 mb-1">회원가입</h1>
        <p className="text-sm text-slate-500 mb-6">가입 후 기업을 등록하면 BI 서비스를 바로 이용할 수 있습니다.</p>
        <ErrorBox error={error} />
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-600">이름</label>
            <input value={name} onChange={e => setName(e.target.value)} required
              className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600">이메일</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
              className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600">비밀번호 (8자 이상)</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              required minLength={8}
              className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm" />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600">비밀번호 확인</label>
            <input type="password" value={password2} onChange={e => setPassword2(e.target.value)}
              required minLength={8}
              className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2.5 text-sm" />
          </div>
          <button disabled={busy}
            className="w-full bg-brand-600 text-white rounded-lg py-2.5 text-sm font-semibold hover:bg-brand-700 disabled:opacity-50">
            {busy ? '가입 중…' : '가입하기'}
          </button>
        </form>
        <div className="mt-6 text-center text-xs text-slate-400">
          이미 계정이 있으신가요? <Link to="/login" className="text-brand-600 hover:underline">로그인</Link>
        </div>
      </div>
    </div>
  )
}
