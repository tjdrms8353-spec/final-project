import { useState } from 'react';
import { bi, biToken } from '../../services/biApi';
import { Alert, Button, Card, Field } from './ui';

export default function BiAuthPanel({ onLogin }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ email: '', name: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const data = await bi(`/auth/${mode}`, { method: 'POST', body: mode === 'login' ? { email: form.email, password: form.password } : form });
      biToken.set(data.token);
      onLogin(data.user);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }

  return <div className="mx-auto max-w-md py-10">
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
