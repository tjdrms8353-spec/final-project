import React, { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { usePlatform } from '../context/PlatformContext';
import { MARKET_REGIMES } from '../data/mockDb';
import { AppTab, MarketRegime, UserRole } from '../types/platform';
import { ResilientImage } from './ResilientImage';

const NAV_ITEMS: { id: AppTab; label: string }[] = [
  { id: 'dashboard', label: '대시보드' },
  { id: 'news-sns', label: '뉴스·SNS' },
  { id: 'doc-ai', label: 'AI 문서' },
  { id: 'finance', label: '금융 분석' },
  { id: 'receipt-ocr', label: '영수증 OCR' },
  { id: 'dataops', label: '운영 콘솔' },
];

const ROLE_OPTIONS: { role: UserRole; label: string }[] = [
  { role: 'GUEST', label: 'Guest' },
  { role: 'ANALYST', label: 'Analyst' },
  { role: 'DATAOPS', label: 'DataOps' },
  { role: 'ADMIN', label: 'Admin' },
];

const REGIME_OPTIONS: { id: MarketRegime; label: string }[] = [
  { id: 'BULL_MOMENTUM', label: '강세 · 거래확대' },
  { id: 'REGULATORY_ALERT', label: '규제 이슈 급증' },
  { id: 'MACRO_TIGHTENING', label: '금리 · 환율 경계' },
];

export const TopNavAndToolbar: React.FC = () => {
  const {
    activeTab,
    setActiveTab,
    currentUser,
    effectiveRole,
    setAuthModalOpen,
    switchRolePreview,
    marketRegime,
    setMarketRegime,
  } = usePlatform();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const regimeInfo = MARKET_REGIMES[marketRegime];

  return (
    <div className="sticky top-0 z-30 bg-white border-b border-slate-200">
      {/* Strict 3-Zone Top Bar Contract */}
      <header className="max-w-[1440px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-3">
        {/* Zone 1: Single text element wordmark */}
        <button
          type="button"
          onClick={() => setActiveTab('news-sns')}
          className="font-display text-lg font-bold tracking-tight text-slate-900 whitespace-nowrap shrink-0 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded"
        >
          DataPulse AI
        </button>

        {/* Workspace navigation */}
        <nav
          aria-label="주요 워크스페이스"
          className="hidden xl:flex items-center gap-6 text-sm font-medium"
        >
          {NAV_ITEMS.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveTab(item.id)}
                aria-current={isActive ? 'page' : undefined}
                className={`py-5 border-b-2 transition-colors whitespace-nowrap shrink-0 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 ${
                  isActive
                    ? 'border-blue-600 text-slate-900 font-semibold'
                    : 'border-transparent text-slate-600 hover:text-slate-900 hover:border-slate-300'
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Zone 3: 1 primary action */}
        <div className="flex items-center gap-3 shrink-0">
          {currentUser ? (
            <button
              type="button"
              onClick={() => setAuthModalOpen(true)}
              className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition-colors whitespace-nowrap shrink-0 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
            >
              <ResilientImage
                src={currentUser.avatarUrl}
                alt={currentUser.name}
                fallbackTitle={currentUser.name.slice(0, 1)}
                className="w-6 h-6 rounded-full object-cover"
              />
              <span className="text-xs font-medium text-slate-800">{currentUser.name}</span>
              <span className="text-xs font-mono text-slate-500">· {effectiveRole}</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setAuthModalOpen(true)}
              className="px-4 py-2 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
            >
              로그인 / OAuth
            </button>
          )}

          <button
            type="button"
            onClick={() => setMobileMenuOpen((v) => !v)}
            aria-label="메뉴 열기"
            className="xl:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </header>

      {/* Mobile Nav Drawer */}
      {mobileMenuOpen && (
        <div className="xl:hidden border-t border-slate-200 bg-white px-4 py-3 flex flex-wrap gap-2">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                setActiveTab(item.id);
                setMobileMenuOpen(false);
              }}
              className={`px-3 py-2 text-xs font-medium rounded-md whitespace-nowrap shrink-0 ${
                activeTab === item.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-100 text-slate-700'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}

      {/* Workspace Utility Toolbar (below header): Market Regime Context + RBAC Switcher */}
      <div className="bg-slate-50 border-t border-slate-200">
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-2 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-2.5">
          {/* Left: Dynamic Market Regime & Key Indices */}
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="font-medium text-slate-700 whitespace-nowrap shrink-0">
              시장·데이터 국면
            </span>
            <div
              role="group"
              aria-label="시장 국면 시뮬레이션"
              className="inline-flex items-center gap-1 p-0.5 bg-slate-200/70 rounded-lg"
            >
              {REGIME_OPTIONS.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setMarketRegime(opt.id)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    marketRegime === opt.id
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <div className="hidden xl:flex items-center gap-2 text-xs text-slate-500 font-mono tabular-nums">
              <span>KOSPI {regimeInfo.kospiIndex}</span>
              <span aria-hidden="true">·</span>
              <span>BTC {regimeInfo.btcKrw}</span>
              <span aria-hidden="true">·</span>
              <span>ETL {regimeInfo.etlThroughput}</span>
            </div>
          </div>

          {/* Right: RBAC Role Switcher for Instant Access-Control Testing */}
          <div className="flex flex-wrap items-center gap-2.5 text-xs">
            <span className="font-medium text-slate-600 whitespace-nowrap shrink-0">
              RBAC 권한 시뮬레이션
            </span>
            <div
              role="group"
              aria-label="역할 전환 스위치"
              className="inline-flex items-center gap-1 p-0.5 bg-slate-200/70 rounded-lg"
            >
              {ROLE_OPTIONS.map((opt) => (
                <button
                  key={opt.role}
                  type="button"
                  onClick={() => switchRolePreview(opt.role)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    effectiveRole === opt.role
                      ? 'bg-slate-900 text-white shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
