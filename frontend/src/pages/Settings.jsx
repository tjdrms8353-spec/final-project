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
  const [invites, setInvites] = useState([])
  const [myCompanies, setMyCompanies] = useState([])
  const [collect, setCollect] = useState(null)
  const [invEmail, setInvEmail] = useState('')
  const [invRole, setInvRole] = useState('MEMBER')
  const [invToken, setInvToken] = useState('')
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    Promise.all([
      api('/api/company'), api('/api/users'), api('/api/notification-settings'),
      api('/api/invites'), api('/api/companies/mine'), api('/api/collection/status'),
    ]).then(([c, u, n, i, m, col]) => {
      setCompany(c); setUsers(u); setNs(n); setInvites(i); setMyCompanies(m); setCollect(col)
    }).catch(e => setError(e.message)).finally(() => setLoading(false))
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

  const deactivateUser = async (uid, name) => {
    if (!confirm(`${name} 사용자의 접근을 해제할까요?`)) return
    try { await api(`/api/users/${uid}`, { method: 'DELETE' }); load() }
    catch (e) { setError(e.message) }
  }

  const sendInvite = async (e) => {
    e.preventDefault(); setError(''); setMsg(''); setInvToken('')
    try {
      const res = await api('/api/invites', { method: 'POST', body: { email: invEmail, role: invRole } })
      setInvToken(res.invite_token)
      setMsg(`초대 생성: ${invEmail} (${invRole}) — 토큰을 수락 대상에게 전달하세요.`)
      setInvEmail('')
      load()
    } catch (err) { setError(err.message) }
  }

  const cancelInvite = async (id) => {
    try { await api(`/api/invites/${id}/cancel`, { method: 'POST' }); load() }
    catch (e) { setError(e.message) }
  }

  const switchCompany = async (company_id) => {
    try {
      await api('/api/companies/select', { method: 'POST', body: { company_id } })
      window.location.reload()
    } catch (e) { setError(e.message) }
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
        {[['company', '기업 정보'], ['users', '사용자 · 권한'], ['notify', '알림 설정'], ['collect', '데이터 수집']].map(([k, l]) => (
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
            {/* 외부 AI(LLM) 분석 전송 옵트인 — 미승인 시 기업 데이터를 외부 LLM에 보내지 않음 */}
            <label className="md:col-span-2 flex items-start gap-3 border border-slate-200 rounded-lg p-3 text-xs text-slate-600">
              <input type="checkbox" disabled={!canWrite}
                checked={!!company.allow_external_ai}
                onChange={e => setCompany({ ...company, allow_external_ai: e.target.checked })}
                className="mt-0.5 w-4 h-4 accent-brand-600" />
              <span>
                <b className="text-slate-800">외부 AI 분석 사용 허용</b><br />
                체크하면 검증된 KPI·프로필 데이터를 외부 LLM 서비스에 전송해 AI 분석을 받습니다.
                미체크 시 규칙 기반 엔진만 사용되며 기업 데이터가 외부로 전송되지 않습니다.
              </span>
            </label>
            {canWrite && <div className="md:col-span-2"><button className="bg-brand-600 text-white text-sm rounded-lg px-5 py-2.5 hover:bg-brand-700">저장</button></div>}
            {!canWrite && <div className="md:col-span-2 text-xs text-amber-600">읽기 전용 권한으로는 수정할 수 없습니다.</div>}
          </form>
        </Card>
      )}

      {tab === 'users' && (
        <div className="space-y-4">
          {myCompanies.length > 1 && (
            <Card className="p-4">
              <SectionTitle>워크스페이스 전환</SectionTitle>
              <div className="flex flex-wrap gap-2">
                {myCompanies.map(c => (
                  <button key={c.company_id} onClick={() => !c.active && switchCompany(c.company_id)}
                    disabled={c.active}
                    className={`px-3 py-1.5 text-xs rounded-lg border ${c.active ? 'bg-brand-600 text-white border-brand-600' : 'border-slate-300 text-slate-600 hover:bg-slate-50'}`}>
                    {c.name} ({c.role}){c.active ? ' · 현재' : ''}
                  </button>
                ))}
              </div>
            </Card>
          )}

          <Card className="overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500">
                <tr>{['이름', '이메일', '권한', '역할 설명', ...(isAdmin ? ['관리'] : [])].map(h => <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>)}</tr>
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
                    {isAdmin && (
                      <td className="px-4 py-2.5 whitespace-nowrap">
                        {u.id !== user.id && (
                          <>
                            <select value={u.role} onChange={e => changeRole(u.id, e.target.value)}
                              className="border border-slate-300 rounded px-2 py-1 text-xs mr-2">
                              {['OWNER', 'ADMIN', 'MEMBER', 'VIEWER'].map(r => <option key={r}>{r}</option>)}
                            </select>
                            <button onClick={() => deactivateUser(u.id, u.name)}
                              className="text-rose-500 text-xs hover:underline">접근 해제</button>
                          </>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            {!isAdmin && <div className="px-4 py-3 text-xs text-slate-400">권한 변경·초대는 ADMIN/OWNER만 가능합니다.</div>}
          </Card>

          {isAdmin && (
            <Card className="p-5">
              <SectionTitle>사용자 초대</SectionTitle>
              <form onSubmit={sendInvite} className="flex flex-wrap gap-2 items-end">
                <label className="text-xs text-slate-500 flex-1 min-w-40">이메일
                  <input type="email" required value={invEmail} onChange={e => setInvEmail(e.target.value)}
                    className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" /></label>
                <label className="text-xs text-slate-500">권한
                  <select value={invRole} onChange={e => setInvRole(e.target.value)}
                    className="mt-1 border border-slate-300 rounded-lg px-3 py-2 text-sm">
                    {['ADMIN', 'MEMBER', 'VIEWER'].map(r => <option key={r}>{r}</option>)}
                  </select></label>
                <button className="bg-brand-600 text-white text-sm rounded-lg px-4 py-2 hover:bg-brand-700">초대 생성</button>
              </form>
              {invToken && (
                <div className="mt-3 bg-slate-50 border border-slate-200 rounded-lg p-3">
                  <div className="text-xs text-slate-500 mb-1">초대 토큰 (수락 대상에게 전달 — 이메일 발송 모듈 미연동):</div>
                  <code className="text-xs break-all select-all">{invToken}</code>
                </div>
              )}
              {invites.length > 0 && (
                <table className="w-full text-sm mt-4">
                  <thead className="bg-slate-50 text-xs text-slate-500">
                    <tr>{['이메일', '권한', '상태', '초대자', '만료', ...(isAdmin ? ['관리'] : [])].map(h => <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>)}</tr>
                  </thead>
                  <tbody>
                    {invites.map(i => (
                      <tr key={i.id} className="border-t border-slate-100">
                        <td className="px-3 py-2">{i.email}</td>
                        <td className="px-3 py-2">{i.role}</td>
                        <td className="px-3 py-2"><Badge tone={i.status === 'pending' ? 'blue' : i.status === 'accepted' ? 'green' : 'amber'}>{i.status}</Badge></td>
                        <td className="px-3 py-2">{i.invited_by}</td>
                        <td className="px-3 py-2 text-xs text-slate-500">{i.expires_at.slice(0, 10)}</td>
                        {isAdmin && (
                          <td className="px-3 py-2">
                            {i.status === 'pending' && (
                              <button onClick={() => cancelInvite(i.id)} className="text-rose-500 text-xs hover:underline">취소</button>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          )}
        </div>
      )}

      {tab === 'collect' && collect && (
        <div className="space-y-4">
          <Card className="p-5">
            <SectionTitle>외부 데이터 수집기</SectionTitle>
            <p className="text-xs text-slate-500 mb-3">
              환율·금리·뉴스를 외부 공개 소스에서 주기적으로 수집해 기업 데이터와 분리된 출처로 저장합니다.
              수집된 데이터는 분석·대시보드의 시장 지표로 반영됩니다.
            </p>
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500">
                <tr>{['수집기', '출처', '상태'].map(h => <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>)}</tr>
              </thead>
              <tbody>
                {collect.collectors.map(c => (
                  <tr key={c.name} className="border-t border-slate-100">
                    <td className="px-4 py-2.5 font-medium">{c.name}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-500">{c.source}</td>
                    <td className="px-4 py-2.5 space-x-1">
                      <Badge tone={c.enabled ? 'green' : 'amber'}>{c.enabled ? '활성' : '비활성'}</Badge>
                      {c.configured && !c.license_verified && (
                        <Badge tone="rose">이용 조건 미검증</Badge>
                      )}
                      {!c.configured && !c.enabled && (
                        <Badge tone="slate">API 키/설정 대기</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <Card className="p-5">
            <SectionTitle>수집 현황</SectionTitle>
            <div className="text-sm text-slate-600 space-y-1">
              <div>마지막 수집: {collect.last_run?.at ? collect.last_run.at.replace('T', ' ').slice(0, 19) : '아직 없음'}</div>
              {collect.company_data && (
                <div>수집 데이터: 시장 지표 {collect.company_data.market_series}건 · 실수집 뉴스 {collect.company_data.news_real}건</div>
              )}
              {collect.last_run?.summary?.map(s => (
                <div key={s.name} className="text-xs text-slate-500">
                  · {s.name}: 시계열 {s.series}건 / 뉴스 {s.news}건{s.errors.length ? ` — ${s.errors.join(' / ')}` : ''}
                </div>
              ))}
            </div>
            {isAdmin && (
              <button onClick={async () => {
                try { const r = await api('/api/collection/run', { method: 'POST' }); setMsg('수집 실행 완료'); setCollect({ ...collect, last_run: { at: r.ran_at, summary: r.collectors } }) }
                catch (e) { setError(e.message) }
              }} className="mt-4 bg-brand-600 text-white text-sm rounded-lg px-5 py-2.5 hover:bg-brand-700">지금 수집 실행</button>
            )}
            {!isAdmin && <div className="mt-3 text-xs text-slate-400">수동 수집 실행은 ADMIN/OWNER만 가능합니다.</div>}
          </Card>
        </div>
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
            <label className="block py-2">
              <span className="text-xs text-slate-500">카카오 수신 전화번호</span>
              <input value={ns.kakao_phone || ''} disabled={!canWrite} placeholder="01012345678"
                onChange={e => setNs({ ...ns, kakao_phone: e.target.value })}
                className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm disabled:bg-slate-50" />
            </label>
            <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">{ns.note}</div>
            {canWrite && <button onClick={saveNs} className="mt-4 bg-brand-600 text-white text-sm rounded-lg px-5 py-2.5 hover:bg-brand-700">저장</button>}
          </Card>
        </div>
      )}
    </div>
  )
}
