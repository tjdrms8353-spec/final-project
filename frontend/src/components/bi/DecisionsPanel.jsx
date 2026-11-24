import { useEffect, useState } from 'react';
import { bi } from '../../services/biApi';
import { Alert, Badge, Card } from './ui';

export default function DecisionsPanel({ company, version }) {
  const [decisions, setDecisions] = useState([]);
  const [actions, setActions] = useState([]);
  const [error, setError] = useState('');
  const load = () => Promise.all([bi(`/companies/${company.id}/decisions`), bi(`/companies/${company.id}/actions`)])
    .then(([d, a]) => { setDecisions(d); setActions(a); }).catch(e => setError(e.message));
  useEffect(() => { load(); }, [company.id, version]);
  async function update(action, status) {
    setError('');
    try { await bi(`/companies/${company.id}/actions/${action.id}`, { method: 'PATCH', body: { status } }); load(); }
    catch (e) { setError(e.message); }
  }
  return <div className="space-y-4">
    <Alert>{error}</Alert>
    <Card title={`후속 조치 (${actions.length})`}>
      {actions.length ? <table className="w-full text-left text-sm"><thead className="text-xs text-slate-500">
        <tr><th className="py-1">조치</th><th>담당자</th><th>기한</th><th>상태</th></tr></thead>
        <tbody>{actions.map(a => <tr key={a.id} className="border-t border-slate-100">
          <td className="py-2 pr-2">{a.title}</td><td>{a.assignee || '-'}</td><td className="tabular-nums">{a.due_date || '-'}</td>
          <td><select aria-label={`${a.title} 상태`} value={a.status} disabled={company.role === 'VIEWER'} onChange={e => update(a, e.target.value)}
            className="rounded border border-slate-300 px-1 py-0.5 text-xs">
            <option value="OPEN">대기</option><option value="IN_PROGRESS">진행 중</option><option value="DONE">완료</option></select></td>
        </tr>)}</tbody></table> : <p className="text-sm text-slate-500">등록된 후속 조치가 없습니다.</p>}
    </Card>
    <Card title={`의사결정 이력 (${decisions.length})`}>
      {decisions.length ? <ul className="space-y-3">{decisions.map(d => <li key={d.id} className="border-b border-slate-100 pb-3 text-sm last:border-0">
        <div className="flex flex-wrap items-center gap-2"><Badge value={d.status} /><b>{d.finding_title}</b></div>
        <p className="mt-1 text-slate-700">사유: {d.reason}</p>
        <p className="text-xs text-slate-500">결정자 {d.decided_by} · 담당자 {d.assignee || '-'} · {new Date(d.decided_at).toLocaleString('ko-KR')}</p>
      </li>)}</ul> : <p className="text-sm text-slate-500">아직 결정 기록이 없습니다.</p>}
    </Card>
  </div>;
}
