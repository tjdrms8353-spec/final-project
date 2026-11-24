/** @license SPDX-License-Identifier: Apache-2.0 */
import { PlatformProvider, usePlatform } from './context/PlatformContext';
import { TopNavAndToolbar } from './components/TopNavAndToolbar';
import { AuthModal } from './components/AuthModal';
import { ValidationToasts } from './components/ValidationToasts';
import DashboardPage from './pages/DashboardPage.jsx';
import TrendPage from './pages/TrendPage.jsx';
import FinancePage from './pages/FinancePage.jsx';
import ReceiptPage from './pages/ReceiptPage.jsx';
import DocumentPage from './pages/DocumentPage.jsx';
import DataOpsPage from './pages/DataOpsPage.jsx';
import BiPage from './pages/BiPage.jsx';
const pages = { bi: BiPage, dashboard: DashboardPage, 'news-sns': TrendPage, 'doc-ai': DocumentPage, finance: FinancePage, 'receipt-ocr': ReceiptPage, dataops: DataOpsPage };
function Workspace() {
 const { activeTab } = usePlatform();
 const Page = pages[activeTab] || TrendPage;
 return <div className="min-h-screen bg-slate-50 text-slate-900">
   <TopNavAndToolbar />
   <div role="note" className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900">기업 BI·뉴스 목록은 실제 API·DB와 연결됩니다. 그 외 분석 미리보기·시세·AI·OCR·로그인·자동화는 데모이며 자동 실시간 갱신은 제공하지 않습니다.</div>
   <main className={activeTab === 'dashboard' ? '' : 'mx-auto max-w-[1440px] px-4 py-8 sm:px-6'}><Page /></main>
   <footer className="border-t border-slate-200 bg-white px-4 py-5 text-xs text-slate-600">
     <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4"><span>dayribbon · 중소기업 AI BI·의사결정 지원 플랫폼</span>
     <nav aria-label="기존 AutoFlow 화면" className="flex flex-wrap gap-4">
       <a href="/legacy/index.html" target="_blank" rel="noreferrer">기존 대시보드 ↗</a>
       <a href="/legacy/upload.html" target="_blank" rel="noreferrer">기존 문서 업로드 ↗</a>
       <a href="/legacy/history.html" target="_blank" rel="noreferrer">처리 이력 ↗</a>
       <a href="/legacy/admin_rpa.html" target="_blank" rel="noreferrer">기존 RPA ↗</a>
     </nav></div>
   </footer>
   <AuthModal /><ValidationToasts />
 </div>;
}
export default function App() { return <PlatformProvider><Workspace /></PlatformProvider>; }
