import { useEffect, useRef, useState } from 'react';
import { Download, FileSpreadsheet, UploadCloud } from 'lucide-react';
import { bi } from '../../services/biApi';
import { Alert, Card, cx, dateTimeKo, Empty, PageHeader } from '../ui';
import { useWorkspace } from '../workspace';

const COLUMNS = [
  ['date', '필수', '거래일 (YYYY-MM-DD)', '2026-10-31'], ['category', '필수', '매출 / 매입 / 지출 / 재고 (sales, purchase, expense, inventory)', '매출'],
  ['item', '필수', '품목·계정명', 'DDR5 모듈'], ['amount', '필수', '금액 (원)', '420000000'],
  ['quantity', '선택', '수량', '12000'], ['country', '선택', '거래 국가 (한국 외는 수출·외화 매입으로 집계)', '미국'],
];

export default function DataPage() {
  const { company, can, reload } = useWorkspace();
  const input = useRef(null);
  const [uploads, setUploads] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);
  const load = () => bi(`/companies/${company.id}/erp/uploads`).then(setUploads).catch(e => setError(e.message));
  useEffect(() => { load(); }, [company.id]);

  async function upload(file) {
    if (!file || !can.write) return;
    setBusy(true); setError(''); setResult(null);
    try { setResult(await bi(`/companies/${company.id}/erp/upload`, { method: 'POST', file })); load(); reload(); }
    catch (e) { setError(e.message); } finally { setBusy(false); if (input.current) input.current.value = ''; }
  }

  return <div className="space-y-6">
    <PageHeader title="ERP 데이터 업로드" description="ERP는 기업의 매출·매입·지출·재고를 기록하는 경영 관리 시스템입니다. ERP가 없어도 그 데이터를 CSV 또는 Excel(.xlsx)로 올리면 업종 KPI가 자동 계산됩니다. 최대 10MB · 5만 행, UTF-8·CP949 지원." />
    <div className="grid gap-6 xl:grid-cols-5">
      <div className="min-w-0 space-y-4 xl:col-span-3">
        <Card title="처음이라면: 예시 데이터로 바로 체험하기" subtitle="예시 파일을 내려받아 그대로 업로드하면 KPI·분석 결과를 바로 볼 수 있습니다.">
          <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-600">
            <li>아래 예시 데이터(반도체 또는 자동차 부품)를 다운로드합니다.</li>
            <li>파일을 이 페이지에 끌어다 놓거나 선택해 업로드합니다.</li>
            <li>‘BI 대시보드’와 ‘AI 기회·위험 분석’에서 결과를 확인합니다.</li>
          </ol>
          <p className="mt-2 text-xs text-slate-500">주의: 예시 파일은 데모용 가상 데이터이며, 업로드하면 기존 데이터에 <b>추가</b>됩니다. 같은 파일을 다시 올리면 금액이 중복 집계되니, 체험 후에는 새 기업을 등록해 사용하는 것을 권장합니다.</p>
        </Card>
        <label onDragOver={e => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={e => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files?.[0]); }}
          className={cx('flex flex-col items-center justify-center rounded-xl border-2 border-dashed bg-white px-6 py-12 text-center transition',
            !can.write ? 'cursor-not-allowed border-slate-200 opacity-60' : drag ? 'cursor-pointer border-brand-500 bg-brand-50' : 'cursor-pointer border-slate-300 hover:border-brand-500')}>
          <UploadCloud className="h-10 w-10 text-brand-600" aria-hidden="true" />
          <span className="mt-3 text-sm font-semibold text-slate-900">{busy ? '업로드 중...' : '파일을 끌어다 놓거나 클릭해서 선택'}</span>
          <span className="mt-1 text-xs text-slate-500">{can.write ? '.csv, .xlsx' : '조회자는 업로드할 수 없습니다'}</span>
          <input ref={input} type="file" accept=".csv,.xlsx" className="sr-only" aria-label="ERP 파일 선택" disabled={busy || !can.write} onChange={e => upload(e.target.files?.[0])} />
        </label>
        <Alert tone="warn">업로드한 행은 기존 데이터에 추가됩니다. 같은 파일을 다시 올리면 금액이 중복 집계됩니다.</Alert>
        <Alert>{error}</Alert>
        {result && <Alert tone={result.rejected ? 'warn' : 'ok'}>{result.accepted}행 저장{result.rejected ? ` · ${result.rejected}행 제외: ${result.errors.join(' / ')}` : ' · 대시보드에 반영되었습니다.'}</Alert>}
        <div className="flex flex-wrap gap-2 text-sm">
          <a className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 font-medium text-slate-700 hover:bg-slate-50" href="/api/bi/erp/template.csv"><Download className="h-4 w-4" />빈 양식 다운로드</a>
          <a className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 font-medium text-slate-700 hover:bg-slate-50" href="/samples/semiconductor_erp_sample.csv" download><FileSpreadsheet className="h-4 w-4" />반도체 샘플 데이터</a>
          <a className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 font-medium text-slate-700 hover:bg-slate-50" href="/samples/auto_parts_erp_sample.csv" download><FileSpreadsheet className="h-4 w-4" />자동차 부품 샘플 데이터</a>
        </div>
        <Card title="업로드 이력" bodyClassName="p-0">
          {uploads.length ? <div className="overflow-x-auto"><table className="w-full text-sm">
            <thead><tr className="border-b border-slate-200 text-left text-xs text-slate-500"><th className="px-5 py-2 font-medium">파일</th><th className="px-3 py-2 text-right font-medium">저장</th><th className="px-3 py-2 text-right font-medium">제외</th><th className="px-5 py-2 font-medium">업로드 시각</th></tr></thead>
            <tbody>{uploads.map(u => <tr key={u.id} className="border-b border-slate-100 last:border-0">
              <td className="px-5 py-2.5 text-slate-900">{u.file_name}</td><td className="px-3 py-2.5 text-right tabular-nums">{u.row_count}</td>
              <td className={cx('px-3 py-2.5 text-right tabular-nums', u.rejected_count ? 'text-amber-700' : 'text-slate-400')}>{u.rejected_count}</td>
              <td className="px-5 py-2.5 text-xs text-slate-500">{dateTimeKo(u.uploaded_at)}</td></tr>)}</tbody>
          </table></div> : <div className="p-5"><Empty title="아직 업로드한 파일이 없습니다" /></div>}
        </Card>
      </div>
      <Card title="파일 형식" subtitle="첫 행은 열 이름이어야 합니다. 한글 열 이름도 인식합니다." className="xl:col-span-2" bodyClassName="p-0">
        <table className="w-full text-sm"><tbody>{COLUMNS.map(([c, req, desc, ex]) => <tr key={c} className="border-b border-slate-100 align-top last:border-0">
          <td className="px-5 py-2.5"><code className="font-mono text-xs font-semibold text-slate-900">{c}</code><span className={cx('ml-1.5 text-[11px]', req === '필수' ? 'text-red-600' : 'text-slate-400')}>{req}</span></td>
          <td className="py-2.5 pr-5 text-xs text-slate-600">{desc}<span className="mt-0.5 block font-mono text-slate-400">예: {ex}</span></td></tr>)}</tbody></table>
      </Card>
    </div>
  </div>;
}
