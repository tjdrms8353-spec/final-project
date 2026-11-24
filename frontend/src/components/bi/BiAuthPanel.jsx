import { useState } from 'react';
import { bi, biToken } from '../../services/biApi';
import { Alert, Button, Card, Field } from './ui';

const DEMO_ACCOUNTS = import.meta.env.VITE_DEMO_MODE === '1' ? [
  ['owner@demo.dayribbon.kr', '대표 (OWNER)'], ['approver@demo.dayribbon.kr', '재무팀장 (APPROVER)'],
  ['analyst@demo.dayribbon.kr', '경영기획 (ANALYST)'], ['viewer@demo.dayribbon.kr', '외부 감사 (VIEWER)'],
] : [];
const DEMO_PASSWORD = 'dayribbon-demo';

export default function BiAuthPanel({ onLogin }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ email: '', name: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(event, demoEmail) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const body = demoEmail ? { email: demoEmail, password: DEMO_PASSWORD }
        : mode === 'login' ? { email: form.email, password: form.password } : form;
      const data = await bi(`/auth/${demoEmail ? 'login' : mode}`, { method: 'POST', body });
      biToken.set(data.token);
      onLogin(data.user);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  return <div className="mx-auto max-w-md py-10">
    {DEMO_ACCOUNTS.length > 0 && <Card title="데모 계정으로 바로 체험" className="mb-4">
      <p className="mb-3 text-sm text-slate-600">반도체 제조 데모 기업(6개월 ERP 샘플, 실제 ECB 환율, 수집 뉴스)이 준비되어 있습니다. 권한별로 보이는 기능이 다릅니다.</p>
      <div className="grid grid-cols-2 gap-2">{DEMO_ACCOUNTS.map(([email, label]) =>
        <Button key={email} variant="secondary" disabled={busy} onClick={e => submit(e, email)}>{label}</Button>)}</div>
    </Card>}
    <Card title={mode === 'login' ? 'dayribbon 로그인' : 'dayribbon 회원가입'}>
      <form onSubmit={submit} className="space-y-3">
        <Field label="이메일" type="email" required value={form.email} onChange={set('email')} autoComplete="email" />
        {mode === 'register' && <Field label="이름" required value={form.name} onChange={set('name')} />}
        <Field label="비밀번호" type="password" required minLength={mode === 'register' ? 8 : 1} value={form.password}
          onChange={set('password')} hint={mode === 'register' ? '8자 이상' : undefined} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
        <Alert>{error}</Alert>
        <Button type="submit" disabled={busy} className="w-full">{mode === 'login' ? '로그인' : '가입하고 시작하기'}</Button>
      </form>
      <button type="button" className="mt-4 text-sm text-blue-700 hover:underline" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}>
        {mode === 'login' ? '계정이 없나요? 회원가입' : '이미 계정이 있나요? 로그인'}
      </button>
    </Card>
  </div>;
}
