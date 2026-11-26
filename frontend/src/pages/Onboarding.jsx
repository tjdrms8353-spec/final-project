import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { ErrorBox } from '../components/ui'

const FIELDS = [
  ['name', '기업명 *', 'text'],
  ['business_type', '사업자 유형', 'select'],
  ['industry', '업종', 'text'],
  ['size', '기업 규모 (예: 중소기업 · 직원 50명)', 'text'],
  ['products', '주요 생산 제품', 'text'],
  ['export_countries', '주요 수출 국가', 'text'],
  ['import_countries', '주요 수입 국가', 'text'],
  ['raw_materials', '주요 원자재', 'text'],
  ['export_import_ratio', '수출입 비중 (예: 수출 60% / 수입 40%)', 'text'],
  ['interest_areas', '관심 산업 분야', 'text'],
  ['risk_concerns', '관심 위험 요소', 'text'],
]

export default function Onboarding() {
  const { user, logout, refreshUser } = useAuth()
  const nav = useNavigate()
  const [form, setForm] = useState({})
  const [inviteToken, setInviteToken] = useState('')
  const [companies, setCompanies] = useState([])
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (user && !user.company_id) {
      api('/api/companies/mine').then(setCompanies).catch(() => {})
    }
  }, [user])

  if (!user) { nav('/login'); return null }
  if (user.company_id) { nav('/app/dashboard'); return null }

  const registerCompany = async (e) => {
    e.preventDefault()
    setError(''); setBusy(true)
    try {
      await api('/api/companies', { method: 'POST', body: form })
      await refreshUser()
      nav('/app/dashboard')
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  const acceptInvite = async (e) => {
    e.preventDefault()
    setError(''); setBusy(true)
    try {
      await api('/api/invites/accept', { method: 'POST', body: { token: inviteToken } })
      await refreshUser()
      nav('/app/dashboard')
    } catch (err) { setError(err.message) }
    finally { setBusy(false) }
  }

  const selectCompany = async (company_id) => {
    setError('')
    try {
      await api('/api/companies/select', { method: 'POST', body: { company_id } })
      await refreshUser()
      nav('/app/dashboard')
    } catch (err) { setError(err.message) }
  }

  return (
    <div className="min-h-screen bg-slate-100 py-10 px-4">
      <div className="max-w-2xl mx-auto space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-2xl font-bold text-brand-950">dayribbon</div>
            <h1 className="text-lg font-bold text-slate-900 mt-1">시작하기</h1>
            <p className="text-sm text-slate-500">{user.name}님, 기업 워크스페이스를 등록하거나 초대를 수락하세요.</p>
          </div>
          <button onClick={logout} className="text-sm text-slate-500 hover:text-rose-600 border border-slate-200 rounded-lg px-3 py-1.5 bg-white">
            로그아웃
          </button>
        </div>

        <ErrorBox error={error} />
        {msg && <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg px-4 py-2 text-sm">{msg}</div>}

        {companies.length > 0 && (
          <div className="bg-white rounded-2xl p-6 border border-slate-200">
            <h2 className="text-sm font-bold text-slate-800 mb-3">소속 기업으로 계속하기</h2>
            <div className="space-y-2">
              {companies.map(c => (
                <button key={c.company_id} onClick={() => selectCompany(c.company_id)}
                  className="w-full text-left border border-slate-200 rounded-lg px-4 py-3 hover:border-brand-400 hover:bg-brand-50/50">
                  <span className="font-medium text-slate-800">{c.name}</span>
                  <span className="ml-2 text-xs text-slate-400">{c.role}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="bg-white rounded-2xl p-6 border border-slate-200">
          <h2 className="text-sm font-bold text-slate-800 mb-1">초대 수락</h2>
          <p className="text-xs text-slate-400 mb-3">기업 관리자에게 받은 초대 토큰을 입력하세요.</p>
          <form onSubmit={acceptInvite} className="flex gap-2">
            <input value={inviteToken} onChange={e => setInviteToken(e.target.value)} required
              placeholder="초대 토큰"
              className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm" />
            <button disabled={busy} className="bg-slate-700 text-white text-sm rounded-lg px-4 py-2 hover:bg-slate-800 disabled:opacity-50">수락</button>
          </form>
        </div>

        <div className="bg-white rounded-2xl p-6 border border-slate-200">
          <h2 className="text-sm font-bold text-slate-800 mb-1">새 기업 등록</h2>
          <p className="text-xs text-slate-400 mb-4">기업명만 필수입니다. 나머지는 설정에서 언제든 입력할 수 있습니다.</p>
          <form onSubmit={registerCompany} className="grid md:grid-cols-2 gap-3">
            {FIELDS.map(([k, label, type]) => (
              <label key={k} className={`text-xs text-slate-500 ${k === 'name' ? 'md:col-span-2' : ''}`}>
                {label}
                {type === 'select' ? (
                  <select value={form[k] || 'corporation'}
                    onChange={e => setForm({ ...form, [k]: e.target.value })}
                    className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white">
                    <option value="corporation">법인사업자</option>
                    <option value="sole_proprietor">개인사업자</option>
                  </select>
                ) : (
                  <input required={k === 'name'} value={form[k] || ''}
                    onChange={e => setForm({ ...form, [k]: e.target.value })}
                    className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                )}
              </label>
            ))}
            <div className="md:col-span-2">
              <button disabled={busy}
                className="bg-brand-600 text-white text-sm rounded-lg px-5 py-2.5 hover:bg-brand-700 disabled:opacity-50">
                {busy ? '등록 중…' : '기업 등록하고 시작하기 (OWNER 권한 부여)'}
              </button>
            </div>
          </form>
        </div>

        <div className="text-[11px] text-slate-400 text-center">
          신규 기업은 데이터가 없는 상태로 시작합니다. 등록 후 내부 데이터 관리에서 재무 데이터를 업로드하면 분석이 시작됩니다.
        </div>
      </div>
    </div>
  )
}
