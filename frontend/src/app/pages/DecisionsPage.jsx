import { useState } from 'react';
import { ClipboardList, History } from 'lucide-react';
import { bi } from '../../services/biApi';
import { Alert, Badge, Card, cx, dateTimeKo, Empty, Loading, PageHeader } from '../ui';
import { useWorkspace } from '../workspace';

const COLUMNS = [['OPEN', '대기'], ['IN_PROGRESS', '진행 중'], ['DONE', '완료']];

export default function DecisionsPage() {
  const { company, decisions, actions, can, reload, dashboard } = useWorkspace();
  const [error, setError] = useState('');
  if (!dashboard) return <Loading />;
  async function move(a, status) {
    setError('');
    try { await bi(`/companies/${company.id}/actions/${a.id}`, { method: 'PATCH', body: { status } }); reload(); }
    catch (e) { setError(e.message); }
  }
  const count = (s) => decisions.filter(d => d.status === s).length;
  return <div className="space-y-6">
    <PageHeader title="결정·후속조치" description="관리자 결정과 사유, 담당자, 후속조치 진행 상황을 기록합니다." />
    <section aria-label="결정 요약" className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {[['전체 결정', decisions.length, 'text-slate-900'], ['승인', count('APPROVED'), 'text-emerald-700'], ['보류', count('ON_HOLD'), 'text-slate-700'], ['반려', count('REJECTED'), 'text-red-700']].map(([l, v, c]) =>
        <div key={l} className="rounded-xl border border-slate-200 bg-white p-4"><p className="text-xs font-medium text-slate-500">{l}</p><p className={cx('mt-1 text-2xl font-bold tabular-nums', c)}>{v}</p></div>)}
    </section>
    <Alert>{error}</Alert>
    <Card title={`후속조치 (${actions.length})`} subtitle={can.write ? '상태를 바꾸면 바로 저장됩니다.' : '조회자는 상태를 바꿀 수 없습니다.'}>
      {actions.length ? <div className="grid gap-4 md:grid-cols-3">{COLUMNS.map(([status, label]) => {
        const items = actions.filter(a => a.status === status);
        return <div key={status} className="rounded-lg bg-slate-50 p-3">
          <h3 className="mb-2 flex items-center justify-between text-xs font-semibold text-slate-600">{label}<span className="tabular-nums">{items.length}</span></h3>
          <ul className="space-y-2">{items.map(a => <li key={a.id} className="rounded-lg border border-slate-200 bg-white p-3">
            <p className="text-sm font-medium text-slate-900">{a.title}</p>
            <p className="mt-1 text-xs text-slate-500">담당 {a.assignee || '미지정'} · 기한 {a.due_date || '-'}</p>
            <select aria-label={`${a.title} 상태`} value={a.status} disabled={!can.write} onChange={e => move(a, e.target.value)}
              className="mt-2 w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-xs disabled:bg-slate-50">
              {COLUMNS.map(([s, l]) => <option key={s} value={s}>{l}</option>)}</select>
          </li>)}{!items.length && <li className="py-4 text-center text-xs text-slate-400">없음</li>}</ul>
        </div>;
      })}</div> : <Empty icon={ClipboardList} title="등록된 후속조치가 없습니다" description="분석 항목에 승인·보류 결정을 남기면 후속조치가 만들어집니다." />}
    </Card>
    <Card title={`의사결정 이력 (${decisions.length})`}>
      {decisions.length ? <ol className="relative space-y-5 border-l border-slate-200 pl-5">{decisions.map(d => <li key={d.id}>
        <span className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full bg-brand-600" aria-hidden="true" />
        <div className="flex flex-wrap items-center gap-2"><Badge value={d.status} /><a href={`#/analysis?f=${d.finding_id}`} className="text-sm font-semibold text-slate-900 hover:text-brand-700">{d.finding_title}</a></div>
        <p className="mt-1 text-sm text-slate-700">사유: {d.reason}</p>
        <p className="mt-0.5 text-xs text-slate-500">결정자 {d.decided_by} · 담당자 {d.assignee || '-'} · {dateTimeKo(d.decided_at)}</p>
      </li>)}</ol> : <Empty icon={History} title="아직 결정 기록이 없습니다" />}
    </Card>
  </div>;
}
