import { useEffect, useState } from 'react';
import { request } from '../services/api';

const PAGE_SIZE = 5;
const dateText = (item) => {
  const value = item.published_at || item.observed_at;
  return value ? new Date(value).toLocaleString('ko-KR') : '날짜 정보 없음';
};
const safeLink = (url) => /^https?:\/\//i.test(url) ? url : undefined;

export default function StoredNewsView() {
  const [draft, setDraft] = useState({ q: '', source: '' });
  const [filters, setFilters] = useState({ q: '', source: '' });
  const [offset, setOffset] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [list, setList] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setList(null);
    setSelectedId(null);
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
    if (filters.q) params.set('q', filters.q);
    if (filters.source) params.set('source', filters.source);
    request(`/api/news?${params}`, { signal: controller.signal })
      .then(data => {
        if (!controller.signal.aborted) setList(data);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError('뉴스를 불러오지 못했습니다. 백엔드 연결을 확인하고 다시 시도해주세요.');
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [filters, offset, refresh]);

  useEffect(() => {
    setDetail(null);
    setDetailError('');
    if (!selectedId) return;
    const controller = new AbortController();
    request(`/api/news/${encodeURIComponent(selectedId)}`, { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setDetail(data); })
      .catch(() => { if (!controller.signal.aborted) setDetailError('기사를 불러오지 못했습니다. 삭제되었거나 서버에 연결할 수 없습니다.'); });
    return () => controller.abort();
  }, [selectedId]);

  function search(event) {
    event.preventDefault();
    setOffset(0);
    setFilters({ q: draft.q.trim(), source: draft.source.trim() });
  }

  return <section className="space-y-5" aria-labelledby="stored-news-title">
    <header>
      <p className="text-sm font-medium text-blue-700">dayribbon · 데이리본</p>
      <h1 id="stored-news-title" className="mt-1 text-2xl font-bold">수집된 뉴스</h1>
      <p className="mt-2 text-sm text-slate-600">DB에 저장된 실제 기사입니다. 자동 실시간 갱신·순위·감성 분석은 아직 제공하지 않습니다.</p>
    </header>
    <form onSubmit={search} className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4">
      <label className="flex-1 min-w-48 text-sm">제목 검색
        <input className="mt-1 block w-full rounded border border-slate-300 p-2" value={draft.q} maxLength={200} onChange={e => setDraft({ ...draft, q: e.target.value })} placeholder="검색어 입력" />
      </label>
      <label className="text-sm">출처 이름
        <input className="mt-1 block w-full rounded border border-slate-300 p-2" value={draft.source} maxLength={200} onChange={e => setDraft({ ...draft, source: e.target.value })} placeholder="예: BBC News (정확히 일치)" />
      </label>
      <button className="rounded bg-blue-700 px-4 py-2 text-white" type="submit">검색</button>
      <button className="rounded border border-slate-300 px-4 py-2" type="button" onClick={() => { setDraft({ q: '', source: '' }); setFilters({ q: '', source: '' }); setOffset(0); }}>초기화</button>
      <button className="rounded border border-slate-300 px-4 py-2" type="button" onClick={() => setRefresh(n => n + 1)}>목록 새로고침</button>
    </form>
    <p className="text-xs text-slate-500">최신순 · 새로고침은 저장된 목록을 다시 조회하며 외부 뉴스 수집을 실행하지 않습니다.</p>
    <div aria-live="polite" aria-busy={loading}>
      {loading && <p className="py-6">뉴스를 불러오는 중입니다…</p>}
      {error && <p role="alert" className="rounded border border-red-200 bg-red-50 p-4 text-red-800">{error}</p>}
      {!loading && list && <>
        <p className="mb-3 text-sm">검색 결과 {list.total}건</p>
        {list.items.length === 0 ? <p className="rounded-xl border bg-white p-6">표시할 기사가 없습니다. 검색 조건을 바꾸거나 이전 페이지로 이동해주세요.</p> :
          <ul className="divide-y rounded-xl border border-slate-200 bg-white">
            {list.items.map(item => <li key={item.article_id} className="p-5">
              <p className="mb-2 text-xs text-slate-500">{item.source} · {item.published_at ? '발행' : '관측'} {dateText(item)}</p>
              <button type="button" className="text-left font-semibold text-slate-900 hover:text-blue-700 hover:underline" onClick={() => setSelectedId(item.article_id)}>{item.title_ko || item.title}</button>
              <a href={safeLink(item.url)} target="_blank" rel="noopener noreferrer" className="ml-3 inline-block text-sm text-blue-700 underline">원문 보기 ↗</a>
              {item.title_ko && <p className="mt-1 text-sm text-slate-500"><span className="mr-1 rounded bg-slate-100 px-1 text-xs">기계 번역</span>원문: {item.title}</p>}
            </li>)}
          </ul>}
        <nav aria-label="뉴스 페이지" className="mt-4 flex items-center gap-4">
          <button type="button" className="rounded border px-4 py-2 disabled:opacity-40" disabled={offset === 0} onClick={() => setOffset(n => Math.max(0, n - PAGE_SIZE))}>이전</button>
          <span className="text-sm">{Math.floor(offset / PAGE_SIZE) + 1}페이지</span>
          <button type="button" className="rounded border px-4 py-2 disabled:opacity-40" disabled={offset + PAGE_SIZE >= list.total} onClick={() => setOffset(n => n + PAGE_SIZE)}>다음</button>
        </nav>
      </>}
    </div>
    {selectedId && <section aria-label="기사 상세" aria-live="polite" className="rounded-xl border border-blue-200 bg-white p-5">
      <button type="button" className="float-right text-sm underline" onClick={() => setSelectedId(null)}>상세 닫기</button>
      {!detail && !detailError && <p>상세 내용을 불러오는 중입니다…</p>}
      {detailError && <p role="alert">{detailError}</p>}
      {detail && <>
        <h2 className="pr-20 text-lg font-bold">{detail.title_ko || detail.title}</h2>
        {detail.title_ko && <p className="mt-1 text-sm text-slate-500">원문: {detail.title}</p>}
        <p className="mt-2 text-sm text-slate-500">{detail.source} · {detail.published_at ? '발행' : '관측'} {dateText(detail)}</p>
        <p className="my-4 text-sm">{detail.summary_ko || detail.summary || '제공된 요약문이 없습니다. 기사 내용은 원문에서 확인하세요.'}</p>
        {detail.summary_ko && <p className="mb-4 text-xs text-slate-500">DeepL 기계 번역 · 원문 요약: {detail.summary}</p>}
        <a className="text-blue-700 underline" href={safeLink(detail.url)} target="_blank" rel="noopener noreferrer">{detail.source} 원문 보기 ↗</a>
      </>}
    </section>}
  </section>;
}
