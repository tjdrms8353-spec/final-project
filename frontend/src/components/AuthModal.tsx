import React, { useState } from 'react';
import { LogOut, ShieldCheck, X } from 'lucide-react';
import { usePlatform } from '../context/PlatformContext';

export const AuthModal: React.FC = () => {
  const {
    authModalOpen,
    setAuthModalOpen,
    currentUser,
    effectiveRole,
    loginWithEmail,
    loginWithOAuth,
    registerAccount,
    logout,
  } = usePlatform();

  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('seojun.kim@datapulse.kr');
  const [password, setPassword] = useState('demo1234');
  const [name, setName] = useState('');
  const [department, setDepartment] = useState('데이터 전략팀');

  if (!authModalOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'login') {
      if (!email.trim()) return;
      loginWithEmail(email, password);
    } else {
      if (!name.trim() || !email.trim()) return;
      registerAccount(name, email, department);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
    >
      <div className="w-full max-w-md bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
          <h2 id="auth-modal-title" className="font-display text-base font-semibold text-slate-900">
            {currentUser ? '계정 세션 및 권한 정보' : 'dayribbon 인증 (데모)'}
          </h2>
          <button
            type="button"
            onClick={() => setAuthModalOpen(false)}
            aria-label="닫기"
            className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {currentUser ? (
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-900">{currentUser.name}</span>
                  <span className="text-xs font-mono font-medium text-blue-700">
                    {effectiveRole}
                  </span>
                </div>
                <p className="text-xs text-slate-600">{currentUser.email}</p>
                <p className="text-xs text-slate-500">
                  {currentUser.department} · 인증방식 {currentUser.provider}
                </p>
              </div>

              <div className="space-y-2 text-xs text-slate-600">
                <div className="flex items-center gap-2 font-medium text-slate-800">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>현재 역할 기반 허용 범위</span>
                </div>
                <ul className="space-y-1 pl-6 list-disc">
                  <li>뉴스·SNS 실시간 트렌드 및 금융 시세 조회</li>
                  <li>AI 문서 업로드·분류 및 영수증 OCR 전표 등록 (ANALYST+)</li>
                  <li>Airflow DAG 파이프라인 및 Playwright RPA 실행 (DATAOPS+)</li>
                  <li>Pandera 오류 주입 테스트 및 RBAC 회원 관리 (ADMIN)</li>
                </ul>
              </div>

              <button
                type="button"
                onClick={() => {
                  logout();
                  setAuthModalOpen(false);
                }}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 border border-red-200 rounded-lg transition-colors cursor-pointer"
              >
                <LogOut className="w-4 h-4" />
                <span>로그아웃 (Guest 비회원 전환 테스트)</span>
              </button>
            </div>
          ) : null}

          <div className="border-t border-slate-200 pt-4 space-y-4">
            <div className="grid grid-cols-2 gap-1 p-1 bg-slate-100 rounded-lg">
              <button
                type="button"
                onClick={() => setMode('login')}
                className={`py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                  mode === 'login' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                }`}
              >
                이메일 로그인
              </button>
              <button
                type="button"
                onClick={() => setMode('signup')}
                className={`py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                  mode === 'signup' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
                }`}
              >
                신규 회원가입
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-3">
              {mode === 'signup' && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">이름</label>
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="홍길동"
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">소속 부서</label>
                    <input
                      type="text"
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      placeholder="데이터 분석팀"
                      className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                    />
                  </div>
                </>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">이메일</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@datapulse.kr"
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">비밀번호</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2.5 px-4 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors cursor-pointer"
              >
                {mode === 'login' ? '이메일로 로그인' : '회원가입 및 즉시 시작'}
              </button>
            </form>

            <div className="space-y-2">
              <p className="text-center text-xs text-slate-500">또는 소셜 OAuth 2.0 원클릭 인증</p>
              <div className="grid grid-cols-2 gap-2.5">
                <button
                  type="button"
                  onClick={() => loginWithOAuth('KAKAO')}
                  className="py-2.5 px-3 text-xs font-semibold text-slate-900 bg-[#FEE500] hover:bg-[#F5DC00] rounded-lg transition-colors cursor-pointer whitespace-nowrap"
                >
                  카카오 로그인
                </button>
                <button
                  type="button"
                  onClick={() => loginWithOAuth('GOOGLE')}
                  className="py-2.5 px-3 text-xs font-semibold text-slate-800 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg transition-colors cursor-pointer whitespace-nowrap"
                >
                  Google 로그인
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
