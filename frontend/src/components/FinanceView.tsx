import React, { useMemo, useState } from 'react';
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Bookmark, Search } from 'lucide-react';
import { usePlatform } from '../context/PlatformContext';
import { TimeframeKey } from '../types/platform';

const ASSET_FILTERS = ['전체', '가상자산', '국내주식', '해외주식'] as const;
const TIMEFRAMES: TimeframeKey[] = ['1D', '1W', '1M', '1Y'];

function formatAssetPrice(value: number, currency: 'KRW' | 'USD'): string {
  if (currency === 'USD') return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
  return `${value.toLocaleString('ko-KR')}원`;
}

export const FinanceView: React.FC = () => {
  const {
    financialAssets,
    selectedAssetSymbol,
    trackAssetView,
    watchlistSymbols,
    toggleWatchlist,
    issues,
    trackIssueClick,
    setSelectedTopicCategory,
    setActiveTab,
  } = usePlatform();

  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<(typeof ASSET_FILTERS)[number]>('전체');
  const [timeframe, setTimeframe] = useState<TimeframeKey>('1W');
  const [showMa7, setShowMa7] = useState(true);

  const filteredAssets = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return financialAssets.filter((asset) => {
      const typeMatch = typeFilter === '전체' || asset.assetType === typeFilter;
      const queryMatch =
        !q ||
        asset.symbol.toLowerCase().includes(q) ||
        asset.name.toLowerCase().includes(q);
      return typeMatch && queryMatch;
    });
  }, [financialAssets, typeFilter, searchQuery]);

  const activeAsset = useMemo(
    () =>
      financialAssets.find((a) => a.symbol === selectedAssetSymbol) ??
      filteredAssets[0] ??
      financialAssets[0],
    [financialAssets, selectedAssetSymbol, filteredAssets]
  );

  const seriesData = activeAsset.series[timeframe];
  const spikePoints = useMemo(
    () => seriesData.filter((p) => p.spikeEvent),
    [seriesData]
  );

  const linkedIssues = useMemo(
    () => issues.filter((i) => activeAsset.linkedIssueIds.includes(i.id)),
    [issues, activeAsset]
  );

  const isWatchlisted = watchlistSymbols.includes(activeAsset.symbol);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-medium text-blue-700 mb-1">
          시나리오 C · 주식·가상자산 시세 및 뉴스 상관 분석
        </p>
        <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 text-balance">
          금융 자산 시계열 차트 및 이슈 상관 모니터링
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          종목이나 코인을 검색해 최근 시세, 이동평균선, 거래량 추이 및 뉴스·SNS 언급 급등 이벤트를 함께 분석합니다.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 4 Cols: Asset Directory & Search */}
        <div className="lg:col-span-4 space-y-4">
          <section className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="티커, 종목명 검색 (예: BTC, 하이닉스, NVDA)"
                className="w-full pl-8 pr-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>

            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg overflow-x-auto">
              {ASSET_FILTERS.map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setTypeFilter(f)}
                  className={`flex-1 px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    typeFilter === f
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>

            <div className="divide-y divide-slate-200">
              {filteredAssets.length === 0 ? (
                <p className="text-xs text-slate-500 py-6 text-center">
                  검색 조건에 맞는 자산이 없습니다.
                </p>
              ) : (
                filteredAssets.map((asset) => {
                  const active = asset.symbol === activeAsset.symbol;
                  const isUp = asset.change24hPct >= 0;
                  return (
                    <button
                      key={asset.symbol}
                      type="button"
                      onClick={() => trackAssetView(asset.symbol)}
                      className={`w-full text-left py-3 px-2 rounded-lg transition-colors flex items-center justify-between gap-2 cursor-pointer ${
                        active ? 'bg-blue-50/70' : 'hover:bg-slate-50'
                      }`}
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-bold text-slate-900 truncate">
                            {asset.name}
                          </span>
                        </div>
                        <p className="text-[11px] font-mono text-slate-500">
                          {asset.symbol} · {asset.assetType}
                        </p>
                      </div>

                      <div className="text-right font-mono tabular-nums shrink-0">
                        <p className="text-xs font-semibold text-slate-900">
                          {formatAssetPrice(asset.currentPrice, asset.currency)}
                        </p>
                        <p
                          className={`text-[11px] font-semibold ${
                            isUp ? 'text-emerald-700' : 'text-red-700'
                          }`}
                        >
                          {isUp ? '+' : ''}
                          {asset.change24hPct}%
                        </p>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </section>

          {/* Watchlist Panel */}
          <section className="bg-white border border-slate-200 rounded-xl p-4 space-y-2.5">
            <h3 className="text-xs font-semibold text-slate-800">내 관심 자산 (Watchlist)</h3>
            <div className="flex flex-wrap gap-2">
              {watchlistSymbols.length === 0 ? (
                <span className="text-xs text-slate-500">등록된 관심 자산이 없습니다.</span>
              ) : (
                watchlistSymbols.map((sym) => (
                  <button
                    key={sym}
                    type="button"
                    onClick={() => trackAssetView(sym)}
                    className={`px-2.5 py-1 text-xs font-mono font-medium rounded-md border transition-colors cursor-pointer ${
                      sym === activeAsset.symbol
                        ? 'bg-slate-900 text-white border-slate-900'
                        : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                    }`}
                  >
                    {sym}
                  </button>
                ))
              )}
            </div>
          </section>
        </div>

        {/* Right 8 Cols: Main Interactive Price + Volume Chart + Correlated Issues */}
        <div className="lg:col-span-8 space-y-6">
          <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-4">
              <div>
                <div className="text-xs text-slate-500">
                  {activeAsset.assetType} · {activeAsset.symbol} · 연관 섹터 {activeAsset.linkedCategory}
                </div>
                <div className="flex items-baseline gap-3 mt-1">
                  <h2 className="font-display text-2xl font-bold text-slate-900">
                    {activeAsset.name}
                  </h2>
                  <span className="font-mono tabular-nums text-xl font-bold text-slate-900">
                    {formatAssetPrice(activeAsset.currentPrice, activeAsset.currency)}
                  </span>
                  <span
                    className={`font-mono tabular-nums text-sm font-semibold ${
                      activeAsset.change24hPct >= 0 ? 'text-emerald-700' : 'text-red-700'
                    }`}
                  >
                    {activeAsset.change24hPct >= 0 ? '+' : ''}
                    {activeAsset.change24hPct}%
                  </span>
                </div>
              </div>

              <button
                type="button"
                onClick={() => toggleWatchlist(activeAsset.symbol)}
                className={`inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
                  isWatchlisted
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
                }`}
              >
                <Bookmark className="w-3.5 h-3.5" />
                <span>{isWatchlisted ? '관심 자산 저장됨' : '관심 자산 추가'}</span>
              </button>
            </div>

            {/* Key Metrics Row */}
            <div className="grid grid-cols-3 gap-4 text-xs">
              <div>
                <p className="text-slate-500">24시간 거래대금/량</p>
                <p className="font-mono tabular-nums text-sm font-semibold text-slate-900 mt-0.5">
                  {activeAsset.volume24h}
                </p>
              </div>
              <div>
                <p className="text-slate-500">시가총액</p>
                <p className="font-mono tabular-nums text-sm font-semibold text-slate-900 mt-0.5">
                  {activeAsset.marketCap}
                </p>
              </div>
              <div>
                <p className="text-slate-500">30일 변동성</p>
                <p className="font-mono tabular-nums text-sm font-semibold text-slate-900 mt-0.5">
                  {activeAsset.volatility30d}%
                </p>
              </div>
            </div>

            {/* Timeframe & MA Controls */}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="inline-flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
                {TIMEFRAMES.map((tf) => (
                  <button
                    key={tf}
                    type="button"
                    onClick={() => setTimeframe(tf)}
                    className={`px-3 py-1 text-xs font-mono font-medium rounded-md transition-colors cursor-pointer ${
                      timeframe === tf
                        ? 'bg-white text-slate-900 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>

              <label className="inline-flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showMa7}
                  onChange={(e) => setShowMa7(e.target.checked)}
                  className="rounded border-slate-300 text-blue-600 focus:ring-blue-600"
                />
                <span>7구간 이동평균선(MA7) 표시</span>
              </label>
            </div>

            {/* Price Chart */}
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={seriesData} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
                  <defs>
                    <linearGradient id="assetPriceFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.16} />
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 11, fill: '#64748B' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    domain={['auto', 'auto']}
                    tick={{ fontSize: 11, fill: '#64748B' }}
                    width={64}
                    tickFormatter={(v: number) =>
                      activeAsset.currency === 'USD'
                        ? `$${v}`
                        : v >= 1000000
                        ? `${Math.round(v / 10000).toLocaleString()}만`
                        : v.toLocaleString()
                    }
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    formatter={(val, name) => [
                      formatAssetPrice(Number(val ?? 0), activeAsset.currency),
                      String(name ?? ''),
                    ]}
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderColor: '#E2E8F0',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="price"
                    name="가격"
                    stroke="#2563EB"
                    strokeWidth={2}
                    fill="url(#assetPriceFill)"
                  />
                  {showMa7 && (
                    <Line
                      type="monotone"
                      dataKey="ma7"
                      name="이동평균(MA7)"
                      stroke="#64748B"
                      strokeWidth={1.5}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            {/* Volume Sub-Chart */}
            <div className="space-y-1.5 pt-2 border-t border-slate-200">
              <p className="text-xs font-medium text-slate-600">구간별 거래량 (DuckDB Parquet 집계)</p>
              <div className="h-24 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={seriesData} margin={{ top: 4, right: 12, left: 4, bottom: 0 }}>
                    <XAxis dataKey="label" hide />
                    <YAxis width={64} tick={{ fontSize: 10, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderColor: '#E2E8F0',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="volume" name="거래량 지수" fill="#94A3B8" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* News Mention Spike Events */}
            {spikePoints.length > 0 && (
              <div className="pt-3 border-t border-slate-200 space-y-2">
                <h3 className="text-xs font-semibold text-slate-800">
                  구간 내 뉴스·SNS 언급 급등 이벤트
                </h3>
                <div className="space-y-1.5">
                  {spikePoints.map((sp) => (
                    <div
                      key={sp.label}
                      className="flex items-center justify-between gap-3 text-xs py-1.5 px-3 bg-slate-50 rounded-lg border border-slate-200"
                    >
                      <span className="text-slate-800 font-medium">
                        <span className="font-mono text-slate-500 mr-2">{sp.label}</span>
                        {sp.spikeEvent}
                      </span>
                      <span className="font-mono tabular-nums text-blue-700 font-semibold shrink-0">
                        언급 {sp.newsMentionSpike?.toLocaleString()}건
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* Linked Issues Section */}
          <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-display text-base font-semibold text-slate-900">
                {activeAsset.name} 관련 최신 이슈
              </h3>
              <button
                type="button"
                onClick={() => {
                  setSelectedTopicCategory(activeAsset.linkedCategory);
                  setActiveTab('news-sns');
                }}
                className="text-xs font-semibold text-blue-700 hover:underline cursor-pointer"
              >
                뉴스·SNS 탭에서 전체 보기 →
              </button>
            </div>
            <div className="divide-y divide-slate-200">
              {linkedIssues.map((iss) => (
                <button
                  key={iss.id}
                  type="button"
                  onClick={() => {
                    setSelectedTopicCategory(iss.category);
                    trackIssueClick(iss.id);
                    setActiveTab('news-sns');
                  }}
                  className="w-full text-left py-3 first:pt-1 last:pb-0 hover:bg-slate-50 cursor-pointer space-y-1"
                >
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>
                      {iss.category} · {iss.sourceName}
                    </span>
                    <span className="font-mono tabular-nums text-emerald-700 font-semibold">
                      +{iss.mentionGrowthPct}%
                    </span>
                  </div>
                  <p className="text-sm font-semibold text-slate-900">{iss.title}</p>
                </button>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};
