import React, { useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Database, Play, Shield } from 'lucide-react';
import { usePlatform } from '../context/PlatformContext';
import { UserRole } from '../types/platform';

const SCHEMA_RELATIONS = [
  {
    parent: 'trend_issues',
    child: 'sns_reactions',
    fk: 'issue_id',
    engine: 'TiDB Cloud · SQLAlchemy',
    note: '실시간 뉴스·트렌드 이슈 1건당 다수의 SNS 게시글·댓글 1:N 매핑',
  },
  {
    parent: 'analyzed_documents',
    child: 'document_matched_issues',
    fk: 'document_id',
    engine: 'Sentence-BERT · TiDB Cloud',
    note: '업로드 문서 1건당 대표/관련 카테고리 및 유사 이슈 매칭 이력 저장',
  },
  {
    parent: 'financial_assets',
    child: 'financial_price_points',
    fk: 'symbol',
    engine: 'DuckDB · Parquet · Polars',
    note: '주식·코인 종목별 시간대별 OHLCV 시계열 및 뉴스 언급 스파이크 연계',
  },
  {
    parent: 'receipt_records',
    child: 'receipt_line_items',
    fk: 'receipt_id',
    engine: 'Tesseract OCR · Playwright RPA',
    note: '영수증 전표 헤더와 다중 구매 품목(1:N) 검증 후 ERP 전표 자동 입력',
  },
];

