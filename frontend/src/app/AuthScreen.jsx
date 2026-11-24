import { useState } from 'react';
import { BarChart3, FileSearch, Gavel, ShieldCheck } from 'lucide-react';
import { bi, biToken } from '../services/biApi';
import { Logo } from './Logo';
import { Alert, Button, Field } from './ui';

const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === '1';
const DEMO_PASSWORD = 'dayribbon-demo';
const DEMO_ACCOUNTS = [
  { email: 'owner@demo.dayribbon.kr', role: '대표 (OWNER)', name: '김대표', can: '모든 기능 · 구성원 권한 관리' },
  { email: 'approver@demo.dayribbon.kr', role: '재무팀장 (APPROVER)', name: '이재무', can: '분석 검토 · 승인/보류/반려 결정' },
  { email: 'analyst@demo.dayribbon.kr', role: '경영기획 (ANALYST)', name: '박분석', can: '데이터 업로드 · 분석 실행 (결정 불가)' },
  { email: 'viewer@demo.dayribbon.kr', role: '외부 감사 (VIEWER)', name: '최조회', can: '조회 전용' },
];
const FLOW = ['기업 등록', '데이터 수집·업로드', '맞춤형 BI 대시보드', 'AI 기회·위험 분석', '근거 확인', '관리자 결정', '결과 기록'];
const FEATURES = [
  [BarChart3, '업종 맞춤 KPI', 'ERP·엑셀 장부만 올리면 업종별 핵심 지표가 자동 계산됩니다.'],
  [FileSearch, '근거 기반 AI 분석', '수치는 SQL·Python으로 계산하고, 모든 판단에 출처와 불확실성을 붙입니다.'],
  [Gavel, '의사결정 기록', '승인·보류·반려 사유와 후속조치 담당자·기한을 남깁니다.'],
  [ShieldCheck, '권한 분리', '대표·승인권자·분석가·조회자 권한을 기업별로 나눕니다.'],
];

export default function AuthScreen({ onLogin }) {
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ email: '', name: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function login(body, path, key) {
    setBusy(key); setError('');
    try {
      const data = await bi(`/auth/${path}`, { method: 'POST', body });
      biToken.set(data.token);
      window.location.hash = '/overview';
      onLogin(data.user);
    } catch (e) { setError(e.message); } finally { setBusy(''); }
  }
  const submit = (e) => {
    e.preventDefault();
    login(mode === 'login' ? { email: form.email, password: form.password } : form, mode, 'form');
  };

  return <div className="grid min-h-screen lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
    <aside className="hidden flex-col justify-between bg-brand-900 p-10 text-white lg:flex">
      <Logo light />
      <div className="max-w-md">
        <p className="text-sm font-medium text-brand-200">중소기업 맞춤형 AI BI 플랫폼</p>
        <h1 className="mt-3 text-3xl font-bold leading-snug">데이터에서 결정까지,<br />근거가 남는 경영 판단</h1>
        <ol className="mt-8 space-y-2.5">
          {FLOW.map((s, i) => <li key={s} className="flex items-center gap-3 text-sm text-brand-100">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold text-white tabular-nums">{i + 1}</span>{s}</li>)}
        </ol>
      </div>
      <ul className="grid grid-cols-2 gap-4">
        {FEATURES.map(([Icon, title, desc]) => <li key={title} className="rounded-xl bg-white/5 p-4">
          <Icon className="h-5 w-5 text-brand-200" aria-hidden="true" />
          <p className="mt-2 text-sm font-semibold">{title}</p>
          <p className="mt-1 text-xs leading-relaxed text-brand-100/80">{desc}</p>
        </li>)}
      </ul>
    </aside>

    <main className="flex items-center justify-center px-5 py-10 sm:px-10">
      <div className="w-full max-w-lg">
        <Logo className="mb-8 lg:hidden" />
        {DEMO_MODE && <section aria-labelledby="demo-title" className="mb-8">
          <h2 id="demo-title" className="text-xl font-bold text-slate-900">데모 계정으로 바로 체험하기</h2>
          <p className="mt-1 text-sm text-slate-500">반도체 제조 데모 기업 ‘리본반도체’에 6개월 ERP 샘플, 실제 ECB 환율, 수집 뉴스가 준비되어 있습니다. 권한에 따라 할 수 있는 일이 다릅니다.</p>
          <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
            {DEMO_ACCOUNTS.map(a => <button key={a.email} type="button" disabled={Boolean(busy)}
              onClick={() => login({ email: a.email, password: DEMO_PASSWORD }, 'login', a.email)}
              className="group rounded-xl border border-slate-200 bg-white p-4 text-left transition hover:border-brand-500 hover:shadow-sm disabled:opacity-60">
              <span className="flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-900">{a.role}</span>
                <span className="text-xs text-brand-600 opacity-0 transition group-hover:opacity-100">{busy === a.email ? '접속 중...' : '입장 →'}</span>
              </span>
              <span className="mt-0.5 block text-xs text-slate-500">{a.name} · {a.can}</span>
            </button>)}
          </div>
          <div className="mt-8 flex items-center gap-3 text-xs text-slate-400"><span className="h-px flex-1 bg-slate-200" />또는 이메일 계정으로<span className="h-px flex-1 bg-slate-200" /></div>
        </section>}

        <section aria-labelledby="auth-title" className="rounded-xl border border-slate-200 bg-white p-6">
          <h2 id="auth-title" className="text-lg font-bold text-slate-900">{mode === 'login' ? '로그인' : '회원가입'}</h2>
          <form onSubmit={submit} className="mt-4 space-y-3">
            <Field label="이메일" type="email" required value={form.email} onChange={set('email')} autoComplete="email" />
            {mode === 'register' && <Field label="이름" required value={form.name} onChange={set('name')} autoComplete="name" />}
            <Field label="비밀번호" type="password" required minLength={mode === 'register' ? 8 : 1} value={form.password} onChange={set('password')}
              hint={mode === 'register' ? '8자 이상' : undefined} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
            <Alert>{error}</Alert>
            <Button type="submit" disabled={Boolean(busy)} className="w-full">{busy === 'form' ? '처리 중...' : mode === 'login' ? '로그인' : '가입하고 시작하기'}</Button>
          </form>
          <button type="button" className="mt-4 text-sm font-medium text-brand-700 hover:underline" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }}>
            {mode === 'login' ? '계정이 없나요? 회원가입' : '이미 계정이 있나요? 로그인'}
          </button>
        </section>
      </div>
    </main>
  </div>;
}
