import { ArrowRight, Check, CircleDashed, ClipboardList, Newspaper, Sparkles } from 'lucide-react';
import { Badge, Button, Card, cx, dateKo, Empty, Loading, Stat } from '../ui';
import { go, useWorkspace } from '../workspace';

const HEADLINE = ['sales', 'operating_profit', 'gross_margin_pct', 'inventory_days'];

function FlowProgress({ steps }) {
  return <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:grid-cols-7">
    {steps.map((s, i) => <li key={s.label}>
      <a href={`#/${s.to}`} className={cx('flex h-full flex-col rounded-lg border p-3 transition hover:border-brand-500',
        s.state === 'done' ? 'border-slate-200 bg-white' : s.state === 'todo' ? 'border-amber-300 bg-amber-50' : 'border-dashed border-slate-300 bg-white')}>
        <span className="flex items-center gap-1.5 text-xs text-slate-500">
          {s.state === 'done' ? <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" /> : <CircleDashed className={cx('h-3.5 w-3.5', s.state === 'todo' ? 'text-amber-600' : 'text-slate-400')} aria-hidden="true" />}
          {i + 1}단계<span className="sr-only">{s.state === 'done' ? ' 완료' : s.state === 'todo' ? ' 진행 필요' : ' 시작 전'}</span>
        </span>
        <span className="mt-1 text-sm font-semibold text-slate-900">{s.label}</span>
        <span className="mt-0.5 text-xs text-slate-500">{s.note}</span>
      </a>
    </li>)}
  </ol>;
}

export default function OverviewPage() {
  const { user, company, dashboard, run, decisions, actions, pendingCount, openActions } = useWorkspace();
  if (!dashboard) return <Loading />;
  const kpi = Object.fromEntries(dashboard.kpis.map(k => [k.code, k]));
  const pending = run?.findings.filter(f => f.status === 'PENDING') || [];
  const usd = dashboard.indicators['USD/KRW']?.change_30d;
  const hasData = dashboard.monthly.length > 0;
  const steps = [
    { label: '기업 등록', to: 'company', state: 'done', note: company.industry_label },
    { label: '데이터 업로드', to: 'data', state: hasData ? 'done' : 'todo', note: hasData ? `${dashboard.monthly.length}개월 데이터` : 'ERP·엑셀 업로드 필요' },
    { label: '맞춤 대시보드', to: 'dashboard', state: hasData ? 'done' : 'wait', note: `KPI ${dashboard.kpis.length}개` },
    { label: 'AI 분석', to: 'analysis', state: run ? 'done' : hasData ? 'todo' : 'wait', note: run ? `${run.period} · ${run.findings.length}건` : '분석 실행 필요' },
    { label: '근거 확인', to: 'analysis', state: run ? (pendingCount ? 'todo' : 'done') : 'wait', note: run ? `검토 대기 ${pendingCount}건` : '-' },
    { label: '관리자 결정', to: 'decisions', state: decisions.length ? 'done' : run ? 'todo' : 'wait', note: `결정 ${decisions.length}건` },
    { label: '결과 기록', to: 'decisions', state: actions.length && !openActions ? 'done' : actions.length ? 'todo' : 'wait', note: actions.length ? `조치 ${actions.length - openActions}/${actions.length} 완료` : '후속조치 없음' },
  ];

  return <div className="space-y-6">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="text-sm text-slate-500">안녕하세요, {user.name}님</p>
        <h1 className="mt-0.5 text-2xl font-bold text-slate-900">{company.name} 경영 현황</h1>
        <p className="mt-1 text-sm text-slate-500">{dashboard.period ? `${dashboard.period} 기준` : '데이터 없음'} · 주요 제품 {company.main_products.join(', ') || '-'} · 거래국 {company.trade_countries.join(', ') || '-'}</p>
      </div>
      <Button icon={Sparkles} onClick={() => go('analysis')}>분석 결과 보기</Button>
    </div>

    <section aria-label="의사결정 흐름"><FlowProgress steps={steps} /></section>

    <section aria-label="핵심 지표" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {HEADLINE.filter(c => kpi[c]).map(c => <Stat key={c} label={kpi[c].label} value={kpi[c].value} previous={kpi[c].previous} unit={kpi[c].unit} higherIsBetter={kpi[c].higher_is_better} />)}
    </section>

    <div className="grid gap-6 xl:grid-cols-5">
      <Card title="검토가 필요한 분석" subtitle={run ? `${run.period} 분석 · ${run.narrative_source === 'llm' ? 'LLM 요약' : '템플릿 요약'}` : undefined} className="xl:col-span-3"
        actions={<Button variant="ghost" size="sm" onClick={() => go('analysis')}>전체 보기<ArrowRight className="h-3.5 w-3.5" /></Button>} bodyClassName="p-0">
        {pending.length ? <ul className="divide-y divide-slate-100">{pending.map(f => <li key={f.id}>
          <a href={`#/analysis?f=${f.id}`} className="flex items-center gap-3 px-5 py-3.5 hover:bg-slate-50">
            <Badge value={f.kind} /><span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-900">{f.title}</span>
            <Badge value={f.severity} prefix="영향 " /><ArrowRight className="h-4 w-4 text-slate-400" aria-hidden="true" />
          </a></li>)}</ul>
          : <div className="p-5"><Empty icon={Sparkles} title={run ? '검토 대기 중인 분석이 없습니다' : '아직 분석 결과가 없습니다'} description={run ? '모든 항목에 결정이 기록되었습니다.' : 'ERP 데이터를 업로드한 뒤 분석을 실행하세요.'} /></div>}
      </Card>

      <Card title="진행 중인 후속조치" className="xl:col-span-2" actions={<Button variant="ghost" size="sm" onClick={() => go('decisions')}>관리<ArrowRight className="h-3.5 w-3.5" /></Button>} bodyClassName="p-0">
        {actions.filter(a => a.status !== 'DONE').length ? <ul className="divide-y divide-slate-100">{actions.filter(a => a.status !== 'DONE').slice(0, 5).map(a => <li key={a.id} className="px-5 py-3">
          <div className="flex items-start justify-between gap-2"><p className="text-sm font-medium text-slate-900">{a.title}</p><Badge value={a.status} /></div>
          <p className="mt-0.5 text-xs text-slate-500">담당 {a.assignee || '미지정'} · 기한 {a.due_date || '-'}</p>
        </li>)}</ul> : <div className="p-5"><Empty icon={ClipboardList} title="진행 중인 후속조치가 없습니다" /></div>}
      </Card>
    </div>

    <div className="grid gap-6 xl:grid-cols-5">
      <Card title="시장 신호" subtitle="무료 ECB 기준환율 · 저장된 뉴스" className="xl:col-span-2">
        <dl className="grid grid-cols-2 gap-4">
          <div><dt className="text-xs text-slate-500">USD/KRW 30일 변동</dt>
            <dd className={cx('mt-1 text-xl font-bold tabular-nums', usd ? (usd.change_pct >= 0 ? 'text-red-700' : 'text-emerald-700') : 'text-slate-400')}>{usd ? `${usd.change_pct > 0 ? '+' : ''}${usd.change_pct}%` : '-'}</dd>
            {usd && <dd className="text-xs text-slate-500 tabular-nums">{usd.from_value.toLocaleString('ko-KR')} → {usd.to_value.toLocaleString('ko-KR')}원</dd>}</div>
          <div><dt className="text-xs text-slate-500">관련 뉴스 (최근 {dashboard.news.days || 14}일)</dt>
            <dd className="mt-1 text-xl font-bold tabular-nums text-slate-900">{dashboard.news.recent_count}건</dd>
            <dd className="text-xs text-slate-500">직전 기간 {dashboard.news.previous_count ?? 0}건</dd></div>
        </dl>
        <p className="mt-4 text-xs text-slate-500">외화 매입 비중 {kpi.fx_purchase_share_pct?.value ?? '-'}% · 수출 비중 {kpi.export_share_pct?.value ?? '-'}% → 환율 변동이 원가·매출에 함께 영향을 줍니다.</p>
      </Card>
      <Card title="관련 산업 뉴스" className="xl:col-span-3" actions={<Button variant="ghost" size="sm" onClick={() => go('market')}>더 보기<ArrowRight className="h-3.5 w-3.5" /></Button>} bodyClassName="p-0">
        {dashboard.news.items.length ? <ul className="divide-y divide-slate-100">{dashboard.news.items.slice(0, 5).map(n => <li key={n.url}>
          <a href={n.url} target="_blank" rel="noreferrer" className="block px-5 py-3 hover:bg-slate-50">
            <p className="text-sm text-slate-900">{n.title}</p><p className="mt-0.5 text-xs text-slate-500">{n.source} · {dateKo(n.date)}</p>
          </a></li>)}</ul> : <div className="p-5"><Empty icon={Newspaper} title="일치하는 저장 기사가 없습니다" /></div>}
      </Card>
    </div>
  </div>;
}
