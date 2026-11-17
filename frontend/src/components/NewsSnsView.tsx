import React, { useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ArrowDownRight, ArrowUpRight, CheckCircle2, Search } from 'lucide-react';
import { usePlatform } from '../context/PlatformContext';
import { HOURLY_MENTION_SERIES, MARKET_REGIMES } from '../data/mockDb';
import { SentimentType, TopicCategory } from '../types/platform';

const CATEGORY_TABS: TopicCategory[] = [
  '전체',
  '가상자산',
  '주식·금융',
  'AI·테크',
  '정치·경제',
  '소비자·유통',
];

const SENTIMENT_OPTIONS: ('전체' | SentimentType)[] = ['전체', '긍정', '중립', '부정'];

export const NewsSnsView: React.FC = () => {
  const {
    issues,
    snsReactions,
    selectedTopicCategory,
    setSelectedTopicCategory,
    selectedIssueId,
    trackIssueClick,
    personalizedIssues,
    marketRegime,
    setActiveTab,
    trackAssetView,
  } = usePlatform();

  const [searchQuery, setSearchQuery] = useState('');
  const [sentimentFilter, setSentimentFilter] = useState<'전체' | SentimentType>('전체');
  const [sortBy, setSortBy] = useState<'growth' | 'mentions' | 'rank'>('rank');

  const regimeInfo = MARKET_REGIMES[marketRegime];

  const filteredIssues = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const list = issues.filter((item) => {
      const catMatch =
        selectedTopicCategory === '전체' ||
        item.category === selectedTopicCategory ||
        item.relatedCategories.includes(selectedTopicCategory);
      const sentMatch = sentimentFilter === '전체' || item.sentiment === sentimentFilter;
      const queryMatch =
        !q ||
        item.title.toLowerCase().includes(q) ||
        item.summary.toLowerCase().includes(q) ||
        item.keywords.some((k) => k.toLowerCase().includes(q));
      return catMatch && sentMatch && queryMatch;
    });

    return [...list].sort((a, b) => {
      if (sortBy === 'growth') return b.mentionGrowthPct - a.mentionGrowthPct;
      if (sortBy === 'mentions') return b.mentionCount - a.mentionCount;
      return a.rank - b.rank;
    });
  }, [issues, selectedTopicCategory, sentimentFilter, searchQuery, sortBy]);

  const activeIssue = useMemo(() => {
    return (
      filteredIssues.find((i) => i.id === selectedIssueId) ??
      filteredIssues[0] ??
      issues[0]
    );
  }, [filteredIssues, selectedIssueId, issues]);

  const linkedReactions = useMemo(() => {
    if (!activeIssue) return [];
    return snsReactions.filter((r) => r.issueId === activeIssue.id);
  }, [snsReactions, activeIssue]);

  const chartData =
    HOURLY_MENTION_SERIES[selectedTopicCategory] ?? HOURLY_MENTION_SERIES['전체'];

  const totalMentions = useMemo(
    () => filteredIssues.reduce((acc, cur) => acc + cur.mentionCount, 0),
    [filteredIssues]
  );

  const avgPositive = useMemo(() => {
    if (filteredIssues.length === 0) return 0;
    return Math.round(
      filteredIssues.reduce((acc, cur) => acc + cur.positiveRatio, 0) /
        filteredIssues.length
    );
  }, [filteredIssues]);

  return (
    <div className="space-y-6">
      {/* Page Title & Context Summary */}
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <p className="text-xs font-medium text-blue-700 mb-1">
            시나리오 A · 실시간 뉴스·SNS 통합 트렌드 분석
          </p>
          <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 text-balance">
            실시간 이슈 TOP 10 및 여론 감성 모니터링
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            {regimeInfo.shortDesc}
          </p>
        </div>

        {/* Summary KPI Strip (Tabular Numerals) */}
        <div className="grid grid-cols-3 gap-6 bg-white border border-slate-200 rounded-xl px-5 py-3 shrink-0">
          <div>
            <p className="text-xs text-slate-500">선택 영역 언급량</p>
            <p className="text-lg font-bold font-mono tabular-nums text-slate-900">
              {totalMentions.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500">평균 긍정 지수</p>
            <p className="text-lg font-bold font-mono tabular-nums text-emerald-700">
              {avgPositive}%
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500">검증된 이슈</p>
            <p className="text-lg font-bold font-mono tabular-nums text-slate-900">
              {filteredIssues.length}건
            </p>
          </div>
        </div>
      </div>

      {/* Category Filter Tabs + Search + Sentiment + Sort */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
          <div
            role="tablist"
            aria-label="주제 카테고리 필터"
            className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg overflow-x-auto"
          >
            {CATEGORY_TABS.map((cat) => (
              <button
                key={cat}
                type="button"
                role="tab"
                aria-selected={selectedTopicCategory === cat}
                onClick={() => setSelectedTopicCategory(cat)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  selectedTopicCategory === cat
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <div className="relative flex-1 sm:w-60">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="키워드, 종목, 이슈 검색"
                className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
            </div>

            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
              {SENTIMENT_OPTIONS.map((sent) => (
                <button
                  key={sent}
                  type="button"
                  onClick={() => setSentimentFilter(sent)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                    sentimentFilter === sent
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  {sent}
                </button>
              ))}
            </div>

            <select
              aria-label="정렬 기준"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'growth' | 'mentions' | 'rank')}
              className="px-3 py-1.5 text-xs font-medium border border-slate-300 rounded-lg bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="rank">종합 순위순</option>
              <option value="growth">언급량 급상승순</option>
              <option value="mentions">누적 언급량순</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main 2-Column Workspace: Left (Chart + TOP 10 List), Right (1:N Detail + SNS + Personalized) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 7 Cols */}
        <div className="lg:col-span-7 space-y-6">
          {/* Hourly Mention Volume Trend Chart */}
          <section className="bg-white border border-slate-200 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="font-display text-base font-semibold text-slate-900">
                  {selectedTopicCategory} 시간대별 뉴스·SNS 언급량 추이
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Polars 시간 단위 집계 · Parquet 파티션 기반 실시간 시계열
                </p>
              </div>
              <div className="flex items-center gap-4 text-xs text-slate-600">
                <span>파랑: SNS 언급</span>
                <span>슬레이트: 뉴스 기사</span>
              </div>
            </div>

            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 6, right: 8, left: -12, bottom: 0 }}>
                  <defs>
                    <linearGradient id="snsFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.18} />
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="hour" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderColor: '#E2E8F0',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="snsCount"
                    name="SNS 언급량"
                    stroke="#2563EB"
                    strokeWidth={2}
                    fill="url(#snsFill)"
                  />
                  <Area
                    type="monotone"
                    dataKey="newsCount"
                    name="뉴스 기사 수"
                    stroke="#475569"
                    strokeWidth={1.75}
                    fill="transparent"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* TOP 10 Issues Table / List */}
          <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
              <h2 className="font-display text-base font-semibold text-slate-900">
                급상승 이슈 랭킹 ({selectedTopicCategory})
              </h2>
              <span className="text-xs text-slate-500">항목 클릭 시 우측 1:N SNS 반응 조회</span>
            </div>

            {filteredIssues.length === 0 ? (
              <div className="p-10 text-center space-y-3">
                <p className="text-sm font-medium text-slate-700">
                  조건에 일치하는 이슈가 없습니다.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedTopicCategory('전체');
                    setSentimentFilter('전체');
                    setSearchQuery('');
                  }}
                  className="px-4 py-2 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 cursor-pointer"
                >
                  필터 초기화
                </button>
              </div>
            ) : (
              <div className="divide-y divide-slate-200">
                {filteredIssues.map((issue) => {
                  const isSelected = activeIssue?.id === issue.id;
                  const rankDiff = issue.prevRank - issue.rank;
                  const sentimentColor =
                    issue.sentiment === '긍정'
                      ? 'text-emerald-700'
                      : issue.sentiment === '부정'
                      ? 'text-red-700'
                      : 'text-slate-600';

                  return (
                    <button
                      key={issue.id}
                      type="button"
                      onClick={() => trackIssueClick(issue.id)}
                      className={`w-full text-left px-5 py-4 transition-colors cursor-pointer flex items-start gap-4 ${
                        isSelected ? 'bg-blue-50/60' : 'hover:bg-slate-50'
                      }`}
                    >
                      <div className="w-10 shrink-0 pt-0.5">
                        <span className="font-mono tabular-nums text-base font-bold text-slate-900">
                          {String(issue.rank).padStart(2, '0')}
                        </span>
                        <div className="flex items-center gap-0.5 text-[11px] font-mono tabular-nums mt-0.5">
                          {rankDiff > 0 ? (
                            <span className="text-emerald-600 flex items-center">
                              <ArrowUpRight className="w-3 h-3" />
                              {rankDiff}
                            </span>
                          ) : rankDiff < 0 ? (
                            <span className="text-red-600 flex items-center">
                              <ArrowDownRight className="w-3 h-3" />
                              {Math.abs(rankDiff)}
                            </span>
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </div>
                      </div>

                      <div className="flex-1 min-w-0 space-y-1.5">
                        {/* Unboxed Metadata with typographic separators */}
                        <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
                          <span className="font-medium text-slate-700">{issue.category}</span>
                          <span aria-hidden="true">·</span>
                          <span>{issue.sourceName}</span>
                          <span aria-hidden="true">·</span>
                          <span className="font-mono tabular-nums">{issue.publishedAt}</span>
                          <span aria-hidden="true">·</span>
                          <span className={`font-medium ${sentimentColor}`}>
                            여론 {issue.sentiment}
                          </span>
                        </div>

                        <h3 className="text-sm font-semibold text-slate-900 leading-snug">
                          {issue.title}
                        </h3>

                        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs text-slate-500">
                          <span>{issue.keywords.join(' · ')}</span>
                          <div className="flex items-center gap-3 font-mono tabular-nums shrink-0">
                            <span className="text-slate-700 font-medium">
                              {issue.mentionCount.toLocaleString()}건
                            </span>
                            <span className="text-emerald-700 font-semibold">
                              +{issue.mentionGrowthPct}%
                            </span>
                          </div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </section>
        </div>

        {/* Right 5 Cols: Selected Issue Detail + 1:N SNS Reactions + Personalized Insights */}
        <div className="lg:col-span-5 space-y-6">
          {activeIssue && (
            <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-5">
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2 text-xs text-slate-500">
                  <span>
                    이슈 상세 · {activeIssue.category} / {activeIssue.relatedCategories.join(', ')}
                  </span>
                  <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Pandera 검증 완료
                  </span>
                </div>
                <h2 className="font-display text-lg font-bold text-slate-900 leading-snug">
                  {activeIssue.title}
                </h2>
                <p className="text-sm text-slate-600 leading-relaxed">{activeIssue.summary}</p>
              </div>

              {/* Sentiment Distribution Bar */}
              <div className="space-y-1.5 pt-2 border-t border-slate-200">
                <div className="flex items-center justify-between text-xs text-slate-600">
                  <span>감성 분석 분포</span>
                  <span className="font-mono tabular-nums">
                    긍정 {activeIssue.positiveRatio}% · 중립 {activeIssue.neutralRatio}% · 부정{' '}
                    {activeIssue.negativeRatio}%
                  </span>
                </div>
                <div className="h-2 w-full rounded-full overflow-hidden flex bg-slate-100">
                  <div
                    style={{ width: `${activeIssue.positiveRatio}%` }}
                    className="bg-emerald-600"
                  />
                  <div
                    style={{ width: `${activeIssue.neutralRatio}%` }}
                    className="bg-slate-400"
                  />
                  <div
                    style={{ width: `${activeIssue.negativeRatio}%` }}
                    className="bg-red-600"
                  />
                </div>
              </div>

              {/* Data Lineage Metadata */}
              <div className="py-2.5 px-3 bg-slate-50 rounded-lg text-xs text-slate-600 flex flex-wrap items-center justify-between gap-2">
                <span>Parquet 파티션: <code className="font-mono text-slate-800">{activeIssue.parquetPartition}</code></span>
                {activeIssue.category === '가상자산' && (
                  <button
                    type="button"
                    onClick={() => {
                      trackAssetView('BTC');
                      setActiveTab('finance');
                    }}
                    className="text-blue-700 font-semibold hover:underline cursor-pointer whitespace-nowrap"
                  >
                    BTC 시세 연계 보기 →
                  </button>
                )}
              </div>

              {/* 1:N SNS Reactions Feed */}
              <div className="space-y-3 pt-2 border-t border-slate-200">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-900">
                    연결된 SNS 반응 및 댓글 (TiDB 1:N)
                  </h3>
                  <span className="text-xs font-mono tabular-nums text-slate-500">
                    {linkedReactions.length}건
                  </span>
                </div>

                {linkedReactions.length === 0 ? (
                  <p className="text-xs text-slate-500 py-4 text-center">
                    수집된 세부 SNS 댓글이 없습니다.
                  </p>
                ) : (
                  <div className="divide-y divide-slate-200">
                    {linkedReactions.map((post) => (
                      <div key={post.id} className="py-3 first:pt-0 last:pb-0 space-y-1.5">
                        <div className="flex items-center justify-between text-xs text-slate-500">
                          <span className="font-medium text-slate-800">
                            {post.platform} · {post.authorHandle}
                          </span>
                          <span className="font-mono tabular-nums">
                            {post.postedAt} · {post.sentiment}
                          </span>
                        </div>
                        <p className="text-xs text-slate-700 leading-relaxed">{post.content}</p>
                        <div className="text-[11px] font-mono tabular-nums text-slate-500">
                          공감 {post.likes} · 답글 {post.replies}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>
          )}

          {/* User Activity Based Personalized Recommendations */}
          <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <div>
              <h3 className="font-display text-sm font-semibold text-slate-900">
                조회 이력 기반 맞춤 이슈 추천
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                최근 클릭한 주제 및 현재 시장 국면({regimeInfo.label}) 반영
              </p>
            </div>

            <div className="divide-y divide-slate-200">
              {personalizedIssues.map((rec) => (
                <button
                  key={rec.id}
                  type="button"
                  onClick={() => trackIssueClick(rec.id)}
                  className="w-full text-left py-3 first:pt-1 last:pb-0 hover:bg-slate-50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>
                      {rec.category} · {rec.sourceName}
                    </span>
                    <span className="font-mono tabular-nums text-emerald-700 font-semibold">
                      +{rec.mentionGrowthPct}%
                    </span>
                  </div>
                  <p className="text-xs font-semibold text-slate-900 mt-1 line-clamp-1">
                    {rec.title}
                  </p>
                </button>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};
