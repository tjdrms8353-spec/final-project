import { useCallback, useEffect, useState } from 'react';
import AnalysisPanel from '../components/bi/AnalysisPanel.jsx';
import BiAuthPanel from '../components/bi/BiAuthPanel.jsx';
import BiDashboard, { UploadPanel } from '../components/bi/BiDashboard.jsx';
import CompanyForm from '../components/bi/CompanyForm.jsx';
import DecisionsPanel from '../components/bi/DecisionsPanel.jsx';
import MembersPanel from '../components/bi/MembersPanel.jsx';
import SimulationPanel from '../components/bi/SimulationPanel.jsx';
import { Alert, Button } from '../components/bi/ui.jsx';
import { bi, biToken } from '../services/biApi';

const TABS = [['dashboard', '맞춤 대시보드'], ['analysis', 'AI 기회·위험 분석'], ['decisions', '결정·후속조치'], ['simulation', '시나리오'], ['settings', '데이터·구성원']];
const FLOW = ['기업 등록', '데이터 업로드', '맞춤 대시보드', 'AI 기회·위험 분석', '근거 확인', '관리자 결정', '결과 기록'];

export default function BiPage() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(Boolean(biToken.get()));
  const [companies, setCompanies] = useState([]);
  const [companyId, setCompanyId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [tab, setTab] = useState('dashboard');
  const [dashboard, setDashboard] = useState(null);
  const [members, setMembers] = useState([]);
  const [version, setVersion] = useState(0);
  const [error, setError] = useState('');

  const logout = () => { biToken.clear(); setUser(null); setCompanies([]); setCompanyId(null); setDashboard(null); };

  useEffect(() => {
    if (!biToken.get()) return;
    bi('/auth/me').then(setUser).catch(() => biToken.clear()).finally(() => setChecking(false));
  }, []);

  const loadCompanies = useCallback(async (selectId) => {
    const list = await bi('/companies');
    setCompanies(list);
    setCompanyId(id => selectId || (list.some(c => c.id === id) ? id : list[0]?.id ?? null));
  }, []);
  useEffect(() => { if (user) loadCompanies().catch(e => setError(e.message)); }, [user, loadCompanies]);

  const refresh = useCallback(() => {
    if (!companyId) return;
    setError('');
    Promise.all([bi(`/companies/${companyId}/dashboard`), bi(`/companies/${companyId}/members`)])
      .then(([d, m]) => { setDashboard(d); setMembers(m); })
      .catch(e => { if (e.status === 401) logout(); setError(e.message); });
  }, [companyId]);
  useEffect(() => { setDashboard(null); refresh(); }, [refresh, version]);

  if (checking) return <p className="p-8 text-sm text-slate-500">세션 확인 중...</p>;
  if (!user) return <BiAuthPanel onLogin={setUser} />;
  const company = companies.find(c => c.id === companyId);

  return <div className="mx-auto max-w-[1440px] space-y-5 px-4 py-6 md:px-6">
    <header className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 className="font-display text-2xl font-semibold text-slate-900">기업 맞춤 BI</h2>
        <ol className="mt-1 flex flex-wrap gap-1 text-xs text-slate-500" aria-label="의사결정 흐름">
          {FLOW.map((s, i) => <li key={s}>{i ? '→ ' : ''}{s}</li>)}</ol>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        {companies.length > 0 && <select aria-label="기업 선택" value={companyId || ''} onChange={e => { setCompanyId(Number(e.target.value)); setCreating(false); }}
          className="rounded-lg border border-slate-300 px-2 py-2">
          {companies.map(c => <option key={c.id} value={c.id}>{c.name} · {c.industry_label} ({c.role})</option>)}</select>}
        <Button variant="secondary" onClick={() => setCreating(true)}>+ 기업 등록</Button>
        <span className="text-slate-600">{user.name}</span>
        <Button variant="secondary" onClick={logout}>로그아웃</Button>
      </div>
    </header>
    <Alert>{error}</Alert>

    {creating || !company ? <CompanyForm onCancel={companies.length ? () => setCreating(false) : null}
      onCreated={c => { setCreating(false); setTab('settings'); loadCompanies(c.id); }} /> : <>
      <nav className="flex flex-wrap gap-1 border-b border-slate-200" aria-label="BI 메뉴">
        {TABS.map(([id, label]) => <button key={id} type="button" onClick={() => setTab(id)} aria-current={tab === id ? 'page' : undefined}
          className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium ${tab === id ? 'border-blue-600 text-blue-700' : 'border-transparent text-slate-600 hover:text-slate-900'}`}>{label}</button>)}
      </nav>
      <p className="text-xs text-slate-500">{company.name} · {company.industry_label} · 주요 제품 {company.main_products.join(', ') || '-'} · 거래국 {company.trade_countries.join(', ') || '-'} · 내 권한 {company.role}</p>
      {tab === 'dashboard' && (dashboard ? <BiDashboard key={companyId} data={dashboard} onRefresh={() => setVersion(v => v + 1)} /> : <p className="text-sm text-slate-500">불러오는 중...</p>)}
      {tab === 'analysis' && <AnalysisPanel company={company} members={members} onChanged={() => setVersion(v => v + 1)} />}
      {tab === 'decisions' && <DecisionsPanel company={company} version={version} />}
      {tab === 'simulation' && <SimulationPanel company={company} />}
      {tab === 'settings' && <div className="grid gap-5 xl:grid-cols-2">
        <UploadPanel company={company} onUploaded={() => setVersion(v => v + 1)} />
        <MembersPanel company={company} members={members} onChanged={() => setVersion(v => v + 1)} />
      </div>}
    </>}
  </div>;
}
