import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import {
  ANALYST_AVATAR_URL,
  INITIAL_AIRFLOW_DAGS,
  INITIAL_ANALYZED_DOCUMENTS,
  INITIAL_FINANCIAL_ASSETS,
  INITIAL_RECEIPT_RECORDS,
  INITIAL_SNS_REACTIONS,
  INITIAL_TREND_ISSUES,
  INITIAL_USERS,
  MARKET_REGIMES,
} from '../data/mockDb';
import {
  AirflowDag,
  AnalyzedDocument,
  AppTab,
  AuditLogEntry,
  AuthProvider,
  ContentCategory,
  FinancialAsset,
  GuardRuleType,
  MarketRegime,
  ReceiptRecord,
  SnsReaction,
  TopicCategory,
  TrendIssue,
  UserAccount,
  UserRole,
} from '../types/platform';

interface ToastNotification {
  id: string;
  guardRule: GuardRuleType;
  status: 'PASSED' | 'BLOCKED';
  title: string;
  message: string;
}

interface PlatformContextValue {
  activeTab: AppTab;
  setActiveTab: (tab: AppTab) => void;

  // Auth & RBAC
  users: UserAccount[];
  currentUser: UserAccount | null;
  effectiveRole: UserRole;
  authModalOpen: boolean;
  setAuthModalOpen: (open: boolean) => void;
  loginWithEmail: (email: string, password: string) => boolean;
  loginWithOAuth: (provider: Exclude<AuthProvider, 'EMAIL'>) => void;
  registerAccount: (name: string, email: string, department: string) => boolean;
  logout: () => void;
  switchRolePreview: (role: UserRole) => void;
  updateUserRole: (userId: string, role: UserRole) => void;

  // Market Regime (Dynamic Context)
  marketRegime: MarketRegime;
  setMarketRegime: (regime: MarketRegime) => void;

  // Personalization & History
  recentIssueIds: string[];
  recentAssetSymbols: string[];
  watchlistSymbols: string[];
  trackIssueClick: (issueId: string) => void;
  trackAssetView: (symbol: string) => void;
  toggleWatchlist: (symbol: string) => void;
  personalizedIssues: TrendIssue[];

  // Scenario A: News & SNS
  issues: TrendIssue[];
  snsReactions: SnsReaction[];
  selectedTopicCategory: TopicCategory;
  setSelectedTopicCategory: (cat: TopicCategory) => void;
  selectedIssueId: string;
  setSelectedIssueId: (id: string) => void;

  // Scenario B: AI Document Analysis
  analyzedDocs: AnalyzedDocument[];
  analyzeDocument: (params: {
    fileName: string;
    fileType: 'PDF' | 'DOCX' | 'TXT';
    fileSizeKb: number;
    rawText: string;
  }) => AnalyzedDocument | null;
  deleteAnalyzedDoc: (id: string) => void;

  // Scenario C: Finance
  financialAssets: FinancialAsset[];
  selectedAssetSymbol: string;
  setSelectedAssetSymbol: (symbol: string) => void;

  // Scenario D: Receipt OCR & RPA
  receipts: ReceiptRecord[];
  registerReceipt: (
    draft: Omit<ReceiptRecord, 'id' | 'registeredBy' | 'registeredAt' | 'rpaStatus'>
  ) => ReceiptRecord | null;
  runPlaywrightRpa: (receiptId: string) => boolean;

  // DataOps & Validation Engine
  dags: AirflowDag[];
  runAirflowDag: (dagId: string) => void;
  faultInjectionMode: boolean;
  setFaultInjectionMode: (enabled: boolean) => void;
  auditLogs: AuditLogEntry[];
  toasts: ToastNotification[];
  dismissToast: (id: string) => void;
}

const PlatformContext = createContext<PlatformContextValue | null>(null);

function nowTimestamp(): string {
  const d = new Date();
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');
  return `${hh}:${mm}:${ss}`;
}

