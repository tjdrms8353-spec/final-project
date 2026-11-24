import { useState } from 'react';
import {
  Archive, BookOpen, Building2, ClipboardCheck, Database, FileText, FlaskConical, Gauge, LayoutDashboard, LogOut, Menu,
  Newspaper, Receipt, Server, ShieldCheck, Sparkles, TrendingUp, Upload, Users, X,
} from 'lucide-react';
import { Logo } from './Logo';
import { Badge, cx, Loading } from './ui';
import { go, useHashRoute, useWorkspace } from './workspace';
import OverviewPage from './pages/OverviewPage';
import DashboardPage from './pages/DashboardPage';
import AnalysisPage from './pages/AnalysisPage';
import DecisionsPage from './pages/DecisionsPage';
import SimulationPage from './pages/SimulationPage';
import MarketPage from './pages/MarketPage';
import DataPage from './pages/DataPage';
import MembersPage from './pages/MembersPage';
import CompanyPage, { CompanyForm } from './pages/CompanyPage';
import ReportsPage from './pages/ReportsPage';
import AuditPage from './pages/AuditPage';
import LegacyPage, { LEGACY_MODULES } from './pages/LegacyPage';

const LEGACY_ICONS = { trends: Newspaper, documents: FileText, finance: TrendingUp, receipts: Receipt, dataops: Server, classic: Archive };

const NAV = [
  { group: '경영 현황', items: [
    { id: 'overview', label: '개요', icon: Gauge, page: OverviewPage },
    { id: 'dashboard', label: 'BI 대시보드', icon: LayoutDashboard, page: DashboardPage },
    { id: 'market', label: '시장·뉴스', icon: Newspaper, page: MarketPage },
  ] },
  { group: '의사결정', items: [
    { id: 'analysis', label: 'AI 기회·위험 분석', icon: Sparkles, page: AnalysisPage, count: 'pendingCount' },
    { id: 'decisions', label: '결정·후속조치', icon: ClipboardCheck, page: DecisionsPage, count: 'openActions' },
    { id: 'simulation', label: '시나리오 시뮬레이션', icon: FlaskConical, page: SimulationPage },
  ] },
  { group: '데이터·관리', items: [
    { id: 'data', label: 'ERP 데이터 업로드', icon: Upload, page: DataPage },
    { id: 'members', label: '구성원·권한', icon: Users, page: MembersPage },
    { id: 'company', label: '기업 정보', icon: Building2, page: CompanyPage },
  ] },
  { group: '보고·감사', items: [
    { id: 'reports', label: '주간·월간 보고서', icon: BookOpen, page: ReportsPage },
    { id: 'audit', label: '감사 추적 로그', icon: ShieldCheck, page: AuditPage },
  ] },
  { group: '기존 기능 (데모 화면)', items: LEGACY_MODULES.map(m => ({ id: `legacy/${m.id}`, label: m.label, icon: LEGACY_ICONS[m.id] || Database, page: LegacyPage, legacy: true })) },
];
const ALL = NAV.flatMap(g => g.items);

