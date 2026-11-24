import { useEffect, useState } from 'react';
import { Download, ShieldCheck } from 'lucide-react';
import { bi } from '../../services/biApi';
import { Alert, Button, Card, cx, dateTimeKo, Empty, LABEL, Loading, PageHeader } from '../ui';
import { useWorkspace } from '../workspace';

const PAGE = 25;
export const AUDIT_ACTIONS = {
  COMPANY_CREATED: ['기업 등록', 'bg-brand-50 text-brand-700'],
  MEMBER_UPDATED: ['권한 변경', 'bg-violet-50 text-violet-700'],
  ERP_UPLOAD: ['데이터 업로드', 'bg-sky-50 text-sky-700'],
  ANALYSIS_RUN: ['AI 분석 실행', 'bg-indigo-50 text-indigo-700'],
  DECISION: ['관리자 결정', 'bg-emerald-50 text-emerald-700'],
  ACTION_UPDATE: ['후속조치 변경', 'bg-amber-50 text-amber-800'],
  SIMULATION_RUN: ['시뮬레이션', 'bg-slate-100 text-slate-700'],
  REPORT_GENERATED: ['보고서 생성', 'bg-slate-100 text-slate-700'],
};

const pct = (v) => `${v > 0 ? '+' : ''}${v}%`;
export function describe(item) {
  const d = item.detail || {};
  switch (item.action) {
    case 'COMPANY_CREATED': return `${d.name} (${d.industry})`;
    case 'MEMBER_UPDATED': return `${d.name} <${d.email}> → ${LABEL[d.role] || d.role}`;
    case 'ERP_UPLOAD': return `${d.file_name} · ${d.accepted}행 저장${d.rejected ? `, ${d.rejected}행 제외` : ''}`;
    case 'ANALYSIS_RUN': return `${d.period} 분석 · 결과 ${d.findings}건 · ${d.narrative_source === 'llm' ? 'LLM 요약' : '템플릿 요약'}`;
    case 'DECISION': return `분석 항목 #${item.entity_id} ${LABEL[d.status] || d.status} — 사유: ${d.reason}${d.follow_up ? ` · 후속조치: ${d.follow_up}` : ''}`;
    case 'ACTION_UPDATE': return `${d.title}: ${LABEL[d.from] || d.from} → ${LABEL[d.to] || d.to}`;
    case 'SIMULATION_RUN': return `환율 ${pct(d.fx_pct)}, 원자재 ${pct(d.purchase_price_pct)}, 판매단가 ${pct(d.sales_pct)}, 판매량 ${pct(d.volume_pct)}`;
    case 'REPORT_GENERATED': return `${d.kind === 'weekly' ? '주간' : '월간'} 보고서 · ${d.period}`;
    default: return JSON.stringify(d);
  }
}

function toCsv(items) {
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const rows = [['id', 'time', 'user', 'action', 'description'], ...items.map(i => [i.id, dateTimeKo(i.created_at), i.user, AUDIT_ACTIONS[i.action]?.[0] || i.action, describe(i)])];
  return '\ufeff' + rows.map(r => r.map(esc).join(',')).join('\r\n');
}

export default function AuditPage() {
  const { company, version } = useWorkspace();
  const [action, setAction] = useState('');
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    setError('');
    const q = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
    if (action) q.set('action', action);
    bi(`/companies/${company.id}/audit-logs?${q}`).then(d => alive && setData(d)).catch(e => alive && setError(e.message));
    return () => { alive = false; };
  }, [company.id, action, offset, version]);

  async function exportCsv() {
    const q = new URLSearchParams({ limit: '200', offset: '0' });
    if (action) q.set('action', action);
    try {
      const all = await bi(`/companies/${company.id}/audit-logs?${q}`);
      const url = URL.createObjectURL(new Blob([toCsv(all.items)], { type: 'text/csv;charset=utf-8' }));
      const a = Object.assign(document.createElement('a'), { href: url, download: `dayribbon_audit_${company.id}.csv` });
      a.click(); URL.revokeObjectURL(url);
    } catch (e) { setError(e.message); }
  }

  const filter = (v) => { setAction(v); setOffset(0); };
  return <div className="space-y-5">
    <PageHeader title="감사 추적 로그" description="누가 언제 무엇을 했는지 모든 업로드·분석·결정·권한 변경·보고서 생성을 자동 기록합니다. 기록은 수정·삭제할 수 없습니다."
      actions={<Button variant="secondary" icon={Download} onClick={exportCsv} disabled={!data?.total}>CSV 내보내기</Button>} />
    <div role="group" aria-label="작업 종류 필터" className="flex flex-wrap gap-1.5">
      {[['', '전체'], ...Object.entries(AUDIT_ACTIONS).map(([k, [l]]) => [k, l])].map(([k, l]) =>
        <button key={k || 'all'} type="button" aria-pressed={action === k} onClick={() => filter(k)}
          className={cx('rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset', action === k ? 'bg-slate-900 text-white ring-slate-900' : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-50')}>{l}</button>)}
    </div>
    <Alert>{error}</Alert>
    <Card bodyClassName="p-0">
      {!data ? <div className="px-5"><Loading /></div> : data.items.length ? <>
        <ol className="divide-y divide-slate-100">{data.items.map(i => {
          const [label, tone] = AUDIT_ACTIONS[i.action] || [i.action, 'bg-slate-100 text-slate-700'];
          return <li key={i.id} className="grid gap-1 px-5 py-3 sm:grid-cols-[150px_120px_110px_minmax(0,1fr)] sm:items-start sm:gap-3">
            <time className="text-xs tabular-nums text-slate-500" dateTime={i.created_at}>{dateTimeKo(i.created_at)}</time>
            <span className="text-sm font-medium text-slate-900">{i.user || '-'}</span>
            <span><span className={cx('inline-flex rounded-md px-1.5 py-0.5 text-xs font-medium', tone)}>{label}</span></span>
            <span className="min-w-0 break-words text-sm text-slate-700">{describe(i)}</span>
          </li>;
        })}</ol>
        <div className="flex items-center justify-between border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
          <span className="tabular-nums">총 {data.total}건 중 {offset + 1}–{Math.min(offset + PAGE, data.total)}</span>
          <span className="flex gap-2"><Button size="sm" variant="secondary" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - PAGE))}>이전</Button>
            <Button size="sm" variant="secondary" disabled={offset + PAGE >= data.total} onClick={() => setOffset(offset + PAGE)}>다음</Button></span>
        </div>
      </> : <div className="p-5"><Empty icon={ShieldCheck} title="기록이 없습니다" description="이 기능 도입 이후의 작업부터 기록됩니다." /></div>}
    </Card>
  </div>;
}