function fullDateTime(): string {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  const da = String(d.getDate()).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${yyyy}-${mo}-${da} ${hh}:${mm}`;
}

export const PlatformProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeTab, setActiveTab] = useState<AppTab>('bi');
  const [users, setUsers] = useState<UserAccount[]>(INITIAL_USERS);
  const [currentUser, setCurrentUser] = useState<UserAccount | null>(INITIAL_USERS[0]);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  const [marketRegime, setMarketRegimeState] = useState<MarketRegime>('BULL_MOMENTUM');

  const [issues, setIssues] = useState<TrendIssue[]>(INITIAL_TREND_ISSUES);
  const [snsReactions] = useState<SnsReaction[]>(INITIAL_SNS_REACTIONS);
  const [selectedTopicCategory, setSelectedTopicCategory] = useState<TopicCategory>('가상자산');
  const [selectedIssueId, setSelectedIssueId] = useState<string>('iss-01');

  const [recentIssueIds, setRecentIssueIds] = useState<string[]>(['iss-01', 'iss-04']);
  const [recentAssetSymbols, setRecentAssetSymbols] = useState<string[]>(['BTC', '000660']);
  const [watchlistSymbols, setWatchlistSymbols] = useState<string[]>(['BTC', 'SOL', '000660']);

  const [analyzedDocs, setAnalyzedDocs] = useState<AnalyzedDocument[]>(INITIAL_ANALYZED_DOCUMENTS);
  const [financialAssets] = useState<FinancialAsset[]>(INITIAL_FINANCIAL_ASSETS);
  const [selectedAssetSymbol, setSelectedAssetSymbol] = useState<string>('BTC');
  const [receipts, setReceipts] = useState<ReceiptRecord[]>(INITIAL_RECEIPT_RECORDS);

  const [dags, setDags] = useState<AirflowDag[]>(INITIAL_AIRFLOW_DAGS);
  const [faultInjectionMode, setFaultInjectionMode] = useState<boolean>(false);

  const [toasts, setToasts] = useState<ToastNotification[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([
    {
      id: 'aud-01',
      timestamp: '19:20:04',
      guardRule: '@PanderaSchemaCheck',
      actorName: 'Airflow Scheduler',
      actorRole: 'DATAOPS',
      action: 'news_sns_crawler_dag 적재 검증',
      status: 'PASSED',
      message: '18,420건 스키마 검증 완료 (중복 1,248건 Polars 제거 후 TiDB 적재)',
    },
    {
      id: 'aud-02',
      timestamp: '19:25:00',
      guardRule: '@DeduplicationCheck',
      actorName: 'Airflow Scheduler',
      actorRole: 'DATAOPS',
      action: 'market_ohlcv_polars_dag 중복 검사',
      status: 'PASSED',
      message: 'DuckDB Parquet 파티션 무결성 확인 (중복 키 312건 필터링)',
    },
  ]);

  const effectiveRole: UserRole = currentUser ? currentUser.role : 'GUEST';

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const recordGuardEvent = useCallback(
    (
      guardRule: GuardRuleType,
      status: 'PASSED' | 'BLOCKED',
      action: string,
      message: string,
      actorOverride?: { name: string; role: UserRole }
    ) => {
      const id = `evt-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
      const actorName = actorOverride?.name ?? currentUser?.name ?? '비회원(Guest)';
      const actorRole = actorOverride?.role ?? (currentUser ? currentUser.role : 'GUEST');

      setAuditLogs((prev) => [
        {
          id,
          timestamp: nowTimestamp(),
          guardRule,
          actorName,
          actorRole,
          action,
          status,
          message,
        },
        ...prev.slice(0, 49),
      ]);

      setToasts((prev) => [
        {
          id,
          guardRule,
          status,
          title: action,
          message,
        },
        ...prev.slice(0, 2),
      ]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 4500);
    },
    [currentUser]
  );

  // Auth handlers
  const loginWithEmail = useCallback(
    (email: string, _password: string) => {
      const found = users.find((u) => u.email.toLowerCase() === email.trim().toLowerCase());
      if (found) {
        setCurrentUser(found);
        setAuthModalOpen(false);
        recordGuardEvent(
          '@PreAuthorize',
          'PASSED',
          '이메일 인증 로그인',
          `${found.name} (${found.role}) 세션 및 권한 토큰이 발급되었습니다.`,
          { name: found.name, role: found.role }
        );
        return true;
      }
      const created: UserAccount = {
        id: `usr-${Date.now()}`,
        name: email.split('@')[0] || '분석가',
        email: email.trim(),
        role: 'ANALYST',
        provider: 'EMAIL',
        department: '데이터 리서치팀',
        avatarUrl: ANALYST_AVATAR_URL,
      };
      setUsers((prev) => [...prev, created]);
      setCurrentUser(created);
      setAuthModalOpen(false);
      recordGuardEvent(
        '@PreAuthorize',
        'PASSED',
        '신규 계정 로그인',
        `${created.name} (ANALYST) 계정이 활성화되었습니다.`,
        { name: created.name, role: created.role }
      );
      return true;
    },
    [users, recordGuardEvent]
  );

  const loginWithOAuth = useCallback(
    (provider: Exclude<AuthProvider, 'EMAIL'>) => {
      const label = provider === 'KAKAO' ? '카카오 OAuth 2.0' : 'Google OAuth 2.0';
      const oauthUser: UserAccount = {
        id: `usr-oauth-${provider.toLowerCase()}`,
        name: provider === 'KAKAO' ? '박지민 (Kakao)' : '이도현 (Google)',
        email: provider === 'KAKAO' ? 'jimin.park@kakao.com' : 'dohyun.lee@gmail.com',
        role: provider === 'KAKAO' ? 'ANALYST' : 'DATAOPS',
        provider,
        department: provider === 'KAKAO' ? '투자 전략분석팀' : '데이터 엔지니어링팀',
        avatarUrl: ANALYST_AVATAR_URL,
      };
      setCurrentUser(oauthUser);
      setAuthModalOpen(false);
      recordGuardEvent(
        '@PreAuthorize',
        'PASSED',
        `${label} 원클릭 인증`,
        `${oauthUser.name} · ${oauthUser.role} 권한으로 인증되었습니다.`,
        { name: oauthUser.name, role: oauthUser.role }
      );
    },
    [recordGuardEvent]
  );

  const registerAccount = useCallback(
    (name: string, email: string, department: string) => {
      const newUser: UserAccount = {
        id: `usr-${Date.now()}`,
        name: name.trim(),
        email: email.trim(),
        role: 'ANALYST',
        provider: 'EMAIL',
        department: department.trim() || '데이터 분석팀',
        avatarUrl: ANALYST_AVATAR_URL,
      };
      setUsers((prev) => [...prev, newUser]);
      setCurrentUser(newUser);
      setAuthModalOpen(false);
      recordGuardEvent(
        '@PreAuthorize',
        'PASSED',
        '신규 회원가입 완료',
        `${newUser.name} (${newUser.department}) 계정이 TiDB 사용자 테이블에 등록되었습니다.`,
        { name: newUser.name, role: newUser.role }
      );
      return true;
    },
    [recordGuardEvent]
  );

  const logout = useCallback(() => {
    const prevName = currentUser?.name ?? '사용자';
    setCurrentUser(null);
    recordGuardEvent(
      '@PreAuthorize',
      'PASSED',
      '로그아웃 (비회원 전환)',
      `${prevName} 세션이 종료되어 Guest 읽기 전용 모드로 전환되었습니다.`,
      { name: '비회원(Guest)', role: 'GUEST' }
    );
  }, [currentUser, recordGuardEvent]);

  const switchRolePreview = useCallback(
    (role: UserRole) => {
      if (role === 'GUEST') {
        setCurrentUser(null);
        recordGuardEvent(
          '@PreAuthorize',
          'PASSED',
          '역할 시뮬레이션: 비회원(Guest)',
          '쓰기·문서분석·OCR 등록·파이프라인 실행이 차단되는 비회원 상태로 전환했습니다.',
          { name: '비회원(Guest)', role: 'GUEST' }
        );
        return;
      }
      const matched = users.find((u) => u.role === role) ?? users[0];
      const nextUser = { ...matched, role };
      setCurrentUser(nextUser);
      recordGuardEvent(
        '@PreAuthorize',
        'PASSED',
        `역할 시뮬레이션: ${role}`,
        `${nextUser.name} (${role}) 권한 컨텍스트가 즉시 적용되었습니다.`,
        { name: nextUser.name, role }
      );
    },
    [users, recordGuardEvent]
  );

  const updateUserRole = useCallback(
    (userId: string, role: UserRole) => {
      if (effectiveRole !== 'ADMIN') {
        recordGuardEvent(
          '@PreAuthorize',
          'BLOCKED',
          'RBAC 권한 변경 차단',
          '회원 권한 수정은 ADMIN 역할만 수행할 수 있습니다.'
        );
        return;
      }
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, role } : u)));
      if (currentUser?.id === userId) {
        setCurrentUser((prev) => (prev ? { ...prev, role } : prev));
      }
      recordGuardEvent(
        '@PreAuthorize',
        'PASSED',
        'RBAC 권한 정책 업데이트',
        `사용자 ID(${userId})의 역할이 ${role}로 변경되었습니다.`
      );
    },
    [effectiveRole, currentUser, recordGuardEvent]
  );

  const setMarketRegime = useCallback(
    (regime: MarketRegime) => {
      setMarketRegimeState(regime);
      const info = MARKET_REGIMES[regime];
      setSelectedTopicCategory(info.focusCategory);
      recordGuardEvent(
        '@PanderaSchemaCheck',
        'PASSED',
        '실시간 시장 국면 스트림 전환',
        `${info.label} — 추천 포커스가 '${info.focusCategory}' 영역으로 동기화되었습니다.`
      );
    },
    [recordGuardEvent]
  );

  const trackIssueClick = useCallback((issueId: string) => {
    setSelectedIssueId(issueId);
    setRecentIssueIds((prev) => [issueId, ...prev.filter((id) => id !== issueId)].slice(0, 6));
  }, []);

  const trackAssetView = useCallback((symbol: string) => {
    setSelectedAssetSymbol(symbol);
    setRecentAssetSymbols((prev) => [symbol, ...prev.filter((s) => s !== symbol)].slice(0, 5));
  }, []);

  const toggleWatchlist = useCallback(
    (symbol: string) => {
      if (effectiveRole === 'GUEST') {
        recordGuardEvent(
          '@PreAuthorize',
          'BLOCKED',
          '관심 종목 저장 차단',
          '관심 자산 북마크는 로그인한 사용자(ANALYST 이상)만 저장할 수 있습니다.'
        );
        setAuthModalOpen(true);
        return;
      }
      setWatchlistSymbols((prev) =>
        prev.includes(symbol) ? prev.filter((s) => s !== symbol) : [...prev, symbol]
      );
    },
    [effectiveRole, recordGuardEvent]
  );

  const personalizedIssues = useMemo(() => {
    const clickedCategories = new Set<ContentCategory>();
    recentIssueIds.forEach((id) => {
      const found = issues.find((i) => i.id === id);
      if (found) clickedCategories.add(found.category);
    });
    const regimeFocus = MARKET_REGIMES[marketRegime].focusCategory;
    clickedCategories.add(regimeFocus);

    return [...issues]
      .sort((a, b) => {
        const aBoost = (clickedCategories.has(a.category) ? 2 : 0) + (a.category === regimeFocus ? 1 : 0);
        const bBoost = (clickedCategories.has(b.category) ? 2 : 0) + (b.category === regimeFocus ? 1 : 0);
        if (aBoost !== bBoost) return bBoost - aBoost;
        return b.mentionGrowthPct - a.mentionGrowthPct;
      })
      .slice(0, 3);
  }, [issues, recentIssueIds, marketRegime]);

  // Scenario B: Document AI Classifier
  const analyzeDocument = useCallback(
    (params: {
      fileName: string;
      fileType: 'PDF' | 'DOCX' | 'TXT';
      fileSizeKb: number;
      rawText: string;
    }): AnalyzedDocument | null => {
      if (effectiveRole === 'GUEST') {
        recordGuardEvent(
          '@PreAuthorize',
          'BLOCKED',
          'AI 문서 분석 실행 차단',
          '문서 업로드 및 AI 임베딩 분석은 ANALYST 이상 로그인 계정이 필요합니다.'
        );
        setAuthModalOpen(true);
        return null;
      }

      if (faultInjectionMode) {
        recordGuardEvent(
          '@PanderaSchemaCheck',
          'BLOCKED',
          'Pandera 문서 메타데이터 검증 실패',
          '오류 주입 테스트 활성화 상태: file_encoding / token_count 필드 누락으로 적재가 차단되었습니다.'
        );
        return null;
      }

      const textLower = `${params.fileName} ${params.rawText}`.toLowerCase();

      let primaryCategory = '코인';
      let relatedCategories: string[] = ['정치·경제'];
      let mappedTopicCategory: ContentCategory = '가상자산';
      let confidenceScores = [
        { category: '코인 (가상자산)', score: 88 },
        { category: '정치·경제', score: 64 },
        { category: '주식·금융', score: 31 },
        { category: 'AI·테크', score: 12 },
      ];
      let extractedKeywords = ['가상자산', '법인계좌', '스테이블코인', '트래블룰', '금융위원회'];
      let summary =
        '가상자산 이용자 보호법 및 금융당국의 법인 실명계좌 단계적 허용 정책, 스테이블코인 준비금 100% 예치 규제 등 제도권 편입에 따른 시장 영향 분석 문서입니다.';
      let matchedIssueIds = ['iss-01', 'iss-02', 'iss-03', 'iss-09'];

      if (
        textLower.includes('반도체') ||
        textLower.includes('hbm') ||
        textLower.includes('ai') ||
        textLower.includes('nvidia') ||
        textLower.includes('sllm')
      ) {
        primaryCategory = 'AI·테크';
        relatedCategories = ['주식·금융'];
        mappedTopicCategory = 'AI·테크';
        confidenceScores = [
          { category: 'AI·테크', score: 86 },
          { category: '주식·금융', score: 69 },
          { category: '정치·경제', score: 24 },
          { category: '소비자·유통', score: 14 },
        ];
        extractedKeywords = ['HBM4', 'AI반도체', '패키징수율', '외국인수급', 'CAPEX'];
        summary =
          'AI 추론 서버 수요 확대에 따른 차세대 HBM4 양산 및 국내 반도체 대형주 밸류체인 수주 전망을 다룬 기술·산업 리포트입니다.';
        matchedIssueIds = ['iss-04', 'iss-05', 'iss-10'];
      } else if (
        textLower.includes('금리') ||
        textLower.includes('환율') ||
        textLower.includes('거시') ||
        textLower.includes('유통') ||
        textLower.includes('밸류업')
      ) {
        primaryCategory = '정치·경제';
        relatedCategories = ['주식·금융', '소비자·유통'];
        mappedTopicCategory = '정치·경제';
        confidenceScores = [
          { category: '정치·경제', score: 83 },
          { category: '주식·금융', score: 61 },
          { category: '소비자·유통', score: 45 },
          { category: '가상자산', score: 18 },
        ];
        extractedKeywords = ['원달러환율', '미국채금리', '환헤지', '마진방어', '거시경제'];
        summary =
          '미 국채 금리 및 원·달러 환율 변동성이 국내 수출 기업 환헤지 전략과 유통 업종 원가 구조에 미치는 영향을 분석한 거시경제 보고서입니다.';
        matchedIssueIds = ['iss-07', 'iss-05', 'iss-08'];
      }

      const newDoc: AnalyzedDocument = {
        id: `doc-${Date.now()}`,
        fileName: params.fileName,
        fileType: params.fileType,
        fileSizeKb: params.fileSizeKb,
        uploadedBy: currentUser?.name ?? '분석가',
        uploadedAt: fullDateTime(),
        primaryCategory,
        relatedCategories,
        mappedTopicCategory,
        confidenceScores,
        summary,
        extractedKeywords,
        matchedIssueIds,
        rawExcerpt: params.rawText.slice(0, 220) + (params.rawText.length > 220 ? '...' : ''),
        embeddingModel: 'Sentence-BERT (jhgan/ko-sroberta-multitask)',
        classifierModel: 'Scikit-learn CalibratedClassifierCV',
      };

      setAnalyzedDocs((prev) => [newDoc, ...prev]);
      recordGuardEvent(
        '@PanderaSchemaCheck',
        'PASSED',
        'AI 문서 분류 및 TiDB 적재 완료',
        `'${params.fileName}' → 대표 '${primaryCategory}', 관련 '${relatedCategories.join(', ')}' 판별 완료`
      );
      return newDoc;
    },
    [effectiveRole, faultInjectionMode, currentUser, recordGuardEvent]
  );

  const deleteAnalyzedDoc = useCallback(
    (id: string) => {
      if (effectiveRole === 'GUEST') {
        recordGuardEvent(
          '@PreAuthorize',
          'BLOCKED',
          '문서 이력 삭제 차단',
          '분석 이력 삭제는 로그인된 사용자만 수행할 수 있습니다.'
        );
        return;
      }
      setAnalyzedDocs((prev) => prev.filter((d) => d.id !== id));
      recordGuardEvent('@PanderaSchemaCheck', 'PASSED', '문서 분석 이력 삭제', `문서 ID(${id})가 삭제되었습니다.`);
    },
    [effectiveRole, recordGuardEvent]
  );

  // Scenario D: Receipt OCR Registration & Playwright RPA
  const registerReceipt = useCallback(
    (
      draft: Omit<ReceiptRecord, 'id' | 'registeredBy' | 'registeredAt' | 'rpaStatus'>
    ): ReceiptRecord | null => {
      if (effectiveRole === 'GUEST') {
        recordGuardEvent(
          '@PreAuthorize',
          'BLOCKED',
          '지출 내역 등록 차단',
          'OCR 영수증 전표 등록은 ANALYST 이상 로그인 계정이 필요합니다.'
        );
        setAuthModalOpen(true);
        return null;
      }

      if (faultInjectionMode) {
        recordGuardEvent(
          '@PanderaSchemaCheck',
          'BLOCKED',
          'Pandera 영수증 스키마 오류 차단',
          '오류 주입 테스트: 공급가액+부가세 합계 불일치 및 사업자번호 형식 오류로 등록이 거부되었습니다.'
        );
        return null;
      }

      if (!draft.merchantName.trim() || draft.totalAmount <= 0) {
        recordGuardEvent(
          '@OcrIntegrityCheck',
          'BLOCKED',
          '영수증 필수 필드 검증 실패',
          '가맹점명과 합계 금액(0원 초과)을 확인한 후 다시 등록해 주세요.'
        );
        return null;
      }

      const duplicate = receipts.find(
        (r) => r.approvalNo === draft.approvalNo && r.totalAmount === draft.totalAmount && draft.approvalNo !== ''
      );
      if (duplicate) {
        recordGuardEvent(
          '@DeduplicationCheck',
          'BLOCKED',
          '중복 영수증 승인번호 탐지',
          `승인번호 ${draft.approvalNo} (${draft.totalAmount.toLocaleString()}원)는 이미 ${duplicate.id}로 등록되어 있습니다.`
        );
        return null;
      }

      const created: ReceiptRecord = {
        ...draft,
        id: `EXP-2026-${Math.floor(1102 + Math.random() * 8800)}`,
        rpaStatus: '대기',
        registeredBy: currentUser?.name ?? '분석가',
        registeredAt: fullDateTime(),
      };

      setReceipts((prev) => [created, ...prev]);
      recordGuardEvent(
        '@OcrIntegrityCheck',
        'PASSED',
        '영수증 검증 및 지출 원장 등록',
        `${created.merchantName} · ${created.totalAmount.toLocaleString()}원 (OCR 신뢰도 ${created.ocrConfidence}%) TiDB 적재 완료`
      );
      return created;
    },
    [effectiveRole, faultInjectionMode, receipts, currentUser, recordGuardEvent]
  );

  const runPlaywrightRpa = useCallback(
    (receiptId: string) => {
      if (effectiveRole === 'GUEST') {
        recordGuardEvent(
          '@PreAuthorize',
          'BLOCKED',
          'Playwright RPA 실행 차단',
          'RPA 자동 전표 입력은 로그인한 ANALYST 또는 DATAOPS 권한이 필요합니다.'
        );
        setAuthModalOpen(true);
        return false;
      }

      setReceipts((prev) =>
        prev.map((r) => (r.id === receiptId ? { ...r, rpaStatus: 'RPA 입력완료' } : r))
      );
      recordGuardEvent(
        '@PlaywrightRpaSync',
        'PASSED',
        'Playwright ERP 전표 자동 입력 완료',
        `전표 ${receiptId}가 사내 회계 포털에 자동 기표 및 증빙 첨부 완료되었습니다.`
      );
      return true;
    },
    [effectiveRole, recordGuardEvent]
  );

  // DataOps Airflow DAG Trigger
  const runAirflowDag = useCallback(
    (dagId: string) => {
      if (effectiveRole !== 'DATAOPS' && effectiveRole !== 'ADMIN') {
        recordGuardEvent(
          '@PreAuthorize',
          'BLOCKED',
          'Airflow DAG 수동 실행 차단',
          `현재 역할(${effectiveRole})은 파이프라인 실행 권한이 없습니다. DATAOPS 또는 ADMIN으로 전환해 테스트하세요.`
        );
        return;
      }

      const targetDag = dags.find((d) => d.id === dagId);
      if (!targetDag) return;

      if (faultInjectionMode) {
        setDags((prev) =>
          prev.map((d) =>
            d.id === dagId ? { ...d, status: '검증차단', panderaPassed: false, lastRunAt: fullDateTime() } : d
          )
        );
        recordGuardEvent(
          '@PanderaSchemaCheck',
          'BLOCKED',
          `${targetDag.name} 파이프라인 중단`,
          'Pandera 스키마 계약 위반(null_rate > 0.05)이 감지되어 TiDB 적재를 롤백했습니다.'
        );
        return;
      }

      setDags((prev) =>
        prev.map((d) => (d.id === dagId ? { ...d, status: '실행중' } : d))
      );

      setTimeout(() => {
        const addedRows = Math.floor(420 + Math.random() * 1400);
        const dropped = Math.floor(12 + Math.random() * 65);
        setDags((prev) =>
          prev.map((d) =>
            d.id === dagId
              ? {
                  ...d,
                  status: '성공',
                  panderaPassed: true,
                  lastRunAt: fullDateTime(),
                  rowsProcessed: d.rowsProcessed + addedRows,
                  duplicatesDropped: d.duplicatesDropped + dropped,
                }
              : d
          )
        );

        if (dagId === 'dag-news-sns') {
          setIssues((prev) =>
            prev.map((iss, idx) =>
              idx < 3
                ? {
                    ...iss,
                    mentionCount: iss.mentionCount + Math.floor(80 + Math.random() * 210),
                  }
                : iss
            )
          );
        }

        recordGuardEvent(
          '@PanderaSchemaCheck',
          'PASSED',
          `${targetDag.name} 배치 실행 완료`,
          `신규 ${addedRows.toLocaleString()}건 처리 · 중복 ${dropped}건 제거 · ${targetDag.targetTable} 적재 성공`
        );
      }, 650);
    },
    [effectiveRole, dags, faultInjectionMode, recordGuardEvent]
  );

  const value: PlatformContextValue = {
    activeTab,
    setActiveTab,
    users,
    currentUser,
    effectiveRole,
    authModalOpen,
    setAuthModalOpen,
    loginWithEmail,
    loginWithOAuth,
    registerAccount,
    logout,
    switchRolePreview,
    updateUserRole,
    marketRegime,
    setMarketRegime,
    recentIssueIds,
    recentAssetSymbols,
    watchlistSymbols,
    trackIssueClick,
    trackAssetView,
    toggleWatchlist,
    personalizedIssues,
    issues,
    snsReactions,
    selectedTopicCategory,
    setSelectedTopicCategory,
    selectedIssueId,
    setSelectedIssueId,
    analyzedDocs,
    analyzeDocument,
    deleteAnalyzedDoc,
    financialAssets,
    selectedAssetSymbol,
    setSelectedAssetSymbol,
    receipts,
    registerReceipt,
    runPlaywrightRpa,
    dags,
    runAirflowDag,
    faultInjectionMode,
    setFaultInjectionMode,
    auditLogs,
    toasts,
    dismissToast,
  };

  return <PlatformContext.Provider value={value}>{children}</PlatformContext.Provider>;
};

export function usePlatform(): PlatformContextValue {
  const ctx = useContext(PlatformContext);
  if (!ctx) throw new Error('usePlatform must be used within PlatformProvider');
  return ctx;
}
