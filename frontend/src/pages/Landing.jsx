import React from 'react'
import { Link } from 'react-router-dom'

const FEATURES = [
  { icon: '🎯', title: 'No Learning', desc: 'BI 도구 학습 없이 기업 정보를 입력하고 데이터를 올리면 분석이 자동으로 준비됩니다.' },
  { icon: '📡', title: '자동 데이터 수집', desc: '환율·금리·원자재·뉴스 등 외부 시장 데이터를 기업 상황에 맞춰 선별 수집합니다.' },
  { icon: '🏭', title: '기업 맞춤 분석', desc: '업종, 제품, 거래처, 원자재 구성에 따라 분석 결과와 위험도가 달라집니다.' },
  { icon: '🚨', title: '선제적 위험 감지', desc: '질문하지 않아도 환율 급등·수익성 악화·핵심 뉴스 같은 위험을 자동 감지해 알립니다.' },
  { icon: '💡', title: '실행 가능한 인사이트', desc: '단순 지표 나열이 아니라 시나리오 계산과 대응 제안까지 제공합니다.' },
]

const PAIN = [
  '경영 대시보드를 만들 데이터 분석가가 없다',
  '엑셀 재무제표는 있지만 시장 환경과 연결되지 않는다',
  '환율·원자재 변동이 수익에 어떤 영향을 주는지 모른다',
  '중요한 산업 뉴스·정책 변화를 뒤늦게 알게 된다',
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-white">
      {/* 헤더 */}
      <header className="border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="text-xl font-bold text-brand-800">dayribbon</div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm text-slate-600 hover:text-brand-700 px-3 py-2">로그인</Link>
            <Link to="/login" className="text-sm bg-brand-600 text-white rounded-lg px-4 py-2 hover:bg-brand-700">데모 체험하기</Link>
          </div>
        </div>
      </header>

      {/* 히어로 */}
      <section className="bg-gradient-to-br from-brand-950 via-brand-900 to-brand-800 text-white">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <div className="inline-block bg-white/10 rounded-full px-3 py-1 text-xs mb-6">B2B SaaS 경영 분석 플랫폼 · 데모 버전</div>
          <h1 className="text-4xl md:text-5xl font-bold leading-tight mb-6">
            데이터 분석가 없이도<br />경영이 보이는 BI
          </h1>
          <p className="text-brand-200 text-lg max-w-2xl mb-8">
            dayribbon은 중소기업의 내부 재무 데이터와 외부 시장 데이터를 자동으로 연결해
            경영 현황, 성장 기회, 위험 요소를 분석합니다. 복잡한 BI 학습이나 프롬프트 작성 없이
            기업 정보를 입력하고 데이터를 올리면 분석이 시작됩니다.
          </p>
          <div className="flex gap-3">
            <Link to="/login" className="bg-white text-brand-800 font-semibold rounded-xl px-6 py-3 hover:bg-brand-50">데모 체험하기</Link>
            <a href="#how" className="border border-white/30 rounded-xl px-6 py-3 hover:bg-white/10">이용 방법 보기</a>
          </div>
          <div className="mt-6 text-xs text-brand-300">※ 본 데모의 모든 기업·시장 데이터는 가상이며, 분석은 규칙 기반 데모 엔진 결과입니다.</div>
        </div>
      </section>

      {/* 문제 */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-bold text-slate-900 mb-8">중소기업이 겪는 경영 분석의 어려움</h2>
        <div className="grid md:grid-cols-2 gap-4">
          {PAIN.map((p, i) => (
            <div key={i} className="flex gap-3 bg-slate-50 rounded-xl p-4 border border-slate-200">
              <span className="text-rose-500 font-bold">✕</span>
              <span className="text-slate-700 text-sm leading-relaxed">{p}</span>
            </div>
          ))}
        </div>
      </section>

      {/* 차별화 */}
      <section className="bg-slate-50 border-y border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="text-2xl font-bold text-slate-900 mb-3">범용 BI 도구와 무엇이 다른가</h2>
          <p className="text-slate-500 text-sm mb-8">Power BI·Tableau는 강력하지만, 직접 쿼리와 모델링, 차트 설계를 사용자가 해야 합니다. dayribbon은 그 과정을 시스템이 대신합니다.</p>
          <div className="grid md:grid-cols-3 gap-4">
            {[
              ['직접 만들지 않아도 됩니다', '차트·대시보드·분석식을 사용자가 설계할 필요가 없습니다.'],
              ['밖의 세상까지 봅니다', '내부 장부만이 아니라 환율·금리·뉴스·원자재까지 기업 맥락으로 해석합니다.'],
              ['위험을 먼저 알립니다', '사용자가 물어보기 전에 임계값 기반으로 위험을 감지하고 알림을 보냅니다.'],
            ].map(([t, d], i) => (
              <div key={i} className="bg-white rounded-xl p-5 border border-slate-200">
                <div className="text-brand-600 font-semibold mb-2">{t}</div>
                <div className="text-sm text-slate-600">{d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 핵심 기능 */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-bold text-slate-900 mb-8">핵심 기능</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f, i) => (
            <div key={i} className="rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow">
              <div className="text-2xl mb-3">{f.icon}</div>
              <div className="font-semibold text-slate-900 mb-1">{f.title}</div>
              <div className="text-sm text-slate-600 leading-relaxed">{f.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* 이용 방법 */}
      <section id="how" className="bg-slate-50 border-y border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="text-2xl font-bold text-slate-900 mb-8">이용 방법</h2>
          <div className="grid md:grid-cols-4 gap-4">
            {[
              ['1', '기업 정보 입력', '업종·제품·거래처·원자재·수출입 비중을 입력하면 맞춤형 분석 기준이 설정됩니다.'],
              ['2', '데이터 업로드', '월별 재무 Excel/CSV를 올리면 검증 후 경영지표에 자동 반영됩니다.'],
              ['3', '자동 분석', '내부 데이터 + 외부 시장 데이터가 결합되어 성장·방향성·위험 분석이 생성됩니다.'],
              ['4', '의사결정', '분석 결과를 검토하고 결정·후속 조치를 등록하면 월간 보고서로 정리됩니다.'],
            ].map(([n, t, d]) => (
              <div key={n} className="bg-white rounded-xl p-5 border border-slate-200">
                <div className="w-8 h-8 rounded-full bg-brand-600 text-white flex items-center justify-center font-bold mb-3">{n}</div>
                <div className="font-semibold text-slate-900 mb-1">{t}</div>
                <div className="text-sm text-slate-600">{d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* AI 분석 예시 */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-bold text-slate-900 mb-8">AI 경영 분석 예시</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {[
            ['성장 가능성', '매출 전년동기 +8.2%. 수출 비중 62% 환경에서 전장부품 수요 회복이 견인. 단기 성장 동력은 차량용 센서 모듈.'],
            ['사업 방향성', '원자재 비용 비중 55%. 수익률 최하위 제품의 단가 재검토와 웨이퍼 장기공급계약 확대를 제안.'],
            ['위험 요소', '원/달러 환율 +2.8% 급등. 외화 결제 비중 55% 기준 연간 수입 비용 약 1.6억원 증가 시나리오(가정 기반).'],
          ].map(([t, d], i) => (
            <div key={i} className="rounded-xl bg-brand-50 border border-brand-100 p-5">
              <div className="text-xs font-semibold text-brand-700 mb-2">{t}</div>
              <div className="text-sm text-slate-700 leading-relaxed">{d}</div>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400 mt-4">※ 예시 수치는 설명용이며 실제 분석 결과는 등록 데이터에 따라 달라집니다.</p>
      </section>

      {/* CTA */}
      <section className="bg-brand-950 text-white">
        <div className="max-w-6xl mx-auto px-6 py-16 text-center">
          <h2 className="text-2xl font-bold mb-3">지금 데모를 체험해 보세요</h2>
          <p className="text-brand-200 mb-6">데모 계정으로 OWNER/ADMIN/MEMBER/VIEWER 권한 차이까지 확인할 수 있습니다.</p>
          <Link to="/login" className="inline-block bg-white text-brand-900 font-semibold rounded-xl px-8 py-3 hover:bg-brand-50">데모 체험하기</Link>
        </div>
      </section>
      <footer className="bg-slate-900 text-slate-400 text-xs text-center py-6">
        dayribbon BI Demo · 모든 데이터는 가상 데모 데이터입니다 · 규칙 기반 분석 엔진 사용
      </footer>
    </div>
  )
}