function Sidebar({ current, onNavigate }) {
  const ws = useWorkspace();
  const { user, companies, company, selectCompany, onLogout } = ws;
  return <div className="flex h-full flex-col">
    <div className="flex h-16 items-center px-5"><button type="button" onClick={() => { go('overview'); onNavigate(); }} aria-label="dayribbon 개요로 이동"><Logo /></button></div>
    {companies?.length > 0 && <div className="px-3 pb-3">
      <label className="block rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
        <span className="block text-[11px] font-medium text-slate-500">기업</span>
        <select aria-label="기업 선택" value={company?.id || ''} onChange={e => { selectCompany(Number(e.target.value)); onNavigate(); }}
          className="mt-0.5 w-full truncate bg-transparent text-sm font-semibold text-slate-900 focus:outline-none">
          {companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>
    </div>}
    <nav aria-label="주요 메뉴" className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
      {NAV.map(g => <div key={g.group}>
        <p className="px-2 pb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400">{g.group}</p>
        <ul className="space-y-0.5">{g.items.map(item => {
          const active = current === item.id;
          const count = item.count ? ws[item.count] : 0;
          return <li key={item.id}><a href={`#/${item.id}`} onClick={onNavigate} aria-current={active ? 'page' : undefined}
            className={cx('flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors',
              active ? 'bg-brand-50 font-semibold text-brand-700' : item.legacy ? 'text-slate-500 hover:bg-slate-100 hover:text-slate-900' : 'text-slate-700 hover:bg-slate-100 hover:text-slate-900')}>
            <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="flex-1 truncate">{item.label}</span>
            {count > 0 && <span className="rounded-full bg-ribbon px-1.5 text-[11px] font-semibold text-white tabular-nums">{count}</span>}
          </a></li>;
        })}</ul>
      </div>)}
    </nav>
    <div className="border-t border-slate-200 p-3">
      <div className="flex items-center gap-2.5 rounded-lg px-2 py-1.5">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">{user.name.slice(0, 1)}</span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-slate-900">{user.name}</span>
          <span className="block truncate text-xs text-slate-500">{user.email}</span>
        </span>
        <button type="button" onClick={onLogout} className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900" aria-label="로그아웃" title="로그아웃">
          <LogOut className="h-4 w-4" aria-hidden="true" /></button>
      </div>
    </div>
  </div>;
}

export default function AppShell() {
  const { path, params } = useHashRoute();
  const ws = useWorkspace();
  const [open, setOpen] = useState(false);
  const item = ALL.find(i => i.id === path) || ALL[0];
  const Page = item.page;
  const close = () => setOpen(false);

  let content;
  if (item.legacy) content = <LegacyPage id={path.split('/')[1]} />;
  else if (ws.companies === null) content = <Loading />;
  else if (!ws.company) content = <div className="mx-auto max-w-3xl">
    <h1 className="text-2xl font-bold text-slate-900">첫 기업을 등록하세요</h1>
    <p className="mb-6 mt-1 text-sm text-slate-500">업종을 고르면 그 업종에 맞는 KPI 대시보드가 자동으로 구성됩니다.</p>
    <CompanyForm onCreated={c => { ws.loadCompanies(c.id); go('data'); }} />
  </div>;
  else content = <Page params={params} />;

  return <div className="min-h-screen bg-canvas lg:pl-64">
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-slate-200 bg-white lg:block print:hidden"><Sidebar current={item.id} onNavigate={close} /></aside>
    {open && <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="메뉴">
      <button type="button" className="absolute inset-0 bg-slate-900/40" onClick={close} aria-label="메뉴 닫기" />
      <aside className="relative h-full w-72 max-w-[85vw] bg-white shadow-xl print:hidden">
        <button type="button" onClick={close} className="absolute right-3 top-4 rounded-md p-1.5 text-slate-500 hover:bg-slate-100" aria-label="메뉴 닫기"><X className="h-5 w-5" /></button>
        <Sidebar current={item.id} onNavigate={close} />
      </aside>
    </div>}
    <header className="sticky top-0 z-20 flex h-14 print:hidden items-center gap-3 border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6">
      <button type="button" className="rounded-md p-1.5 text-slate-600 hover:bg-slate-100 lg:hidden" onClick={() => setOpen(true)} aria-label="메뉴 열기"><Menu className="h-5 w-5" /></button>
      <p className="min-w-0 flex-1 truncate text-sm text-slate-500">
        {ws.company && !item.legacy ? <><span className="font-medium text-slate-900">{ws.company.name}</span><span className="mx-1.5">/</span></> : null}{item.label}
      </p>
      {ws.loading && !item.legacy && <span className="hidden text-xs text-slate-400 sm:inline" role="status">동기화 중...</span>}
      {ws.company && !item.legacy && <Badge value={ws.company.role}>{ws.company.role} · {ws.company.industry_label}</Badge>}
      {import.meta.env.VITE_DEMO_MODE === '1' && <span className="hidden rounded-md bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200 sm:inline">데모</span>}
    </header>
    <main className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:py-8">
      {ws.error && !item.legacy && <p role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{ws.error}</p>}
      {content}
    </main>
  </div>;
}
