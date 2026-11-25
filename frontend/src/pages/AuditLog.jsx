import React, { useEffect, useState } from 'react'
import { api, fmtDate } from '../api'
import { Badge, Card, EmptyState, ErrorBox, Loading, SectionTitle } from '../components/ui'

const ACTION_LABEL = {
  LOGIN: '로그인', LOGOUT: '로그아웃', COMPANY_UPDATE: '기업정보 수정', USER_UPDATE: '사용자 권한 변경',
  FINANCIAL_CREATE: '재무데이터 등록', FINANCIAL_UPDATE: '재무데이터 수정', FINANCIAL_DELETE: '재무데이터 삭제',
  DATA_UPLOAD: '파일 업로드', DATA_UPLOAD_FAIL: '업로드 실패', ANALYSIS_RUN: '분석 실행',
  ANALYSIS_REVIEW: '분석 검토', DECISION_CREATE: '의사결정 등록', DECISION_UPDATE: '의사결정 변경',
  FOLLOWUP_CREATE: '후속조치 등록', FOLLOWUP_UPDATE: '후속조치 변경', ALERT_UPDATE: '알림 처리',
  REPORT_GENERATE: '보고서 생성', REPORT_VIEW: '보고서 조회', SETTINGS_UPDATE: '알림설정 변경',
  DEMO_EVENT: '데모 이벤트', DEMO_SEED: '데모 데이터 생성',
}

export default function AuditLog() {
  const [data, setData] = useState(null)
  const [filters, setFilters] = useState({ action: '', user_name: '', days: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    const qs = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => { if (v) qs.set(k, v) })
    api(`/api/audit-logs?limit=200&${qs}`)
      .then(setData).catch(e => setError(e.message)).finally(() => setLoading(false))
  }
  useEffect(load, [filters])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-bold text-slate-900">감사 추적 로그</h1>
        <p className="text-xs text-slate-500">{data?.note || '모든 사용자 작업이 자동 기록되며 수정·삭제할 수 없습니다'}</p>
      </div>

      <Card className="p-3 flex flex-wrap gap-2 items-center">
        <input placeholder="작업 유형 검색 (예: UPLOAD)" value={filters.action}
          onChange={e => setFilters({ ...filters, action: e.target.value })}
          className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 w-52" />
        <input placeholder="사용자 이름" value={filters.user_name}
          onChange={e => setFilters({ ...filters, user_name: e.target.value })}
          className="text-sm border border-slate-300 rounded-lg px-3 py-1.5 w-36" />
        <select value={filters.days} onChange={e => setFilters({ ...filters, days: e.target.value })}
          className="text-sm border border-slate-300 rounded-lg px-2 py-1.5">
          <option value="">전체 기간</option>
          <option value="1">최근 24시간</option>
          <option value="7">최근 7일</option>
          <option value="30">최근 30일</option>
        </select>
        <span className="text-xs text-slate-400 ml-auto">총 {data?.total ?? 0}건</span>
      </Card>

      <ErrorBox error={error} />
      <Card className="overflow-hidden">
        {loading ? <Loading /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500">
                <tr>{['일시', '사용자', '권한', '작업', '대상', '내용'].map(h => <th key={h} className="px-3 py-2 text-left font-medium whitespace-nowrap">{h}</th>)}</tr>
              </thead>
              <tbody>
                {(data?.items || []).map(l => (
                  <tr key={l.id} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap">{fmtDate(l.created_at)}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{l.user_name}</td>
                    <td className="px-3 py-2"><Badge tone="slate">{l.user_role || '-'}</Badge></td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      <Badge tone={l.action.includes('DELETE') ? 'red' : l.action.includes('CREATE') || l.action.includes('UPLOAD') ? 'green' : 'blue'}>
                        {ACTION_LABEL[l.action] || l.action}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap">{l.target_type} {l.target_id}</td>
                    <td className="px-3 py-2 text-xs text-slate-600 max-w-[280px] truncate" title={l.detail}>{l.detail || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {data?.items?.length === 0 && <EmptyState title="로그가 없습니다" />}
          </div>
        )}
      </Card>
    </div>
  )
}