export const DataOpsConsoleView: React.FC = () => {
  const {
    dags,
    runAirflowDag,
    faultInjectionMode,
    setFaultInjectionMode,
    auditLogs,
    users,
    updateUserRole,
    effectiveRole,
    issues,
    analyzedDocs,
    receipts,
  } = usePlatform();

  const [logFilter, setLogFilter] = useState<'전체' | 'PASSED' | 'BLOCKED'>('전체');

  const totalRowsProcessed = useMemo(
    () => dags.reduce((acc, d) => acc + d.rowsProcessed, 0),
    [dags]
  );

  const totalDuplicatesDropped = useMemo(
    () => dags.reduce((acc, d) => acc + d.duplicatesDropped, 0),
    [dags]
  );

  const filteredLogs = useMemo(() => {
    if (logFilter === '전체') return auditLogs;
    return auditLogs.filter((l) => l.status === logFilter);
  }, [auditLogs, logFilter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div>
          <p className="text-xs font-medium text-blue-700 mb-1">
            데이터 엔지니어링 · 파이프라인 거버넌스 및 RBAC 콘솔
          </p>
          <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 text-balance">
            ETL 파이프라인 · Pandera 검증 및 권한 관리
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Airflow DAG 배치 실행, Pandera 스키마 오류 주입 시뮬레이션, TiDB 1:N 관계형 구조 및 실시간 감사 로그를 제어합니다.
          </p>
        </div>

        {/* Pandera Fault Injection Simulator */}
        <div className="bg-white border border-slate-200 rounded-xl px-4 py-3 flex items-center gap-4 shrink-0">
          <div className="text-xs">
            <p className="font-semibold text-slate-900">Pandera 오류 주입 테스트</p>
            <p className="text-slate-500">활성화 시 스키마 불일치 요청을 즉시 차단합니다.</p>
          </div>
          <button
            type="button"
            onClick={() => setFaultInjectionMode(!faultInjectionMode)}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer whitespace-nowrap ${
              faultInjectionMode
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            }`}
          >
            {faultInjectionMode ? '오류 주입 활성 (차단 중)' : '정상 검증 모드'}
          </button>
        </div>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <p className="text-xs text-slate-500">누적 ETL 처리 행수</p>
          <p className="font-mono tabular-nums text-2xl font-bold text-slate-900 mt-1">
            {totalRowsProcessed.toLocaleString()}
          </p>
          <p className="text-xs text-slate-500 mt-1">Polars · DuckDB Parquet</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <p className="text-xs text-slate-500">자동 중복 제거 건수</p>
          <p className="font-mono tabular-nums text-2xl font-bold text-emerald-700 mt-1">
            {totalDuplicatesDropped.toLocaleString()}
          </p>
          <p className="text-xs text-slate-500 mt-1">Pandera 무결성 필터링</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <p className="text-xs text-slate-500">적재 이슈 · 분석 문서</p>
          <p className="font-mono tabular-nums text-2xl font-bold text-slate-900 mt-1">
            {issues.length} / {analyzedDocs.length}
          </p>
          <p className="text-xs text-slate-500 mt-1">TiDB Cloud 저장 기준</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <p className="text-xs text-slate-500">OCR 등록 지출 전표</p>
          <p className="font-mono tabular-nums text-2xl font-bold text-slate-900 mt-1">
            {receipts.length}건
          </p>
          <p className="text-xs text-slate-500 mt-1">Playwright RPA 연계 대상</p>
        </div>
      </div>

      {/* Airflow DAG Pipeline Monitor */}
      <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h2 className="font-display text-base font-semibold text-slate-900">
              Apache Airflow ETL & 자동화 DAG 스케줄러
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              수동 실행은 DATAOPS 또는 ADMIN 권한이 필요합니다 (현재 역할: {effectiveRole}).
            </p>
          </div>
          <span className="text-xs text-slate-500">
            계획 스택: Airflow · Polars · DuckDB · Playwright
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-600 border-b border-slate-200">
              <tr>
                <th className="text-left px-5 py-3 font-medium">DAG 식별자 · 설명</th>
                <th className="text-left px-4 py-3 font-medium">처리 엔진</th>
                <th className="text-left px-4 py-3 font-medium">적재 테이블</th>
                <th className="text-right px-4 py-3 font-medium">누적 처리 / 중복제거</th>
                <th className="text-left px-4 py-3 font-medium">상태</th>
                <th className="text-right px-5 py-3 font-medium">실행</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {dags.map((dag) => (
                <tr key={dag.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3.5">
                    <p className="font-mono font-semibold text-slate-900">{dag.name}</p>
                    <p className="text-slate-600 mt-0.5">{dag.description}</p>
                    <p className="text-[11px] font-mono tabular-nums text-slate-400 mt-0.5">
                      {dag.schedule} · 최근 실행 {dag.lastRunAt}
                    </p>
                  </td>
                  <td className="px-4 py-3.5 text-slate-700 whitespace-nowrap">{dag.engine}</td>
                  <td className="px-4 py-3.5 font-mono text-slate-600 whitespace-nowrap">
                    {dag.targetTable}
                  </td>
                  <td className="px-4 py-3.5 text-right font-mono tabular-nums text-slate-800 whitespace-nowrap">
                    {dag.rowsProcessed.toLocaleString()} / {dag.duplicatesDropped.toLocaleString()}
                  </td>
                  <td className="px-4 py-3.5 whitespace-nowrap">
                    <span
                      className={`font-semibold ${
                        dag.status === '성공'
                          ? 'text-emerald-700'
                          : dag.status === '실행중'
                          ? 'text-blue-700'
                          : 'text-red-700'
                      }`}
                    >
                      {dag.status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-right whitespace-nowrap">
                    <button
                      type="button"
                      disabled={dag.status === '실행중'}
                      onClick={() => runAirflowDag(dag.id)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 rounded-md transition-colors cursor-pointer"
                    >
                      <Play className="w-3 h-3" />
                      <span>{dag.status === '실행중' ? '실행 중' : 'DAG 실행'}</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* TiDB 1:N Schema & RBAC User Management */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* TiDB Cloud 1:N Schema */}
        <section className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-blue-700" />
            <h2 className="font-display text-base font-semibold text-slate-900">
              TiDB Cloud · SQLAlchemy 1:N 데이터 모델
            </h2>
          </div>

          <div className="divide-y divide-slate-200">
            {SCHEMA_RELATIONS.map((rel) => (
              <div key={rel.parent} className="py-3 first:pt-1 last:pb-0 space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono font-semibold text-slate-900">
                    {rel.parent} (1) → {rel.child} (N)
                  </span>
                  <span className="font-mono text-slate-500">FK: {rel.fk}</span>
                </div>
                <p className="text-xs text-slate-600">{rel.note}</p>
                <p className="text-[11px] font-mono text-slate-400">{rel.engine}</p>
              </div>
            ))}
          </div>
        </section>

        {/* RBAC User Management */}
        <section className="lg:col-span-6 bg-white border border-slate-200 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-blue-700" />
              <h2 className="font-display text-base font-semibold text-slate-900">
                RBAC 사용자 권한 정책 관리
              </h2>
            </div>
            <span className="text-xs text-slate-500">변경은 ADMIN 역할만 허용</span>
          </div>

          <div className="divide-y divide-slate-200">
            {users.map((u) => (
              <div key={u.id} className="py-3 first:pt-1 last:pb-0 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-slate-900">
                    {u.name} · <span className="text-slate-500 font-normal">{u.department}</span>
                  </p>
                  <p className="text-[11px] font-mono text-slate-500 truncate">
                    {u.email} ({u.provider})
                  </p>
                </div>

                <select
                  aria-label={`${u.name} 역할 변경`}
                  value={u.role}
                  onChange={(e) => updateUserRole(u.id, e.target.value as UserRole)}
                  className="px-2.5 py-1.5 text-xs font-mono border border-slate-300 rounded-md bg-white text-slate-800"
                >
                  <option value="ANALYST">ANALYST</option>
                  <option value="DATAOPS">DATAOPS</option>
                  <option value="ADMIN">ADMIN</option>
                </select>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Real-time Validation & Security Audit Log */}
      <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="font-display text-base font-semibold text-slate-900">
              실시간 검증 및 보안 감사 로그 (FastAPI · Pandera Interceptor)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              권한 검사, 스키마 검증, 중복 차단 및 RPA 동기화 내역이 실시간 기록됩니다.
            </p>
          </div>

          <div className="inline-flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
            {(['전체', 'PASSED', 'BLOCKED'] as const).map((status) => (
              <button
                key={status}
                type="button"
                onClick={() => setLogFilter(status)}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                  logFilter === status
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {status}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-slate-200 max-h-96 overflow-y-auto">
          {filteredLogs.map((log) => (
            <div key={log.id} className="px-5 py-3 flex items-start justify-between gap-4 text-xs">
              <div className="flex items-start gap-2.5 min-w-0">
                {log.status === 'PASSED' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                )}
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono font-semibold text-slate-900">
                      {log.guardRule}
                    </span>
                    <span className="font-semibold text-slate-800">{log.action}</span>
                    <span
                      className={`font-semibold ${
                        log.status === 'PASSED' ? 'text-emerald-700' : 'text-red-700'
                      }`}
                    >
                      [{log.status}]
                    </span>
                  </div>
                  <p className="text-slate-600 mt-0.5">{log.message}</p>
                </div>
              </div>
              <div className="text-right font-mono tabular-nums text-[11px] text-slate-500 shrink-0">
                <p>{log.timestamp}</p>
                <p>
                  {log.actorName} ({log.actorRole})
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
