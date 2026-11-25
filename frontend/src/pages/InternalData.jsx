import React, { useEffect, useRef, useState } from 'react'
import { api, fmtWon } from '../api'
import { useAuth } from '../auth'
import { Badge, Card, EmptyState, ErrorBox, Loading, SectionTitle } from '../components/ui'

const KINDS = [
  { key: 'financial_monthly', label: '월별 재무', desc: 'month, revenue, operating_profit, raw_material_cost, labor_cost, other_cost, export_amount, import_amount, fx_avg_rate' },
  { key: 'product_monthly', label: '제품별 실적', desc: 'month, product_name, revenue, cost' },
  { key: 'customer_monthly', label: '거래처별 실적', desc: 'month, customer_name, country, revenue' },
  { key: 'material_purchase', label: '원자재 구매', desc: 'month, material_name, amount_krw' },
]

const REC_KINDS = [
  { key: 'product_monthly', label: '제품별 실적',
    fields: [{ k: 'month', label: '월', type: 'month' }, { k: 'product_name', label: '제품명', type: 'text' },
             { k: 'revenue', label: '매출(원)', type: 'number' }, { k: 'cost', label: '원가(원)', type: 'number' }],
    cols: [['month', '월'], ['product_name', '제품명'], ['revenue', '매출'], ['cost', '원가'], ['margin', '수익률']] },
  { key: 'customer_monthly', label: '거래처별 실적',
    fields: [{ k: 'month', label: '월', type: 'month' }, { k: 'customer_name', label: '거래처명', type: 'text' },
             { k: 'country', label: '국가', type: 'text' }, { k: 'revenue', label: '매출(원)', type: 'number' }],
    cols: [['month', '월'], ['customer_name', '거래처명'], ['country', '국가'], ['revenue', '매출']] },
  { key: 'material_purchase', label: '원자재 구매',
    fields: [{ k: 'month', label: '월', type: 'month' }, { k: 'material_name', label: '원자재명', type: 'text' },
             { k: 'amount_krw', label: '금액(원)', type: 'number' }, { k: 'currency', label: '통화', type: 'text' }],
    cols: [['month', '월'], ['material_name', '원자재명'], ['amount_krw', '금액'], ['currency', '통화']] },
]

const EMPTY_FORM = { month: '', revenue: '', operating_profit: '', raw_material_cost: '',
  labor_cost: '', other_cost: '', export_amount: '', import_amount: '', fx_avg_rate: '' }

