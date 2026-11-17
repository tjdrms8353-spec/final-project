import React, { useMemo, useRef, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { FileText, Trash2, Upload } from 'lucide-react';
import { usePlatform } from '../context/PlatformContext';
import { SAMPLE_DOCUMENT_PRESETS } from '../data/mockDb';
import { AnalyzedDocument } from '../types/platform';

export const DocumentAiView: React.FC = () => {
  const {
    analyzedDocs,
    analyzeDocument,
    deleteAnalyzedDoc,
    issues,
    snsReactions,
    setSelectedTopicCategory,
    trackIssueClick,
    setActiveTab,
  } = usePlatform();

  const [activeDocId, setActiveDocId] = useState<string>(analyzedDocs[0]?.id ?? '');
  const [isProcessing, setIsProcessing] = useState(false);
  const [customText, setCustomText] = useState('');
  const [customFileName, setCustomFileName] = useState('사용자_직접입력_문서.txt');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const activeDoc: AnalyzedDocument | undefined = useMemo(
    () => analyzedDocs.find((d) => d.id === activeDocId) ?? analyzedDocs[0],
    [analyzedDocs, activeDocId]
  );

  const matchedIssues = useMemo(() => {
    if (!activeDoc) return [];
    return issues.filter((iss) => activeDoc.matchedIssueIds.includes(iss.id));
  }, [activeDoc, issues]);

  const matchedReactions = useMemo(() => {
    const issueIds = new Set(matchedIssues.map((i) => i.id));
    return snsReactions.filter((r) => issueIds.has(r.issueId)).slice(0, 4);
  }, [matchedIssues, snsReactions]);

  const runAnalysisPipeline = (payload: {
    fileName: string;
    fileType: 'PDF' | 'DOCX' | 'TXT';
    fileSizeKb: number;
    rawText: string;
  }) => {
    setIsProcessing(true);
    setTimeout(() => {
      const result = analyzeDocument(payload);
      if (result) {
        setActiveDocId(result.id);
      }
      setIsProcessing(false);
    }, 550);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const ext = file.name.split('.').pop()?.toUpperCase();
    const fileType: 'PDF' | 'DOCX' | 'TXT' =
      ext === 'PDF' ? 'PDF' : ext === 'DOCX' || ext === 'DOC' ? 'DOCX' : 'TXT';
    const fileSizeKb = Math.max(12, Math.round(file.size / 1024));

    let text = '';
    if (fileType === 'TXT' || file.name.endsWith('.md') || file.name.endsWith('.csv')) {
      text = await file.text();
    } else {
      // Simulate PyMuPDF / python-docx extraction combined with filename context
      text = `${file.name} 문서 본문 추출 결과: 가상자산, 규제, 코인, AI 반도체 및 거시경제 지표를 포함한 분석 대상 텍스트입니다.`;
    }

    runAnalysisPipeline({
      fileName: file.name,
      fileType,
      fileSizeKb,
      rawText: text,
    });
    e.target.value = '';
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs font-medium text-blue-700 mb-1">
          시나리오 B · AI 문서 분석 및 유사 이슈 매칭
        </p>
        <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 text-balance">
          문서 자동 분류 및 연관 뉴스·SNS 반응 탐색
        </h1>
        <p className="text-sm text-slate-600 mt-1">
          PDF·DOCX·텍스트 문서를 업로드하면 PyMuPDF/python-docx 파싱 후 Sentence Transformers와 Scikit-learn으로 대표·관련 카테고리를 판별합니다.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 5 Cols: Uploader + Sample Presets + Saved History */}
        <div className="lg:col-span-5 space-y-6">
          <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
            <h2 className="font-display text-base font-semibold text-slate-900">
              분석 문서 업로드
            </h2>

            <div className="border border-dashed border-slate-300 rounded-xl p-6 text-center space-y-3 bg-slate-50/70">
              <Upload className="w-6 h-6 text-slate-500 mx-auto" />
              <div>
                <p className="text-xs font-medium text-slate-800">
                  PDF, DOCX, TXT 파일을 선택해 AI 분류 실행
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  예: 가상자산_규제_보고서.pdf 업로드 시 코인 · 정치·경제 자동 판별
                </p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx,.txt,.md,.csv"
                onChange={handleFileUpload}
                className="hidden"
              />
              <button
                type="button"
                disabled={isProcessing}
                onClick={() => fileInputRef.current?.click()}
                className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors cursor-pointer"
              >
                {isProcessing ? 'AI 임베딩 분석 중...' : '로컬 파일 선택'}
              </button>
            </div>

            {/* Sample Documents for One-Click Demo */}
            <div className="space-y-2 pt-2 border-t border-slate-200">
              <p className="text-xs font-semibold text-slate-700">
                원클릭 샘플 문서 테스트
              </p>
              <div className="space-y-2">
                {SAMPLE_DOCUMENT_PRESETS.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    disabled={isProcessing}
                    onClick={() =>
                      runAnalysisPipeline({
                        fileName: preset.fileName,
                        fileType: preset.fileType,
                        fileSizeKb: preset.fileSizeKb,
                        rawText: preset.rawText,
                      })
                    }
                    className="w-full text-left p-3 rounded-lg border border-slate-200 hover:border-blue-400 hover:bg-blue-50/40 transition-colors cursor-pointer flex items-start gap-3"
                  >
                    <FileText className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-semibold text-slate-900 truncate">
                          {preset.fileName}
                        </span>
                        <span className="text-[11px] font-mono tabular-nums text-slate-500 shrink-0">
                          {preset.fileType} · {preset.fileSizeKb}KB
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                        {preset.description}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Direct Text Input */}
            <div className="space-y-2 pt-2 border-t border-slate-200">
              <p className="text-xs font-semibold text-slate-700">텍스트 직접 입력 분석</p>
              <input
                type="text"
                value={customFileName}
                onChange={(e) => setCustomFileName(e.target.value)}
                className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
                placeholder="문서명.txt"
              />
              <textarea
                rows={3}
                value={customText}
                onChange={(e) => setCustomText(e.target.value)}
                placeholder="분석할 기사 본문이나 보고서 문단을 입력하세요 (예: 스테이블코인 규제 및 한국은행 통화정책)"
                className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
              />
              <button
                type="button"
                disabled={isProcessing || !customText.trim()}
                onClick={() =>
                  runAnalysisPipeline({
                    fileName: customFileName || '직접입력_리포트.txt',
                    fileType: 'TXT',
                    fileSizeKb: Math.max(4, Math.ceil(customText.length / 256)),
                    rawText: customText,
                  })
                }
                className="w-full py-2 px-4 text-xs font-medium text-slate-800 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 rounded-lg transition-colors cursor-pointer"
              >
                입력 텍스트 AI 분류 실행
              </button>
            </div>
          </section>

          {/* Saved Document History in TiDB */}
          <section className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-display text-sm font-semibold text-slate-900">
                분석 완료 문서 이력 (TiDB Cloud)
              </h3>
              <span className="text-xs font-mono tabular-nums text-slate-500">
                {analyzedDocs.length}건
              </span>
            </div>
            <div className="divide-y divide-slate-200">
              {analyzedDocs.map((doc) => (
                <div
                  key={doc.id}
                  className={`py-2.5 flex items-center justify-between gap-2 ${
                    activeDoc?.id === doc.id ? 'text-blue-700' : 'text-slate-800'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => setActiveDocId(doc.id)}
                    className="text-left min-w-0 flex-1 cursor-pointer"
                  >
                    <p className="text-xs font-semibold truncate">{doc.fileName}</p>
                    <p className="text-[11px] text-slate-500">
                      대표 {doc.primaryCategory} · 관련 {doc.relatedCategories.join(', ')} ·{' '}
                      <span className="font-mono tabular-nums">{doc.uploadedAt}</span>
                    </p>
                  </button>
                  <button
                    type="button"
                    onClick={() => deleteAnalyzedDoc(doc.id)}
                    aria-label={`${doc.fileName} 삭제`}
                    className="p-1.5 text-slate-400 hover:text-red-600 cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Right 7 Cols: Classification Result + Confidence Chart + Matched News & SNS */}
        <div className="lg:col-span-7 space-y-6">
          {!activeDoc ? (
            <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
              <p className="text-sm text-slate-600">
                좌측에서 샘플 문서를 선택하거나 파일을 업로드해 AI 분석을 시작하세요.
              </p>
            </div>
          ) : (
            <>
              <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-200 pb-4">
                  <div>
                    <div className="text-xs text-slate-500">
                      {activeDoc.fileType} · {activeDoc.fileSizeKb}KB · 업로더 {activeDoc.uploadedBy}
                    </div>
                    <h2 className="font-display text-xl font-bold text-slate-900 mt-0.5">
                      {activeDoc.fileName}
                    </h2>
                  </div>
                  <div className="text-xs text-slate-500 font-mono">
                    {activeDoc.embeddingModel}
                  </div>
                </div>

                {/* Primary & Related Categories */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                    <p className="text-xs text-slate-500">AI 판별 대표 카테고리</p>
                    <p className="font-display text-2xl font-bold text-blue-700 mt-1">
                      {activeDoc.primaryCategory}
                    </p>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
                    <p className="text-xs text-slate-500">연관 카테고리</p>
                    <p className="font-display text-xl font-bold text-slate-900 mt-1">
                      {activeDoc.relatedCategories.join(', ')}
                    </p>
                  </div>
                </div>

                {/* Summary & Keywords */}
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-slate-900">핵심 요약</h3>
                  <p className="text-sm text-slate-700 leading-relaxed">{activeDoc.summary}</p>
                  <p className="text-xs text-slate-500 pt-1">
                    추출 키워드: {activeDoc.extractedKeywords.join(' · ')}
                  </p>
                </div>

                {/* Confidence Score Chart */}
                <div className="space-y-2 pt-2 border-t border-slate-200">
                  <h3 className="text-sm font-semibold text-slate-900">
                    카테고리별 분류 신뢰도 (%)
                  </h3>
                  <div className="h-44 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={activeDoc.confidenceScores}
                        layout="vertical"
                        margin={{ top: 4, right: 20, left: 24, bottom: 0 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" horizontal={false} />
                        <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: '#64748B' }} />
                        <YAxis
                          type="category"
                          dataKey="category"
                          width={96}
                          tick={{ fontSize: 11, fill: '#334155' }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <Tooltip
                          formatter={(value) => [`${value}%`, '분류 확률']}
                          contentStyle={{
                            backgroundColor: '#FFFFFF',
                            borderColor: '#E2E8F0',
                            borderRadius: '8px',
                            fontSize: '12px',
                          }}
                        />
                        <Bar dataKey="score" fill="#2563EB" radius={[0, 4, 4, 0]} barSize={18} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </section>

              {/* Matched Related News & SNS Reactions */}
              <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-display text-base font-semibold text-slate-900">
                      문서 기반 연관 뉴스 및 SNS 반응
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Sentence-BERT 코사인 유사도 매칭 결과
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedTopicCategory(activeDoc.mappedTopicCategory);
                      setActiveTab('news-sns');
                    }}
                    className="text-xs font-semibold text-blue-700 hover:underline cursor-pointer whitespace-nowrap"
                  >
                    전체 {activeDoc.mappedTopicCategory} 피드 보기 →
                  </button>
                </div>

                <div className="divide-y divide-slate-200">
                  {matchedIssues.map((iss) => (
                    <div key={iss.id} className="py-3 first:pt-0 space-y-1">
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>
                          {iss.category} · {iss.sourceName}
                        </span>
                        <span className="font-mono tabular-nums text-emerald-700 font-semibold">
                          언급 {iss.mentionCount.toLocaleString()}건 (+{iss.mentionGrowthPct}%)
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedTopicCategory(iss.category);
                          trackIssueClick(iss.id);
                          setActiveTab('news-sns');
                        }}
                        className="text-left text-sm font-semibold text-slate-900 hover:text-blue-700 cursor-pointer"
                      >
                        {iss.title}
                      </button>
                    </div>
                  ))}
                </div>

                {matchedReactions.length > 0 && (
                  <div className="pt-3 border-t border-slate-200 space-y-2.5">
                    <h4 className="text-xs font-semibold text-slate-700">주요 SNS 반응 요약</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {matchedReactions.map((r) => (
                        <div
                          key={r.id}
                          className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1"
                        >
                          <div className="flex items-center justify-between text-[11px] text-slate-500">
                            <span className="font-semibold text-slate-700">
                              {r.platform} · {r.authorHandle}
                            </span>
                            <span>{r.sentiment}</span>
                          </div>
                          <p className="text-xs text-slate-700 leading-relaxed line-clamp-2">
                            {r.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
