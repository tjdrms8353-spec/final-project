import { useState } from 'react';
import { Check, Minus } from 'lucide-react';
import { bi } from '../../services/biApi';
import { Alert, Badge, Button, Card, Field, LABEL, PageHeader } from '../ui';
import { useWorkspace } from '../workspace';

const ROLES = ['OWNER', 'APPROVER', 'ANALYST', 'VIEWER'];
const MATRIX = [
  ['대시보드·분석 조회', [1, 1, 1, 1]], ['데이터 업로드·분석 실행', [1, 1, 1, 0]], ['후속조치 상태 변경', [1, 1, 1, 0]],
  ['승인·보류·반려 결정', [1, 1, 0, 0]], ['구성원 권한 관리', [1, 0, 0, 0]],
];

export default function MembersPage() {
  const { company, members, can, reload, user } = useWorkspace();
  const [form, setForm] = useState({ email: '', role: 'APPROVER' });
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  async function submit(e) {
    e.preventDefault(); setError(''); setOk('');
    try { const m = await bi(`/companies/${company.id}/members`, { method: 'PUT', body: form }); setOk(`${m.name}님을 ${LABEL[m.role]}(으)로 지정했습니다.`); setForm({ ...form, email: '' }); reload(); }
    catch (err) { setError(err.message); }
  }
  return <div className="space-y-6">
    <PageHeader title="구성원·권한" description="기업별로 권한이 분리됩니다. 다른 기업의 데이터는 볼 수 없습니다." />
    <div className="grid gap-6 xl:grid-cols-5">
      <Card title={`구성원 (${members.length})`} className="xl:col-span-3" bodyClassName="p-0">
        <ul className="divide-y divide-slate-100">{members.map(m => <li key={m.id} className="flex items-center gap-3 px-5 py-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-sm font-semibold text-slate-700">{m.name.slice(0, 1)}</span>
          <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium text-slate-900">{m.name}{m.id === user.id && <span className="ml-1.5 text-xs text-slate-400">(나)</span>}</span>
            <span className="block truncate text-xs text-slate-500">{m.email}</span></span>
          <Badge value={m.role} />
        </li>)}</ul>
        <div className="border-t border-slate-100 p-5">
          {can.admin ? <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
            <Field label="가입된 사용자 이메일" type="email" required className="min-w-56 flex-1" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} />
            <Field as="select" label="권한" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}>
              {ROLES.map(r => <option key={r} value={r}>{LABEL[r]}</option>)}</Field>
            <Button type="submit">추가·변경</Button>
          </form> : <Alert tone="info">구성원 관리는 대표(OWNER)만 할 수 있습니다.</Alert>}
          <div className="mt-3 space-y-2"><Alert>{error}</Alert><Alert tone="ok">{ok}</Alert></div>
        </div>
      </Card>
      <Card title="권한별 기능" className="xl:col-span-2" bodyClassName="p-0">
        <div className="overflow-x-auto"><table className="w-full text-sm">
          <thead><tr className="border-b border-slate-200 text-xs text-slate-500"><th className="px-4 py-2 text-left font-medium">기능</th>
            {ROLES.map(r => <th key={r} className={`px-2 py-2 font-medium ${r === company.role ? 'text-brand-700' : ''}`}>{LABEL[r].replace('대표·', '')}</th>)}</tr></thead>
          <tbody>{MATRIX.map(([label, flags]) => <tr key={label} className="border-b border-slate-100 last:border-0">
            <td className="px-4 py-2.5 text-slate-700">{label}</td>
            {flags.map((f, i) => <td key={i} className={`px-2 py-2.5 text-center ${ROLES[i] === company.role ? 'bg-brand-50' : ''}`}>
              {f ? <Check className="mx-auto h-4 w-4 text-emerald-600" aria-label="가능" /> : <Minus className="mx-auto h-4 w-4 text-slate-300" aria-label="불가" />}</td>)}
          </tr>)}</tbody></table></div>
        <p className="px-4 py-3 text-xs text-slate-500">현재 내 권한: <b>{LABEL[company.role]}</b> (파란 열)</p>
      </Card>
    </div>
  </div>;
}
