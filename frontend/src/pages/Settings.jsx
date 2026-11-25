import React, { useEffect, useState } from 'react'
import { api, fmtWon } from '../api'
import { useAuth } from '../auth'
import { Badge, Card, ErrorBox, Loading, SectionTitle } from '../components/ui'

const FIELDS = [
  ['name', '기업명'], ['industry', '업종'], ['size', '기업 규모'],
  ['products', '주요 생산 제품 (쉼표 구분)'], ['key_customers', '주요 거래처'],
  ['export_countries', '수출 국가'], ['import_countries', '수입 국가'],
  ['raw_materials', '주요 원자재'], ['export_import_ratio', '수출입 비중'],
  ['annual_revenue', '연간 매출 (원)'], ['annual_raw_material_cost', '연간 원자재 구매 비용 (원)'],
  ['fx_settlement_ratio', '외화 결제 비중 (0~1)'],
  ['interest_areas', '주요 관심 산업'], ['risk_concerns', '관심 위험 요소'],
]
const TEXTAREA = new Set(['products', 'key_customers', 'export_countries', 'import_countries', 'raw_materials', 'interest_areas', 'risk_concerns'])

export default function Settings() {
  const { user } = useAuth()
  const canWrite = ['OWNER', 'ADMIN', 'MEMBER'].includes(user?.role)
  const isAdmin = ['OWNER', 'ADMIN'].includes(user?.role)
  const [tab, setTab] = useState('company')
  const [company, setCompany] = useState(null)
  const [users, setUsers] = useState([])
  const [ns, setNs] = useState(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    Promise.all([
      api('/api/company'), api('/api/users'), api('/api/notification-settings'),
    ]).then(([c, u, n]) => { setCompany(c); setUsers(u); setNs(n) })
      .catch(e => setError(e.message)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const saveCompany = async (e) => {
    e.preventDefault(); setError(''); setMsg('')
    try {
      const body = { ...company }
      ;['annual_revenue', 'annual_raw_material_cost', 'fx_settlement_ratio'].forEach(k => body[k] = Number(body[k]))
      await api('/api/company', { method: 'PUT', body })
      setMsg('기업 정보가 저장되었습니다. 이후 분석·뉴스 선별·위험 계산에 반영됩니다.')
      load()
    } catch (err) { setError(err.message) }
  }

  const changeRole = async (uid, role) => {
    try { await api(`/api/users/${uid}`, { method: 'PUT', body: { role } }); load() }
    catch (e) { setError(e.message) }
  }

  const saveNs = async () => {
    try { await api('/api/notification-settings', { method: 'PUT', body: ns }); setMsg('알림 설정이 저장되었습니다.') }
    catch (e) { setError(e.message) }
  }

  if (loading) return <Loading />

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-bold text-slate-900">기업 설정</h1>
        <p className="text-xs text-slate-500">기업 정보가 뉴스 선별·AI 분석·위험 계산의 기준이 됩니다</p>
      </div>
      <ErrorBox error={error} />
      {msg && <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg px-4 py-2 text-sm">{msg}</div>}

      <div className="flex gap-2">
        {[['company', '기업 정보'], ['users', '사용자 · 권한'], ['notify', '알림 설정']].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-2 rounded-lg text-sm font-medium ${tab === k ? 'bg-brand-600 text-white' : 'bg-white border border-slate-200 text-slate-600'}`}>
            {l}
          </button>
        ))}
      </div>

      {tab === 'company' && company && (
        <Card className="p-5">
          <form onSubmit={saveCompany} className="grid md:grid-cols-2 gap-4">
            {FIELDS.map(([k, label]) => (
              <label key={k} className={`text-xs text-slate-500 ${TEXTAREA.has(k) ? 'md:col-span-2' : ''}`}>
                {label}
                {TEXTAREA.has(k) ? (
                  <textarea rows={2} disabled={!canWrite} value={company[k] || ''}
                    onChange={e => setCompany({ ...company, [k]: e.target.value })}
                    className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm disabled:bg-slate-50" />
                ) : (
                  <input type={['annual_revenue', 'annual_raw_material_cost'].includes(k) ? 'number' : 'text'}
                    step="any" disabled={!canWrite} value={company[k] ?? ''}
                    onChange={e => setCompany({ ...company, [k]: e.target.value })}
                    className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm disabled:bg-slate-50" />
                )}
              </label>
            ))}
            {canWrite && <div className="md:col-span-2"><button className="bg-brand-600 text-white text-sm rounded-lg px-5 py-2.5 hover:bg-brand-700">저장</button></div>}
            {!canWrite && <div className="md:col-span-2 text-xs text-amber-600">읽기 전용 권한으로는 수정할 수 없습니다.</div>}
          </form>
        </Card>
      )}

      {tab === 'users' && (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500">
              <tr>{['이름', '이메일', '권한', '역할 설명', ...(isAdmin ? ['권한 변경'] : [])].map(h => <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>)}</tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} className="border-t border-slate-100">
                  <td className="px-4 py-2.5 font-medium">{u.name}</td>
                  <td className="px-4 py-2.5">{u.email}</td>
                  <td className="px-4 py-2.5"><Badge tone={u.role === 'OWNER' ? 'purple' : u.role === 'VIEWER' ? 'amber' : 'blue'}>{u.role}</Badge></td>
                  <td className="px-4 py-2.5 text-xs text-slate-500">
                    {{ OWNER: '기업 대표·최고관리자', ADMIN: '기업 관리자', MEMBER: '실무 담당자', VIEWER: '읽기 전용·외부 감사' }[u.role]}
                  </td>
                  {isAdmin && u.id !== user.id && (
                    <td className="px-4 py-2.5">
                      <select value={u.role} onChange={e => changeRole(u.id, e.target.value)}
                        className="border border-slate-300 rounded px-2 py-1 text-xs">
                        {['OWNER', 'ADMIN', 'MEMBER', 'VIEWER'].map(r => <option key={r}>{r}</option>)}
                      </select>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {!isAdmin && <div className="px-4 py-3 text-xs text-slate-400">권한 변경은 ADMIN/OWNER만 가능합니다. 각 계정으로 로그인해 권한 차이를 확인해 보세요.</div>}
        </Card>
      )}

      {tab === 'notify' && ns && (
        <div className="grid lg:grid-cols-2 gap-4">
          <Card className="p-5">
            <SectionTitle>알림 유형</SectionTitle>
            {[
              ['risk_alert', '위험 알림'], ['important_news', '중요 뉴스 알림'],
              ['kpi_change', '경영지표 변동 알림'], ['analysis_done', '분석 완료 알림'],
              ['weekly_summary', '주간 경영 요약'],
            ].map(([k, l]) => (
              <label key={k} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                <span className="text-sm text-slate-700">{l}</span>
                <input type="checkbox" checked={ns[k]} disabled={!canWrite}
                  onChange={e => setNs({ ...ns, [k]: e.target.checked })} className="w-4 h-4 accent-brand-600" />
              </label>
            ))}
          </Card>
          <Card className="p-5">
            <SectionTitle>발송 채널</SectionTitle>
            <label className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-sm text-slate-700">이메일 알림</span>
              <input type="checkbox" checked={ns.email_enabled} disabled={!canWrite}
                onChange={e => setNs({ ...ns, email_enabled: e.target.checked })} className="w-4 h-4 accent-brand-600" />
            </label>
            <label className="block py-2">
              <span className="text-xs text-slate-500">이메일 주소</span>
              <input value={ns.email_address} disabled={!canWrite}
                onChange={e => setNs({ ...ns, email_address: e.target.value })}
                className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm disabled:bg-slate-50" />
            </label>
            <label className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-sm text-slate-700">카카오 알림톡</span>
              <input type="checkbox" checked={ns.kakao_enabled} disabled={!canWrite}
                onChange={e => setNs({ ...ns, kakao_enabled: e.target.checked })} className="w-4 h-4 accent-brand-600" />
            </label>
            <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">{ns.note}</div>
            {canWrite && <button onClick={saveNs} className="mt-4 bg-brand-600 text-white text-sm rounded-lg px-5 py-2.5 hover:bg-brand-700">저장</button>}
          </Card>
        </div>
      )}
    </div>
  )
}
