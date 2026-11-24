import { useEffect, useState } from 'react';
import { Pencil, Plus } from 'lucide-react';
import { bi } from '../../services/biApi';
import { Alert, Button, Card, Field, LABEL, PageHeader } from '../ui';
import { go, useWorkspace } from '../workspace';

const list = (t) => t.split(',').map(s => s.trim()).filter(Boolean);

export function CompanyForm({ company, onSaved, onCancel }) {
  const editing = Boolean(company);
  const [industries, setIndustries] = useState([]);
  const [form, setForm] = useState({
    name: '', industry: 'semiconductor', main_products: '', interest_industries: '', trade_countries: '', interest_indicators: '',
    annual_import_krw: '',
    ...(company ? {
      name: company.name, industry: company.industry,
      main_products: company.main_products.join(', '), interest_industries: company.interest_industries.join(', '),
      trade_countries: company.trade_countries.join(', '), interest_indicators: company.interest_indicators.join(', '),
      annual_import_krw: company.annual_import_krw ? String(company.annual_import_krw) : '',
    } : {}),
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { bi('/industries').then(setIndustries).catch(e => setError(e.message)); }, []);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const template = industries.find(i => i.code === form.industry);
  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    const body = {
      name: form.name, industry: form.industry, main_products: list(form.main_products), interest_industries: list(form.interest_industries),
      trade_countries: list(form.trade_countries), interest_indicators: list(form.interest_indicators),
      annual_import_krw: form.annual_import_krw.trim() === '' ? null : Number(form.annual_import_krw),
    };
    try {
      onSaved(await bi(editing ? `/companies/${company.id}` : '/companies', { method: editing ? 'PUT' : 'POST', body }));
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }
  return <Card title={editing ? '기업 정보 수정' : '기업 등록'} subtitle="쉼표로 여러 값을 입력할 수 있습니다." actions={onCancel && <Button variant="secondary" size="sm" onClick={onCancel}>취소</Button>}>
    <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
      <Field label="기업명" required value={form.name} onChange={set('name')} placeholder="예: 리본반도체" />
      <Field as="select" label="업종" value={form.industry} onChange={set('industry')}>{industries.map(i => <option key={i.code} value={i.code}>{i.label}</option>)}</Field>
      <Field label="주요 제품" value={form.main_products} onChange={set('main_products')} placeholder="DDR5 모듈, HBM 패키징" />
      <Field label="관심 산업" value={form.interest_industries} onChange={set('interest_industries')} placeholder="AI 서버, 자동차 전장" />
      <Field label="주요 거래 국가" value={form.trade_countries} onChange={set('trade_countries')} placeholder="미국, 일본, 대만" />
      <Field label="관심 금융지표" value={form.interest_indicators} onChange={set('interest_indicators')} placeholder={template?.market_indicators.join(', ')} hint="비워두면 업종 기본 지표를 사용합니다." />
      <Field label="연간 수입 규모(원)" type="number" min="0" step="100000000" value={form.annual_import_krw} onChange={set('annual_import_krw')}
        placeholder="예: 5000000000" hint="입력하면 환율 변동 시 연간 수입 비용 영향을 자동으로 계산합니다." />
      {template && <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600 md:col-span-2"><b className="text-slate-800">{template.label}</b> 업종 자동 구성 KPI: {template.kpis.map(k => k.label).join(' · ')}</div>}
      <div className="md:col-span-2"><Alert>{error}</Alert></div>
      <div className="md:col-span-2"><Button type="submit" disabled={busy}>{busy ? '저장 중...' : editing ? '저장' : '등록하고 대시보드 만들기'}</Button></div>
    </form>
  </Card>;
}

const Row = ({ label, children }) => <div className="grid grid-cols-3 gap-4 border-b border-slate-100 py-3 last:border-0">
  <dt className="text-sm text-slate-500">{label}</dt><dd className="col-span-2 text-sm text-slate-900">{children || '-'}</dd></div>;

export default function CompanyPage() {
  const { company, dashboard, loadCompanies, reload, selectCompany } = useWorkspace();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(false);
  if (creating) return <div className="mx-auto max-w-3xl"><CompanyForm onCancel={() => setCreating(false)}
    onSaved={c => { setCreating(false); loadCompanies(c.id).then(() => selectCompany(c.id)); go('data'); }} /></div>;
  if (editing && company) return <div className="mx-auto max-w-3xl"><CompanyForm company={company} onCancel={() => setEditing(false)}
    onSaved={() => { setEditing(false); loadCompanies(); reload(); }} /></div>;
  const t = dashboard?.template;
  return <div>
    <PageHeader title="기업 정보" description="등록한 기업 정보에 따라 KPI·뉴스 키워드·관심 지표가 정해집니다."
      actions={<span className="flex gap-2">{company.role === 'OWNER' && <Button variant="secondary" icon={Pencil} onClick={() => setEditing(true)}>수정</Button>}<Button icon={Plus} onClick={() => setCreating(true)}>새 기업 등록</Button></span>} />
    <div className="grid gap-6 xl:grid-cols-2">
      <Card title={company.name}>
        <dl>
          <Row label="업종">{company.industry_label}</Row><Row label="주요 제품">{company.main_products.join(', ')}</Row>
          <Row label="관심 산업">{company.interest_industries.join(', ')}</Row><Row label="주요 거래 국가">{company.trade_countries.join(', ')}</Row>
          <Row label="관심 금융지표">{company.interest_indicators.join(', ')}</Row>
          <Row label="연간 수입 규모">{company.annual_import_krw ? `${Number(company.annual_import_krw).toLocaleString('ko-KR')}원` : '미입력'}
            {company.annual_import_krw ? <span className="block text-xs text-slate-400">환율 변동 시 수입 비용 영향 자동 계산에 사용</span> : null}</Row>
          <Row label="내 권한">{LABEL[company.role]}</Row>
        </dl>
      </Card>
      {t && <Card title={`${t.label} 업종 템플릿`} subtitle="업종별 KPI와 기준값은 템플릿으로 확장할 수 있습니다." bodyClassName="p-0">
        <ul className="divide-y divide-slate-100">{t.kpis.map(k => <li key={k.code} className="flex items-start justify-between gap-3 px-5 py-2.5">
          <span><span className="block text-sm font-medium text-slate-900">{k.label}</span><span className="text-xs text-slate-500">{k.description}</span></span>
          <span className="whitespace-nowrap text-xs text-slate-400">{k.higher_is_better ? '높을수록 좋음' : '낮을수록 좋음'}</span></li>)}</ul>
        {t.news_keywords && <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">뉴스 키워드: {t.news_keywords.join(', ')}</p>}
      </Card>}
    </div>
  </div>;
}