export default function InternalData() {
  const { user } = useAuth()
  const canWrite = ['OWNER', 'ADMIN', 'MEMBER'].includes(user?.role)
  const [tab, setTab] = useState('monthly')
  const [rows, setRows] = useState([])
  const [uploads, setUploads] = useState([])
  const [form, setForm] = useState(EMPTY_FORM)
  const [editing, setEditing] = useState(null)
  const [kind, setKind] = useState('financial_monthly')
  const [file, setFile] = useState(null)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [recKind, setRecKind] = useState('product_monthly')
  const [recRows, setRecRows] = useState([])
  const [recForm, setRecForm] = useState({})
  const fileRef = useRef()

  const load = () => {
    setLoading(true)
    Promise.all([
      api('/api/financial/monthly?months=36'),
      api('/api/financial/uploads'),
    ]).then(([m, u]) => { setRows(m); setUploads(u) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const num = v => (v === '' ? 0 : Number(v))

  const saveRow = async (e) => {
    e.preventDefault()
    setError(''); setMsg('')
    try {
      const body = { month: form.month }
      ;['revenue','operating_profit','raw_material_cost','labor_cost','other_cost','export_amount','import_amount','fx_avg_rate']
        .forEach(k => body[k] = num(form[k]))
      const res = await api('/api/financial/monthly', { method: 'POST', body })
      setMsg(`저장 완료: ${form.month} (자동 분석 실행 — 알림 ${res.pipeline?.new_alerts ?? 0}건, 분석 ${res.pipeline?.new_analyses ?? 0}건 생성)`)
      setForm(EMPTY_FORM); setEditing(null)
      load()
    } catch (err) { setError(err.message) }
  }

  const delRow = async (month) => {
    if (!confirm(`${month} 데이터를 삭제할까요?`)) return
    try { await api(`/api/financial/monthly/${month}`, { method: 'DELETE' }); load() }
    catch (e) { setError(e.message) }
  }

  const editRow = (r) => {
    setEditing(r.month)
    const f = { ...EMPTY_FORM }
    Object.keys(f).forEach(k => f[k] = r[k] ?? '')
    setForm(f)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const doPreview = async (e) => {
    e.preventDefault()
    if (!file) { setError('파일을 선택하세요.'); return }
    setError(''); setMsg(''); setResult(null)
    const fd = new FormData()
    fd.append('file', file)
    fd.append('data_kind', kind)
    try {
      const res = await api('/api/financial/upload/preview', { method: 'POST', formData: fd })
      setPreview(res)
    } catch (err) { setPreview(null); setError(err.message) }
  }

  const doUpload = async (e) => {
    e.preventDefault()
    if (!file) { setError('파일을 선택하세요.'); return }
    setError(''); setMsg(''); setResult(null)
    const fd = new FormData()
    fd.append('file', file)
    fd.append('data_kind', kind)
    try {
      const res = await api('/api/financial/upload', { method: 'POST', formData: fd })
      setResult(res)
      setMsg(`업로드 완료: ${res.row_count}행 처리 (신규 ${res.inserted}, 갱신 ${res.updated})`)
      setFile(null); setPreview(null)
      if (fileRef.current) fileRef.current.value = ''
      load()
    } catch (err) { setError(err.message) }
  }

  const loadRecords = (k = recKind) => {
    api(`/api/financial/records/${k}`).then(setRecRows).catch(e => setError(e.message))
  }
  useEffect(() => { if (tab === 'records') loadRecords() }, [tab, recKind])

  const saveRecord = async (e) => {
    e.preventDefault()
    setError(''); setMsg('')
    try {
      await api(`/api/financial/records/${recKind}`, { method: 'POST', body: recForm })
      setMsg('저장되었습니다. (같은 월·명칭 데이터는 덮어씁니다)')
      setRecForm({})
      loadRecords()
    } catch (err) { setError(err.message) }
  }

  const delRecord = async (id) => {
    if (!confirm('이 데이터를 삭제할까요?')) return
    try { await api(`/api/financial/records/${recKind}/${id}`, { method: 'DELETE' }); loadRecords() }
    catch (e) { setError(e.message) }
  }

  const downloadTemplate = async () => {
    const blob = await api('/api/financial/template')
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'template.xlsx'; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-bold text-slate-900">내부 데이터 관리</h1>
        <p className="text-xs text-slate-500">월별 재무·제품·거래처·원자재 데이터를 등록하면 대시보드와 분석에 자동 반영됩니다</p>
      </div>

      <div className="flex gap-2 border-b border-slate-200">
        {[['monthly', '월별 재무 데이터'], ['records', '제품·거래처·원자재'], ['upload', '파일 업로드'], ['history', '업로드 이력']].map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${tab === k ? 'border-brand-600 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
            {l}
          </button>
        ))}
      </div>

      <ErrorBox error={error} />
      {msg && <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-lg px-4 py-2.5 text-sm">{msg}</div>}
      {result?.warnings?.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 text-amber-700 rounded-lg px-4 py-2.5 text-sm">
          업로드 경고: {result.warnings.join(' / ')}
        </div>
      )}

      {tab === 'monthly' && (
        <>
          {canWrite && (
            <Card className="p-4">
              <SectionTitle>{editing ? `${editing} 수정` : '월별 재무 직접 입력'}</SectionTitle>
              <form onSubmit={saveRow} className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <label className="text-xs text-slate-500">월 (YYYY-MM)
                  <input required pattern="\d{4}-\d{2}" value={form.month} onChange={e => setForm({ ...form, month: e.target.value })}
                    className="mt-1 w-full border border-slate-300 rounded-lg px-2 py-1.5 text-sm" placeholder="2026-10" /></label>
                {['revenue', 'operating_profit', 'raw_material_cost', 'labor_cost', 'other_cost', 'export_amount', 'import_amount', 'fx_avg_rate'].map(k => (
                  <label key={k} className="text-xs text-slate-500">{{ revenue: '매출', operating_profit: '영업이익', raw_material_cost: '원자재비', labor_cost: '인건비', other_cost: '기타비용', export_amount: '수출액', import_amount: '수입액', fx_avg_rate: '평균환율' }[k]} (원)
                    <input type="number" step="any" value={form[k]} onChange={e => setForm({ ...form, [k]: e.target.value })}
                      className="mt-1 w-full border border-slate-300 rounded-lg px-2 py-1.5 text-sm" /></label>
                ))}
                <div className="col-span-2 md:col-span-4 flex gap-2">
                  <button className="bg-brand-600 text-white text-sm rounded-lg px-4 py-2 hover:bg-brand-700">{editing ? '수정 저장' : '등록'}</button>
                  {editing && <button type="button" onClick={() => { setEditing(null); setForm(EMPTY_FORM) }}
                    className="border border-slate-300 text-sm rounded-lg px-4 py-2">취소</button>}
                </div>
              </form>
            </Card>
          )}
          <Card className="overflow-hidden">
            {loading ? <Loading /> : rows.length === 0 ? <EmptyState title="등록된 데이터 없음" /> : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs text-slate-500">
                    <tr>
                      {['월', '매출', '영업이익', '영업이익률', '원자재비', '인건비', '수출액', '수입액', '환율', ...(canWrite ? ['관리'] : [])].map(h => (
                        <th key={h} className="px-3 py-2 text-left font-medium whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(r => (
                      <tr key={r.id} className="border-t border-slate-100 hover:bg-slate-50">
                        <td className="px-3 py-2 font-medium whitespace-nowrap">{r.month}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{fmtWon(r.revenue)}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{fmtWon(r.operating_profit)}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{r.revenue ? (r.operating_profit / r.revenue * 100).toFixed(1) + '%' : '-'}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{fmtWon(r.raw_material_cost)}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{fmtWon(r.labor_cost)}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{fmtWon(r.export_amount)}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{fmtWon(r.import_amount)}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{r.fx_avg_rate}</td>
                        {canWrite && (
                          <td className="px-3 py-2 whitespace-nowrap">
                            <button onClick={() => editRow(r)} className="text-brand-600 text-xs hover:underline mr-2">수정</button>
                            <button onClick={() => delRow(r.month)} className="text-rose-500 text-xs hover:underline">삭제</button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}

      {tab === 'upload' && (
        <div className="grid lg:grid-cols-2 gap-4">
          <Card className="p-5">
            <SectionTitle>Excel / CSV 업로드</SectionTitle>
            {!canWrite && <div className="text-sm text-amber-600 bg-amber-50 rounded-lg p-3 mb-3">읽기 전용 권한으로는 업로드할 수 없습니다.</div>}
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-600">데이터 종류</label>
                <select value={kind} onChange={e => setKind(e.target.value)} disabled={!canWrite}
                  className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                  {KINDS.map(k => <option key={k.key} value={k.key}>{k.label}</option>)}
                </select>
                <div className="text-[11px] text-slate-400 mt-1">
                  {KINDS.find(k => k.key === kind)?.desc}
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-slate-600">파일 (.xlsx / .csv)</label>
                <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" disabled={!canWrite}
                  onChange={e => { setFile(e.target.files?.[0] || null); setPreview(null) }}
                  className="mt-1 w-full text-sm border border-slate-300 rounded-lg px-3 py-2 file:mr-3 file:border-0 file:bg-brand-50 file:text-brand-700 file:rounded file:px-2 file:py-1" />
              </div>
              <div className="flex gap-2">
                <button onClick={doPreview} disabled={!canWrite || !file}
                  className="border border-brand-600 text-brand-700 text-sm rounded-lg px-4 py-2 hover:bg-brand-50 disabled:opacity-50">
                  1. 미리보기
                </button>
                <button onClick={doUpload} disabled={!canWrite || !file}
                  className="bg-brand-600 text-white text-sm rounded-lg px-4 py-2 hover:bg-brand-700 disabled:opacity-50">
                  2. 업로드 확정
                </button>
                <button onClick={downloadTemplate}
                  className="border border-slate-300 text-sm rounded-lg px-4 py-2 hover:bg-slate-50">
                  양식 다운로드 (Excel)
                </button>
              </div>
              {preview && (
                <div className="border border-slate-200 rounded-lg p-3">
                  <div className="text-xs font-semibold text-slate-700 mb-2">
                    미리보기 — {preview.row_count}행 ({preview.note})
                  </div>
                  {preview.warnings.length > 0 && (
                    <div className="text-[11px] text-amber-600 bg-amber-50 rounded p-2 mb-2">
                      {preview.warnings.join(' / ')}
                    </div>
                  )}
                  <div className="overflow-x-auto max-h-56 overflow-y-auto">
                    <table className="w-full text-[11px]">
                      <thead className="bg-slate-50 text-slate-500 sticky top-0">
                        <tr>{preview.columns.map(c => <th key={c} className="px-2 py-1 text-left font-medium whitespace-nowrap">{c}</th>)}</tr>
                      </thead>
                      <tbody>
                        {preview.preview.map((r, i) => (
                          <tr key={i} className="border-t border-slate-100">
                            {preview.columns.map(c => <td key={c} className="px-2 py-1 whitespace-nowrap">{r[c]}</td>)}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
              <div className="text-[11px] text-slate-400 leading-relaxed">
                업로드 시 컬럼 매핑·결측치·중복·month 형식을 자동 검증하고, 같은 월 데이터는 덮어씁니다.
                업로드 완료 후 자동 분석 파이프라인이 실행되어 위험 알림이 갱신됩니다.
              </div>
            </div>
          </Card>
          <Card className="p-5">
            <SectionTitle>검증 규칙 안내</SectionTitle>
            <ul className="text-xs text-slate-600 space-y-2 list-disc pl-4">
              <li>month 컬럼은 반드시 YYYY-MM 형식이어야 합니다.</li>
              <li>월별 재무는 revenue·operating_profit이 필수입니다.</li>
              <li>한글 컬럼명(매출, 영업이익, 원자재비 등)도 자동 변환됩니다.</li>
              <li>결측치가 있으면 경고가 표시되고, 중복 행은 자동 제거됩니다.</li>
              <li>PDF 재무제표 OCR은 데모 범위에서 지원하지 않습니다.</li>
            </ul>
            {result && (
              <div className="mt-4 bg-slate-50 rounded-lg p-3 text-xs text-slate-600">
                <div className="font-semibold mb-1">처리 결과</div>
                <div>행 수: {result.row_count} · 신규 {result.inserted} · 갱신 {result.updated}</div>
                {result.pipeline && (
                  <div className="mt-1">자동 분석: 알림 {result.pipeline.new_alerts}건 · 분석 {result.pipeline.new_analyses}건 생성</div>
                )}
              </div>
            )}
          </Card>
        </div>
      )}

      {tab === 'records' && (
        <>
          <div className="flex gap-2">
            {REC_KINDS.map(k => (
              <button key={k.key} onClick={() => { setRecKind(k.key); setRecForm({}) }}
                className={`px-3 py-1.5 text-xs rounded-full border ${recKind === k.key ? 'bg-brand-600 text-white border-brand-600' : 'border-slate-300 text-slate-600 hover:bg-slate-50'}`}>
                {k.label}
              </button>
            ))}
          </div>
          {canWrite && (
            <Card className="p-4">
              <SectionTitle>{REC_KINDS.find(k => k.key === recKind)?.label} 직접 입력</SectionTitle>
              <form onSubmit={saveRecord} className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {REC_KINDS.find(k => k.key === recKind).fields.map(f => (
                  <label key={f.k} className="text-xs text-slate-500">{f.label}
                    <input required={f.k !== 'country' && f.k !== 'currency'}
                      type={f.type === 'number' ? 'number' : 'text'} step="any"
                      placeholder={f.k === 'month' ? '2026-10' : ''}
                      value={recForm[f.k] ?? ''}
                      onChange={e => setRecForm({ ...recForm, [f.k]: f.type === 'number' ? (e.target.value === '' ? '' : Number(e.target.value)) : e.target.value })}
                      className="mt-1 w-full border border-slate-300 rounded-lg px-2 py-1.5 text-sm" /></label>
                ))}
                <div className="col-span-2 md:col-span-4">
                  <button className="bg-brand-600 text-white text-sm rounded-lg px-4 py-2 hover:bg-brand-700">등록/수정</button>
                </div>
              </form>
            </Card>
          )}
          <Card className="overflow-hidden">
            {recRows.length === 0 ? <EmptyState title="등록된 데이터 없음" /> : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-xs text-slate-500">
                    <tr>
                      {REC_KINDS.find(k => k.key === recKind).cols.map(([, l]) => (
                        <th key={l} className="px-3 py-2 text-left font-medium whitespace-nowrap">{l}</th>
                      ))}
                      {canWrite && <th className="px-3 py-2 text-left font-medium">관리</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {recRows.map(r => (
                      <tr key={r.id} className="border-t border-slate-100 hover:bg-slate-50">
                        {REC_KINDS.find(k => k.key === recKind).cols.map(([c]) => (
                          <td key={c} className="px-3 py-2 whitespace-nowrap">
                            {c === 'margin'
                              ? (r.revenue ? ((r.revenue - r.cost) / r.revenue * 100).toFixed(1) + '%' : '-')
                              : typeof r[c] === 'number' && c !== 'month' ? fmtWon(r[c]) : r[c]}
                          </td>
                        ))}
                        {canWrite && (
                          <td className="px-3 py-2">
                            <button onClick={() => delRecord(r.id)} className="text-rose-500 text-xs hover:underline">삭제</button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}

      {tab === 'history' && (
        <Card className="overflow-hidden">
          {uploads.length === 0 ? <EmptyState title="업로드 이력이 없습니다" /> : (
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-xs text-slate-500">
                <tr>{['파일명', '종류', '형식', '상태', '행 수', '경고', '업로드자', '일시'].map(h => <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>)}</tr>
              </thead>
              <tbody>
                {uploads.map(u => (
                  <tr key={u.id} className="border-t border-slate-100">
                    <td className="px-3 py-2">{u.filename}</td>
                    <td className="px-3 py-2"><Badge tone="blue">{u.data_kind_label}</Badge></td>
                    <td className="px-3 py-2 uppercase">{u.file_type}</td>
                    <td className="px-3 py-2"><Badge tone={u.status === '완료' ? 'green' : u.status === '오류' ? 'red' : 'amber'}>{u.status}</Badge></td>
                    <td className="px-3 py-2">{u.row_count}</td>
                    <td className="px-3 py-2 text-xs text-amber-600 max-w-[200px] truncate" title={u.warnings}>{u.warnings || '-'}</td>
                    <td className="px-3 py-2">{u.uploaded_by}</td>
                    <td className="px-3 py-2 text-xs text-slate-500">{u.created_at.slice(0, 16).replace('T', ' ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}
    </div>
  )
}
