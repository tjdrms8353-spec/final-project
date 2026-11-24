import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { bi } from '../services/biApi';

const parseHash = () => {
  const [path, query = ''] = window.location.hash.replace(/^#\/?/, '').split('?');
  return { path: path || 'overview', params: Object.fromEntries(new URLSearchParams(query)) };
};

export function useHashRoute() {
  const [route, setRoute] = useState(parseHash);
  useEffect(() => {
    const onChange = () => { setRoute(parseHash()); window.scrollTo(0, 0); };
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}

export const go = (path, params) => {
  const q = params ? `?${new URLSearchParams(params)}` : '';
  window.location.hash = `/${path}${q}`;
};

const COMPANY_KEY = 'dayribbon-company';
const Ctx = createContext(null);

export function WorkspaceProvider({ user, onLogout, children }) {
  const [companies, setCompanies] = useState(null);
  const [companyId, setCompanyId] = useState(() => Number(localStorage.getItem(COMPANY_KEY)) || null);
  const [data, setData] = useState({ dashboard: null, members: [], run: null, runs: [], decisions: [], actions: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion(v => v + 1), []);

  const fail = useCallback((e) => { if (e.status === 401) onLogout(); else setError(e.message); }, [onLogout]);

  const loadCompanies = useCallback(async (selectId) => {
    const list = await bi('/companies');
    setCompanies(list);
    setCompanyId(id => {
      const next = selectId || (list.some(c => c.id === id) ? id : list[0]?.id ?? null);
      if (next) localStorage.setItem(COMPANY_KEY, String(next));
      return next;
    });
  }, []);
  useEffect(() => { loadCompanies().catch(fail); }, [loadCompanies, fail]);

  useEffect(() => {
    if (!companyId || !companies?.some(c => c.id === companyId)) return;
    let alive = true;
    setLoading(true); setError('');
    const base = `/companies/${companyId}`;
    Promise.all([bi(`${base}/dashboard`), bi(`${base}/members`), bi(`${base}/analyses`), bi(`${base}/decisions`), bi(`${base}/actions`)])
      .then(async ([dashboard, members, runs, decisions, actions]) => {
        const run = runs[0] ? await bi(`${base}/analyses/${runs[0].id}`) : null;
        if (alive) setData({ dashboard, members, runs, run, decisions, actions });
      })
      .catch(e => alive && fail(e))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [companyId, companies, version, fail]);

  const company = companies?.find(c => c.id === companyId) || null;
  const value = useMemo(() => {
    const role = company?.role;
    return {
      user, onLogout, companies, company, ...data, loading, error, setError, reload, loadCompanies,
      selectCompany: (id) => { localStorage.setItem(COMPANY_KEY, String(id)); setData({ dashboard: null, members: [], run: null, runs: [], decisions: [], actions: [] }); setCompanyId(id); },
      can: { write: ['OWNER', 'APPROVER', 'ANALYST'].includes(role), decide: ['OWNER', 'APPROVER'].includes(role), admin: role === 'OWNER' },
      pendingCount: data.run?.findings.filter(f => f.status === 'PENDING').length || 0,
      openActions: data.actions.filter(a => a.status !== 'DONE').length,
    };
  }, [user, onLogout, companies, company, data, loading, error, reload, loadCompanies]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export const useWorkspace = () => useContext(Ctx);
