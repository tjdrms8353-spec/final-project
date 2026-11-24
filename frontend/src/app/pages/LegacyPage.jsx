import { usePlatform } from '../../context/PlatformContext';
import TrendPage from '../../pages/TrendPage.jsx';
import DocumentPage from '../../pages/DocumentPage.jsx';
import FinancePage from '../../pages/FinancePage.jsx';
import ReceiptPage from '../../pages/ReceiptPage.jsx';
import DataOpsPage from '../../pages/DataOpsPage.jsx';
import LegacyFrame from '../../components/LegacyPage.jsx';
import { cx } from '../ui';

const ClassicPage = () => <div>
  <LegacyFrame page="index" title="기존 대시보드" />
  <nav aria-label="기존 AutoFlow 화면" className="mt-3 flex flex-wrap gap-4 text-sm">
    {[['upload', '문서 업로드'], ['history', '처리 이력'], ['admin_rpa', 'RPA 관리']].map(([p, l]) =>
      <a key={p} href={`/legacy/${p}.html`} target="_blank" rel="noreferrer" className="text-brand-700 hover:underline">{l} ↗</a>)}
  </nav>
</div>;

export const LEGACY_MODULES = [
  { id: 'trends', label: '뉴스·SNS 트렌드', page: TrendPage, note: '저장된 뉴스 목록은 실제 DB와 연결되고, 순위·감성 분석 미리보기는 가상 데이터입니다.' },
  { id: 'documents', label: 'AI 문서 분류', page: DocumentPage },
  { id: 'finance', label: '금융 분석', page: FinancePage },
  { id: 'receipts', label: '영수증 OCR', page: ReceiptPage },
  { id: 'dataops', label: '운영 콘솔', page: DataOpsPage },
  { id: 'classic', label: '기존 대시보드', page: ClassicPage, note: '기존 AutoFlow HTML 화면을 그대로 불러옵니다.' },
];
const ROLES = ['GUEST', 'ANALYST', 'DATAOPS', 'ADMIN'];
const REGIMES = [['BULL_MOMENTUM', '강세·거래확대'], ['REGULATORY_ALERT', '규제 이슈 급증'], ['MACRO_TIGHTENING', '금리·환율 경계']];

function Toggle({ label, options, value, onChange }) {
  return <div className="flex flex-wrap items-center gap-2 text-xs"><span className="font-medium text-slate-600">{label}</span>
    <div role="group" aria-label={label} className="inline-flex gap-0.5 rounded-lg bg-slate-100 p-0.5">
      {options.map(([v, l]) => <button key={v} type="button" onClick={() => onChange(v)} aria-pressed={value === v}
        className={cx('rounded-md px-2 py-1 font-medium', value === v ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900')}>{l}</button>)}
    </div></div>;
}

export default function LegacyPage({ id }) {
  const { effectiveRole, switchRolePreview, marketRegime, setMarketRegime, currentUser, setAuthModalOpen } = usePlatform();
  const mod = LEGACY_MODULES.find(m => m.id === id) || LEGACY_MODULES[0];
  const Page = mod.page;
  return <div>
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-slate-900">{mod.label}</h1>
      <p className="mt-1 text-sm text-amber-800">{mod.note || '기존 프로젝트의 화면을 그대로 유지한 데모입니다. 표시 데이터는 가상 데이터이며 기업 BI 데이터와 연결되지 않습니다.'}</p>
      {mod.id !== 'classic' && <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2 rounded-lg border border-slate-200 bg-white px-4 py-2.5">
        <Toggle label="시장 국면" options={REGIMES} value={marketRegime} onChange={setMarketRegime} />
        <Toggle label="권한 미리보기" options={ROLES.map(r => [r, r])} value={effectiveRole} onChange={switchRolePreview} />
        <button type="button" onClick={() => setAuthModalOpen(true)} className="ml-auto text-xs font-medium text-brand-700 hover:underline">
          {currentUser ? `${currentUser.name} (데모 계정)` : '데모 로그인 / OAuth'}</button>
      </div>}
    </div>
    <Page />
  </div>;
}
