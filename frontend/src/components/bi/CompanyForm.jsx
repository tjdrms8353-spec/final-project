import { useEffect, useState } from 'react';
import { bi } from '../../services/biApi';
import { Alert, Button, Card, Field } from './ui';

const list = (text) => text.split(',').map(s => s.trim()).filter(Boolean);

export default function CompanyForm({ onCreated, onCancel }) {
  const [industries, setIndustries] = useState([]);
  const [form, setForm] = useState({ name: '', industry: 'semiconductor', main_products: '', interest_industries: '', trade_countries: '', interest_indicators: '' });
  const [error, setError] = useState('');
  useEffect(() => { bi('/industries').then(setIndustries).catch(e => setError(e.message)); }, []);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const template = industries.find(i => i.code === form.industry);

  async function submit(event) {
    event.preventDefault();
    setError('');
    try {
      const company = await bi('/companies', { method: 'POST', body: {
        name: form.name, industry: form.industry, main_products: list(form.main_products),
        interest_industries: list(form.interest_industries), trade_countries: list(form.trade_countries),
        interest_indicators: list(form.interest_indicators),
      } });
      onCreated(company);
    } catch (e) { setError(e.message); }
  }

  return <Card title="기업 등록" actions={onCancel && <Button variant="secondary" onClick={onCancel}>취소</Button>}>
    <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
      <Field label="기업명" required value={form.name} onChange={set('name')} placeholder="예: 리본반도체" />
      <label className="block text-sm"><span className="mb-1 block font-medium text-slate-700">업종</span>
        <select value={form.industry} onChange={set('industry')} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
          {industries.map(i => <option key={i.code} value={i.code}>{i.label}</option>)}
        </select></label>
      <Field label="주요 제품 (쉼표 구분)" value={form.main_products} onChange={set('main_products')} placeholder="DDR5, HBM" />
      <Field label="관심 산업 (쉼표 구분)" value={form.interest_industries} onChange={set('interest_industries')} placeholder="AI 서버, 자동차 전장" />
      <Field label="주요 거래 국가 (쉼표 구분)" value={form.trade_countries} onChange={set('trade_countries')} placeholder="미국, 일본, 대만" />
      <Field label="관심 금융지표 (쉼표 구분)" value={form.interest_indicators} onChange={set('interest_indicators')}
        placeholder={template?.market_indicators.join(', ')} hint="비워두면 업종 기본 지표를 사용합니다." />
      {template && <div className="md:col-span-2 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
        <b>{template.label}</b> 업종 자동 구성 KPI: {template.kpis.map(k => k.label).join(' · ')}
      </div>}
      <div className="md:col-span-2"><Alert>{error}</Alert></div>
      <div className="md:col-span-2"><Button type="submit">등록하고 대시보드 만들기</Button></div>
    </form>
  </Card>;
}
