import { useEffect, useState } from 'react';
import { ExternalLink, Search } from 'lucide-react';
import { Line, LineChart, ResponsiveContainer } from 'recharts';
import { request } from '../../services/api';
import { Button, Card, CHART, cx, dateTimeKo, Empty, indicatorLabel, Loading, PageHeader } from '../ui';
import { useWorkspace } from '../workspace';

const PAGE = 10;
const safe = (u) => /^https?:\/\//i.test(u || '') ? u : undefined;

function NewsSearch() {
  const [draft, setDraft] = useState('');
  const [q, setQ] = useState('');
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const c = new AbortController();
    setData(null); setError('');
    const p = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
    if (q) p.set('q', q);
    request(`/api/news?${p}`, { signal: c.signal }).then(d => !c.signal.aborted && setData(d))
      .catch(() => !c.signal.aborted && setError('뉴스를 불러오지 못했습니다.'));
    return () => c.abort();
  }, [q, offset]);
  return <Card title="수집 뉴스 검색" subtitle="RSS 수집기가 저장한 실제 기사 (원문 링크 제공)" bodyClassName="p-0">
    <form className="flex gap-2 border-b border-slate-100 p-4" onSubmit={e => { e.preventDefault(); setOffset(0); setQ(draft.trim()); }}>
      <input value={draft} onChange={e => setDraft(e.target.value)} placeholder="키워드 (예: 반도체, 환율, HBM)" aria-label="뉴스 검색어"
        className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-600 focus:outline-none" />
      <Button type="submit" icon={Search}>검색</Button>
    </form>
    {error ? <p className="p-4 text-sm text-red-700" role="alert">{error}</p> : !data ? <div className="px-4"><Loading /></div> : data.items.length ? <>
      <ul className="divide-y divide-slate-100">{data.items.map(n => <li key={n.id} className="px-4 py-3">
        <a href={safe(n.url)} target="_blank" rel="noreferrer" className="inline-flex items-start gap-1 text-sm text-slate-900 hover:text-brand-700">{n.title_ko || n.title}<ExternalLink className="mt-1 h-3 w-3 shrink-0 text-slate-400" aria-hidden="true" /></a>
        <p className="mt-0.5 text-xs text-slate-500">{n.source} · {dateTimeKo(n.published_at || n.observed_at)}</p>
      </li>)}</ul>
      <div className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-xs text-slate-500">
        <span className="tabular-nums">총 {data.total}건 중 {offset + 1}–{Math.min(offset + PAGE, data.total)}</span>
        <span className="flex gap-2"><Button size="sm" variant="secondary" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - PAGE))}>이전</Button>
          <Button size="sm" variant="secondary" disabled={offset + PAGE >= data.total} onClick={() => setOffset(offset + PAGE)}>다음</Button></span>
      </div></> : <div className="p-4"><Empty title="검색 결과가 없습니다" /></div>}
  </Card>;
}

export default function MarketPage() {
  const { dashboard, company } = useWorkspace();
  if (!dashboard) return <Loading />;
  const indicators = Object.entries(dashboard.indicators);
  return <div className="space-y-6">
    <PageHeader title="시장·뉴스" description={`${company.name}의 관심 지표와 관련 산업 뉴스입니다. 환율은 ECB 기준환율, 금리·유가는 Yahoo Finance 무료 데이터를 사용합니다.`} />
    <section aria-label="관심 금융지표" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {indicators.map(([code, ind]) => {
        const last = ind.series.at(-1); const ch = ind.change_30d;
        return <div key={code} className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium text-slate-500">{indicatorLabel(code)} <span className="text-slate-400">({code})</span></p>
          {last ? <>
            <div className="mt-1 flex items-end justify-between gap-2">
              <p className="text-xl font-bold tabular-nums text-slate-900">{last.value.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}</p>
              <div className="h-9 w-24" aria-hidden="true"><ResponsiveContainer><LineChart data={ind.series.slice(-60)}><Line isAnimationActive={false} dataKey="value" dot={false} stroke={CHART.violet} strokeWidth={1.75} /></LineChart></ResponsiveContainer></div>
            </div>
            <p className={cx('mt-1 text-xs font-medium tabular-nums', ch ? (ch.change_pct >= 0 ? 'text-red-700' : 'text-emerald-700') : 'text-slate-400')}>{ch ? `30일 ${ch.change_pct > 0 ? '+' : ''}${ch.change_pct}%` : '변동 정보 없음'}</p>
            <p className="mt-0.5 text-[11px] text-slate-400">{last.date} 기준</p>
          </> : <p className="mt-2 text-sm text-slate-400">데이터 없음 {code === 'KR_BASE_RATE' ? '(자동 수집 예정)' : ''}</p>}
        </div>;
      })}
    </section>
    <div className="grid gap-6 xl:grid-cols-5">
      <Card title={`${company.name} 관련 뉴스`} subtitle={`최근 ${dashboard.news.days || 14}일 ${dashboard.news.recent_count}건 · 키워드 ${dashboard.news.keywords.slice(0, 6).join(', ')} 외`} className="xl:col-span-2" bodyClassName="p-0">
        {dashboard.news.items.length ? <ul className="divide-y divide-slate-100">{dashboard.news.items.map(n => <li key={n.url} className="px-5 py-3">
          <a href={safe(n.url)} target="_blank" rel="noreferrer" className="text-sm text-slate-900 hover:text-brand-700">{n.title}</a>
          <p className="mt-0.5 text-xs text-slate-500">{n.source} · {dateTimeKo(n.date)}</p></li>)}</ul>
          : <div className="p-5"><Empty title="일치하는 저장 기사가 없습니다" /></div>}
      </Card>
      <div className="xl:col-span-3"><NewsSearch /></div>
    </div>
  </div>;
}
