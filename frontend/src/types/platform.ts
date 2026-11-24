export type UserRole = 'GUEST' | 'ANALYST' | 'DATAOPS' | 'ADMIN';

export type AuthProvider = 'EMAIL' | 'KAKAO' | 'GOOGLE';

export type AppTab = 'bi' | 'dashboard' | 'news-sns' | 'doc-ai' | 'finance' | 'receipt-ocr' | 'dataops';

export type MarketRegime = 'BULL_MOMENTUM' | 'REGULATORY_ALERT' | 'MACRO_TIGHTENING';

export type TopicCategory =
  | '전체'
  | '가상자산'
  | '주식·금융'
  | 'AI·테크'
  | '정치·경제'
  | '소비자·유통';

export type ContentCategory = Exclude<TopicCategory, '전체'>;

export type SentimentType = '긍정' | '중립' | '부정';

export type TimeframeKey = '1D' | '1W' | '1M' | '1Y';

export interface UserAccount {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  provider: AuthProvider;
  department: string;
  avatarUrl?: string;
}

export interface TrendIssue {
  id: string;
  rank: number;
  prevRank: number;
  category: ContentCategory;
  relatedCategories: ContentCategory[];
  title: string;
  summary: string;
  sourceName: string;
  publishedAt: string;
  mentionCount: number;
  mentionGrowthPct: number;
  sentiment: SentimentType;
  positiveRatio: number;
  neutralRatio: number;
  negativeRatio: number;
  keywords: string[];
  panderaVerified: boolean;
  parquetPartition: string;
}

export interface SnsReaction {
  id: string;
  issueId: string;
  platform: 'X(트위터)' | '블라인드' | '레딧' | '네이버 종토방' | '텔레그램';
  authorHandle: string;
  content: string;
  sentiment: SentimentType;
  likes: number;
  replies: number;
  postedAt: string;
}

export interface HourlyMentionPoint {
  hour: string;
  newsCount: number;
  snsCount: number;
  positiveIdx: number;
  negativeIdx: number;
}

export interface AnalyzedDocument {
  id: string;
  fileName: string;
  fileType: 'PDF' | 'DOCX' | 'TXT';
  fileSizeKb: number;
  uploadedBy: string;
  uploadedAt: string;
  primaryCategory: string;
  relatedCategories: string[];
  mappedTopicCategory: ContentCategory;
  confidenceScores: { category: string; score: number }[];
  summary: string;
  extractedKeywords: string[];
  matchedIssueIds: string[];
  rawExcerpt: string;
  embeddingModel: string;
  classifierModel: string;
}

export interface SampleDocumentPreset {
  id: string;
  fileName: string;
  fileType: 'PDF' | 'DOCX' | 'TXT';
  fileSizeKb: number;
  description: string;
  rawText: string;
}

export interface PricePoint {
  label: string;
  price: number;
  ma7: number;
  volume: number;
  newsMentionSpike?: number;
  spikeEvent?: string;
}

export interface FinancialAsset {
  symbol: string;
  name: string;
  assetType: '가상자산' | '국내주식' | '해외주식';
  currency: 'KRW' | 'USD';
  currentPrice: number;
  change24hPct: number;
  volume24h: string;
  marketCap: string;
  volatility30d: number;
  linkedCategory: ContentCategory;
  linkedIssueIds: string[];
  series: Record<TimeframeKey, PricePoint[]>;
}

export interface ReceiptLineItem {
  id: string;
  name: string;
  quantity: number;
  unitPrice: number;
  amount: number;
}

export interface ReceiptRecord {
  id: string;
  merchantName: string;
  businessNo: string;
  transactionDate: string;
  category: '식비/접대비' | 'IT/사무용품' | '클라우드/구독' | '교통/출장';
  supplyAmount: number;
  vatAmount: number;
  totalAmount: number;
  paymentMethod: string;
  approvalNo: string;
  ocrConfidence: number;
  imageUrl?: string;
  rpaStatus: '대기' | 'RPA 입력완료' | '검증차단';
  registeredBy: string;
  registeredAt: string;
  items: ReceiptLineItem[];
}

export interface SampleReceiptPreset {
  id: string;
  label: string;
  imageUrl: string;
  merchantName: string;
  businessNo: string;
  transactionDate: string;
  category: '식비/접대비' | 'IT/사무용품' | '클라우드/구독' | '교통/출장';
  supplyAmount: number;
  vatAmount: number;
  totalAmount: number;
  paymentMethod: string;
  approvalNo: string;
  ocrConfidence: number;
  items: ReceiptLineItem[];
}

export interface AirflowDag {
  id: string;
  name: string;
  description: string;
  schedule: string;
  engine: string;
  lastRunAt: string;
  status: '성공' | '실행중' | '검증차단';
  rowsProcessed: number;
  duplicatesDropped: number;
  panderaPassed: boolean;
  targetTable: string;
}

export type GuardRuleType =
  | '@PreAuthorize'
  | '@PanderaSchemaCheck'
  | '@DeduplicationCheck'
  | '@OcrIntegrityCheck'
  | '@PlaywrightRpaSync';

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  guardRule: GuardRuleType;
  actorName: string;
  actorRole: UserRole;
  action: string;
  status: 'PASSED' | 'BLOCKED';
  message: string;
}

export interface MarketRegimeInfo {
  id: MarketRegime;
  label: string;
  shortDesc: string;
  focusCategory: ContentCategory;
  kospiIndex: string;
  btcKrw: string;
  etlThroughput: string;
}
