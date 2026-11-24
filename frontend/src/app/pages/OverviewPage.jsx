import { ArrowRight, Check, ClipboardList, Sparkles } from 'lucide-react';
import { Badge, Button, Card, cx, kpiText, kpiTitle, Loading } from '../ui';
import { go, useWorkspace } from '../workspace';

const STAGES = ['기업 등록', '데이터 업로드', '맞춤 대시보드', 'AI 분석', '근거 확인', '관리자 결정', '결과 기록'];
const HEADLINE = ['sales', 'operating_profit', 'gross_margin_pct', 'inventory_days'];

export default function OverviewPage() {
  const { company, dashboard, run, pendingCount, openActions } = useWorkspace();
  if (!dashboard) return <Loading />;
  const kpi = Object.fromEntries(dashboard.kpis.map(k => [k.code, k]));
  const pending = run?.findings.filter(f => f.status === 'PENDING') || [];
  const hasData = dashboard.monthly.length > 0;
  const stage = !company ? 0 : !hasData ? 1 : !run ? 3 : pendingCount ? 4 : openActions ? 6 : run ? 5 : 3;
  const month = dashboard.period;

  return <div className="space-y-5">
    <section aria-label="핵심 요약" className="rounded-2xl bg-slate-900 px-6 py-6 text-white sm:px-8">
      <p className="text-xs font-medium tracking-wide text-slate-400">일잘비 · 중소기업 맞춤형 AI 경영 분석</p>
      <h1 className="mt-2 text-xl font-bold sm:text-2xl">
        {company.name} · {company.industry_label}{month && <span className="ml-2 text-sm font-normal text-slate-400">({month} 기준)</span>}
      </h1>
      <p className="mt-1 text-sm text-slate-300">우리 회사 데이터와 뉴스·환율을 모아, 지금 챙길 기회와 위험을 근거와 함께 보여줍니다.</p>
    </section>

    <section aria-label="핵심 숫자" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {HEADLINE.filter(c => kpi[c]).map(k => {
        const up = kpi[k].previous != null && kpi[k].value > kpi[k].previous;
        const down = kpi[k].previous != null && kpi[k].value < kpi[k].previous;
        const bad = down !== Boolean(kpi[k].higher_is_better);
        return <div key={k.code} className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-medium text-slate-500">{k.label}</p>
          <p className="mt-1 text-xl font-bold tabular-nums text-slate-900 sm:text-2xl" title={kpiTitle(kpi[k].value, kpi[k].unit)}>{kpiText(kpi[k].value, kpi[k].unit)}</p>
          <p className={cx('mt-1 text-xs font-medium', kpi[k].previous == null ? 'text-slate-400' : bad ? 'text-red-700' : 'text-emerald-700')}>
            {kpi[k].previous == null ? '전월 데이터 없음' : `${up ? '▲' : down ? '▼' : '–'} 전월 대비 ${Math.abs((kpi[k].value / kpi[k].previous - 1) * 100).toFixed(1)}%`}
          </p>
        </div>;
      })}
    </section>

    <div className="grid gap-5 lg:grid-cols-3">
      <Card title={pendingCount ? `지금 검토할 항목 ${pendingCount}건` : '지금 검토할 항목 없음'} className="lg:col-span-2"
        actions={<Button variant="ghost" size="sm" onClick={() => go('analysis')}>분석 보기<ArrowRight className="h-3.5 w-3.5" /></Button>} bodyClassName="p-0">
        {pending.length ? <ul className="divide-y divide-slate-100">{pending.slice(0, 3).map(f => <li key={f.id}>
          <a href={`#/analysis?f=${f.id}`} className="flex items-center gap-3 px-5 py-3.5 hover:bg-slate-50">
            <Badge value={f.kind} /><span className="min-w-0 flex-1 text-sm font-medium text-slate-900">{f.title}</span>
            <Badge value={f.severity} prefix="영향 " /><ArrowRight className="h-4 w-4 text-slate-400" aria-hidden="true" />
          </a></li>)}</ul>
          : <div className="px-5 py-6 text-sm text-slate-600">{run ? '검토 대기 중인 분석이 없습니다. 모든 항목에 결정이 기록되었습니다.' : 'ERP 데이터를 업로드하면 AI가 기회와 위험을 찾습니다.'}</div>}
        {pending.length > 3 && <a href="#/analysis" className="block border-t border-slate-100 px-5 py-2.5 text-xs font-medium text-brand-700">나머지 {pending.length - 3}건 보기</a>}
      </Card>

      <Card title="오늘 할 일" bodyClassName="p-4">
        {openActions ? <p className="mb-3 flex items-center gap-2 text-sm text-slate-700"><ClipboardList className="h-4 w-4 text-brand-600" />진행 중인 후속조치 {openActions}건</p> : null}
        <ol className="space-y-2">{STAGES.map((label, i) => {
          const done = i < stage, current = i === stage;
          return <li key={label}><a href={`#/${['company', 'data', 'dashboard', 'analysis', 'analysis', 'decisions', 'decisions'][i]}`}
            className={cx('flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition', current ? 'bg-brand-50 font-semibold text-brand-800' : 'text-slate-600 hover:bg-slate-50')}>
            <span className={cx('flex h-5 w-5 items-center justify-center rounded-full text-[11px]', done ? 'bg-emerald-100 text-emerald-700' : current ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-400')}>
              {done ? <Check className="h-3 w-3" /> : i + 1}</span>{label}
          </a></li>;
        })}</ol>
      </Card>
    </div>

    <p className="text-center text-xs text-slate-400">
      <Sparkles className="mr-1 inline h-3.5 w-3.5" />AI는 계산된 숫자만 설명합니다. 결정은 항상 관리자가 합니다. 자세한 내용은 왼쪽 메뉴의 BI 대시보드·AI 분석에서 확인하세요.
    </p>
  </div>;
}
