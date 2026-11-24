import { useState } from 'react';
import { bi } from '../../services/biApi';
import { Alert, Button, Card, Field } from './ui';

const ROLES = { OWNER: '소유자 (전체 권한)', APPROVER: '승인권자 (결정 가능)', ANALYST: '분석가 (업로드·분석)', VIEWER: '조회자 (읽기 전용)' };

export default function MembersPanel({ company, members, onChanged }) {
  const [form, setForm] = useState({ email: '', role: 'APPROVER' });
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  async function submit(event) {
    event.preventDefault();
    setError(''); setOk('');
    try { const m = await bi(`/companies/${company.id}/members`, { method: 'PUT', body: form }); setOk(`${m.name} 님을 ${m.role}(으)로 지정했습니다.`); onChanged(); }
    catch (e) { setError(e.message); }
  }
  return <Card title="구성원 및 권한">
    <ul className="mb-4 divide-y divide-slate-100 text-sm">{members.map(m => <li key={m.id} className="flex justify-between py-2">
      <span>{m.name} <span className="text-xs text-slate-500">{m.email}</span></span><span className="text-xs">{ROLES[m.role]}</span></li>)}</ul>
    {company.role === 'OWNER' ? <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
      <div className="min-w-60 flex-1"><Field label="가입된 사용자 이메일" type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></div>
      <select aria-label="역할" value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} className="rounded-lg border border-slate-300 px-2 py-2 text-sm">
        {Object.entries(ROLES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
      <Button type="submit">추가·변경</Button>
    </form> : <p className="text-xs text-slate-500">구성원 관리는 OWNER만 가능합니다.</p>}
    <div className="mt-3 space-y-2"><Alert>{error}</Alert><Alert tone="ok">{ok}</Alert></div>
  </Card>;
}
