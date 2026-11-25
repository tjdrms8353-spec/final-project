"""데모 데이터 시드 — 가상의 반도체 부품 제조기업 '한빛세미텍'"""
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import (
    AnalysisResult, Company, CustomerMonthly, Decision, FinancialMonthly,
    FollowUp, MarketSeries, MaterialPurchase, NewsItem, Notification,
    NotificationSetting, ProductMonthly, Report, RiskAlert, User,
)
from .security import hash_password
from .utils import month_range, prev_month

random.seed(20261125)

PRODUCTS = ["파워 반도체 패키지", "아날로그 IC 서브스트레이트", "차량용 센서 모듈"]
CUSTOMERS = [
    ("국내 전장부품 A사", "한국"), ("국내 전장부품 B사", "한국"),
    ("해외 디스플레이 모듈 C사", "베트남"), ("해외 산업용 D사", "독일"),
    ("국내 가전 부품 E사", "한국"),
]
MATERIALS = ["실리콘 웨이퍼", "동박(Cu)", "에폭시 수지"]

SERIES = [
    ("USD_KRW", "원/달러 환율", "원", "(데모) 외환 시세 생성"),
    ("BASE_RATE", "한국 기준금리", "%", "(데모) 통화정책 생성"),
    ("FED_RATE", "미국 기준금리", "%", "(데모) 통화정책 생성"),
    ("KOSPI", "코스피 지수", "pt", "(데모) 주식지수 생성"),
    ("NASDAQ", "나스닥 지수", "pt", "(데모) 주식지수 생성"),
    ("SEMI_ETF", "반도체 ETF 지수", "pt", "(데모) 업종지수 생성"),
    ("WTI_OIL", "WTI 국제유가", "$/bbl", "(데모) 원자재 시세 생성"),
    ("COPPER", "국제 구리 가격", "$/t", "(데모) 원자재 시세 생성"),
    ("SILICON_WAFER", "실리콘 웨이퍼 가격지수", "index", "(데모) 원자재 시세 생성"),
]

NEWS = [
    ("글로벌 반도체 수요 회복세…서버·차량용 전장 칩 출하 증가", "반도체", "positive", 88, "높음",
     "서버 및 차량용 반도체 수요가 회복되며 패키징·기판 수요에 긍정적입니다.",
     "주요 거래처의 전장 부품 수주 확대 가능성 → 매출 성장 기회"),
    ("일본의 반도체 소재 수출규제 재검토…공급망 다변화 논의", "공급망", "negative", 82, "높음",
     "일본산 소재·부품 수출 규제 가능성이 제기되어 원자재 조달 리스크가 커지고 있습니다.",
     "일본 의존 원자재(동박 등) 조달 차질 가능 → 원가·납기 리스크"),
    ("한국은행 기준금리 동결…가계부채 부담에 신중론", "정책", "neutral", 65, "보통",
     "기준금리 동결 기조가 이어지며 금융비용 부담은 현 수준 유지 전망입니다.",
     "차입금 이자 비용 안정 → 단기 금융비용 리스크 낮음"),
    ("미국 금리 인하 시사…달러 강세 둔화 기대에 원화 안정", "거시경제", "positive", 70, "보통",
     "미국 금리 인하 기대가 커지며 달러 강세가 둔화될 수 있다는 전망입니다.",
     "수출 비중이 높은 기업에 환율 안정 → 수출 가격 경쟁력 유지"),
    ("국내 반도체 클러스터 사업 본격화…부품·소재 협력사 육성 계획", "정책", "positive", 76, "높음",
     "정부가 반도체 클러스터 내 협력사 육성 계획을 발표했습니다.",
     "국산 부품 인증·매칭 기회 → 신규 거래처 확보 가능성"),
    ("차량용 반도체 품귀 재발 우려…파워 반도체 공급 부족 지속", "반도체", "negative", 74, "보통",
     "차량용 파워 반도체 공급 부족이 이어지며 수요가 공급을 상회하고 있습니다.",
     "당사 파워 패키지 수요 강세 → 매출 증가 요인(단, 원자재 조달 리스크 동반)"),
    ("국제 유가 상승…제조업 에너지 비용 부담 확대", "거시경제", "negative", 58, "보통",
     "국제유가가 상승하며 제조업 전반의 에너지 비용 부담이 커지고 있습니다.",
     "전력·가스 비용 상승 → 제조 간접비 증가 가능"),
    ("베트남, 반도체 인력 양성 프로그램 확대…당지 생산기지 유치 경쟁", "정책", "neutral", 52, "보통",
     "베트남이 반도체 인력 양성을 확대하며 제조기지 유치를 경쟁하고 있습니다.",
     "베트남 거래처 C사의 생산 확대 → 수출 물량 증가 가능성"),
    ("실리콘 웨이퍼 가격 2분기 연속 상승…원자재 조달비 증가 우려", "공급망", "negative", 85, "높음",
     "실리콘 웨이퍼 가격이 연속 상승하며 반도체 제조 원가 부담이 증가하고 있습니다.",
     "최대 원자재인 웨이퍼 조달비 상승 → 원가율 악화 직접 영향"),
    ("미국, 중국산 반도체 관세 재검토…수출 기업 불확실성", "정책", "negative", 68, "보통",
     "미국의 대중 관세 정책 재검토로 반도체 수출 환경의 불확실성이 커졌습니다.",
     "중국향 수출 비중이 있다면 통상 리스크 → 수출 다변화 필요"),
    ("국내 전장부품사 수주잔고 사상 최대…완성차 전동화 확대", "반도체", "positive", 80, "높음",
     "국내 전장부품사의 수주잔고가 사상 최대를 기록하며 전동화 수요가 견조합니다.",
     "주요 거래처 A·B사 수주 확대 → 매출 성장 지속 가능"),
    ("동박(Cu) 가격 급등…MLCC·기판 업계 원가 압박", "공급망", "negative", 71, "높음",
     "동박 가격이 급등하며 전자부품 기판 업계의 원가 부담이 커지고 있습니다.",
     "서브스트레이트 원자재인 동박 조달비 상승 → 제품 원가율 악화"),
    ("원/달러 환율 1,400원대 진입…수입 물가 상승 압력", "환율", "negative", 78, "높음",
     "원/달러 환율이 1,400원대를 돌파하며 수입 원자재 조달 비용 부담이 커졌습니다.",
     "외화 결제 수입 비중이 높아 원가 상승 → 수익성 악화 시나리오"),
    ("글로벌 파운드리 가동률 회복…아웃소싱 수요 증가 전망", "반도체", "positive", 63, "보통",
     "파운드리 가동률이 회복되며 팹리스·부품사의 외주 수요가 늘어날 전망입니다.",
     "부품 외주 물량 증가 → 신규 거래 기회"),
    ("독일 산업생산 부진…유럽 수출 수요 둔화 우려", "거시경제", "negative", 55, "보통",
     "독일 산업생산이 부진하며 유럽향 수출 수요 둔화 우려가 제기됐습니다.",
     "독일 거래처 D사 수요 둔화 가능 → 수출 믹스 점검 필요"),
    ("반도체 장비 투자 확대…국내 부품사 참여 기회 확대", "정책", "positive", 60, "보통",
     "국내 반도체 공장의 설비투자가 확대되며 부품·소재 협력사 참여 기회가 늘고 있습니다.",
     "국내 협력사 네트워크 확대 → 신규 고객 발굴 가능"),
]


def seed(db: Session):
    # 이미 데이터가 있으면 스킵
    if db.query(Company).first():
        return False

    company = Company(
        name="(데모) 한빛세미텍",
        industry="반도체 부품 제조업",
        size="중소기업 (직원 약 150명)",
        products="파워 반도체 패키지, 아날로그 IC 서브스트레이트, 차량용 센서 모듈",
        key_customers="국내 전장부품 A사·B사, 해외 디스플레이 모듈 C사(베트남), 해외 산업용 D사(독일), 국내 가전 부품 E사",
        export_countries="미국, 베트남, 독일",
        import_countries="일본, 대만, 중국",
        raw_materials="실리콘 웨이퍼, 동박(Cu), 에폭시 수지, 금(Au) 와이어",
        export_import_ratio="수출 62% / 수입 38%",
        annual_revenue=115_000_000_000,
        annual_raw_material_cost=71_000_000_000,
        fx_settlement_ratio=0.55,
        interest_areas="반도체 공급망, 수출 통상정책, 환율, 전장부품 수요",
        risk_concerns="환율 급등, 실리콘 웨이퍼·동박 가격 상승, 국내 전장부품 A사 매출 집중",
    )
    db.add(company)
    db.flush()
    cid = company.id

    # 사용자 4개 권한
    pw = hash_password("demo1234")
    for email, name, role in [
        ("owner@dayribbon.demo", "김대표", "OWNER"),
        ("admin@dayribbon.demo", "박관리", "ADMIN"),
        ("member@dayribbon.demo", "이실무", "MEMBER"),
        ("viewer@dayribbon.demo", "최감사", "VIEWER"),
    ]:
        db.add(User(company_id=cid, email=email, password_hash=pw, name=name, role=role))

    db.add(NotificationSetting(company_id=cid, email_address="ceo@hanbit-semitech.demo"))

    # 24개월 재무 데이터
    months = month_range(24)
    base_rev = 8.6e9
    for i, m in enumerate(months):
        trend = 1 + i * 0.004  # 완만한 성장
        seasonal = 1.12 if m.endswith("-11") or m.endswith("-12") else (0.95 if m.endswith("-02") else 1.0)
        noise = random.uniform(0.96, 1.04)
        # 최근 2개월 매출 소폭 둔화 시나리오
        recent_dip = 0.94 if i >= len(months) - 2 else 1.0
        revenue = base_rev * trend * seasonal * noise * recent_dip
        op_margin = random.uniform(0.075, 0.115) - (0.02 if i >= len(months) - 2 else 0)
        op = revenue * op_margin
        mat = revenue * random.uniform(0.52, 0.60)
        labor = revenue * random.uniform(0.11, 0.14)
        other = revenue - mat - labor - op  # 비용+이익=매출이 되도록 잔여 배분
        # 환율: 1,320 → 1,410, 최근 2개월 급등
        fx = 1320 + i * 3.6 + random.uniform(-8, 8)
        if i >= len(months) - 2:
            fx += (i - (len(months) - 3)) * 28
        export_ratio = random.uniform(0.58, 0.66)
        export_amt = revenue * export_ratio
        import_amt = revenue * (1 - export_ratio) * 0.9
        db.add(FinancialMonthly(
            company_id=cid, month=m, revenue=round(revenue),
            operating_profit=round(op), raw_material_cost=round(mat),
            labor_cost=round(labor), other_cost=round(other),
            export_amount=round(export_amt), import_amount=round(import_amt),
            fx_avg_rate=round(fx, 1),
        ))

    # 제품별 (최근 12개월)
    pweights = [0.45, 0.35, 0.20]
    pmargin = [0.14, 0.09, 0.16]
    for i, m in enumerate(months[-12:]):
        rev_total = base_rev * (1 + (len(months) - 12 + i) * 0.004) * random.uniform(0.95, 1.05)
        for pi, pname in enumerate(PRODUCTS):
            pr = rev_total * pweights[pi] * random.uniform(0.92, 1.08)
            pc = pr * (1 - pmargin[pi] + random.uniform(-0.01, 0.01))
            db.add(ProductMonthly(company_id=cid, month=m, product_name=pname,
                                  revenue=round(pr), cost=round(pc)))

    # 거래처별 (최근 12개월)
    cweights = [0.34, 0.22, 0.18, 0.15, 0.11]
    for i, m in enumerate(months[-12:]):
        rev_total = base_rev * (1 + (len(months) - 12 + i) * 0.004) * random.uniform(0.95, 1.05)
        for ci, (cname, country) in enumerate(CUSTOMERS):
            cr = rev_total * cweights[ci] * random.uniform(0.9, 1.1)
            db.add(CustomerMonthly(company_id=cid, month=m, customer_name=cname,
                                   country=country, revenue=round(cr)))

    # 원자재 구매 (최근 12개월)
    mweights = [0.55, 0.30, 0.15]
    for i, m in enumerate(months[-12:]):
        total = base_rev * 0.56 * random.uniform(0.95, 1.05)
        for mi, mname in enumerate(MATERIALS):
            db.add(MaterialPurchase(company_id=cid, month=m, material_name=mname,
                                    amount_krw=round(total * mweights[mi] * random.uniform(0.92, 1.08))))

    # 시장 시계열
    fx_vals = []
    for i, m in enumerate(months):
        fx_vals.append(1320 + i * 3.6)
    for i in range(len(months) - 2):
        fx_vals[i] += random.uniform(-8, 8)
    fx_vals[-2] += 30
    fx_vals[-1] += 58  # 최근 급등

    series_data = {
        "USD_KRW": [round(v, 1) for v in fx_vals],
        "BASE_RATE": [round(3.0 - i * 0.02 + random.uniform(-0.03, 0.03), 2) for i in range(len(months))],
        "FED_RATE": [round(4.5 - i * 0.025 + random.uniform(-0.03, 0.03), 2) for i in range(len(months))],
        "KOSPI": [round(2650 + i * 9 + random.uniform(-60, 60), 1) for i in range(len(months))],
        "NASDAQ": [round(17200 + i * 45 + random.uniform(-250, 250), 1) for i in range(len(months))],
        "SEMI_ETF": [round(100 + i * 1.1 + random.uniform(-4, 4), 2) for i in range(len(months))],
        "WTI_OIL": [round(78 + i * 0.15 + random.uniform(-4, 4), 2) for i in range(len(months))],
        "COPPER": [round(9200 + i * 28 + random.uniform(-150, 150), 0) for i in range(len(months))],
        "SILICON_WAFER": [round(100 + i * 0.9 + random.uniform(-3, 3) + (8 if i > len(months) - 6 else 0), 2)
                          for i in range(len(months))],
    }
    for key, name, unit, source in SERIES:
        for m, v in zip(months, series_data[key]):
            db.add(MarketSeries(company_id=cid, series_key=key, series_name=name,
                                unit=unit, source=source, month=m, value=v))

    # 뉴스
    now = datetime.utcnow()
    for i, (title, cat, sent, rel, imp, impact, why) in enumerate(NEWS):
        days_ago = random.randint(1, 55)
        db.add(NewsItem(
            company_id=cid, title=title, category=cat, sentiment=sent,
            relevance_score=float(rel), importance=imp,
            impact_on_company=impact, why_relevant=why,
            source=f"(데모) {'전자신문' if cat == '반도체' else '산업경제뉴스'}",
            summary=f"{title} — {impact}",
            published_at=now - timedelta(days=days_ago, hours=random.randint(0, 12)),
        ))

    db.commit()

    # 분석 파이프라인 1회 실행 (seed 트리거)
    from .services.analysis_engine import run_pipeline
    result = run_pipeline(db, cid, trigger="seed")

    # 시드 의사결정/후속조치 예시
    first_analysis = db.query(AnalysisResult).filter(
        AnalysisResult.company_id == cid, AnalysisResult.analysis_type == "risk"
    ).first()
    if first_analysis:
        d = Decision(
            company_id=cid, analysis_result_id=first_analysis.id, status="검토 중",
            decision="보류", reason="환율 추이 추가 관찰 후 수입 결제 시점 조정 검토",
            assignee="박관리", due_date=(now + timedelta(days=14)).strftime("%Y-%m-%d"),
            created_by="김대표",
        )
        db.add(d)
        db.flush()
        db.add(FollowUp(company_id=cid, decision_id=d.id,
                        title="주요 수입처와 환헤지(선물환) 조건 협의", status="진행 중",
                        assignee="박관리", due_date=(now + timedelta(days=10)).strftime("%Y-%m-%d"),
                        created_by="김대표"))
        db.add(FollowUp(company_id=cid, decision_id=d.id,
                        title="실리콘 웨이퍼 장기공급계약 물량 재협상", status="등록",
                        assignee="이실무", due_date=(now + timedelta(days=21)).strftime("%Y-%m-%d"),
                        created_by="김대표"))

    # 지난달 보고서 1건 생성
    try:
        from .services.report_service import create_report
        create_report(db, cid, prev_month(months[-1]), "김대표")
    except Exception:
        pass

    # 감사 로그 시드
    from .models import AuditLog
    db.add(AuditLog(company_id=cid, user_name="(시스템)", user_role="SYSTEM",
                    action="DEMO_SEED", target_type="company", target_id=str(cid),
                    detail=f"데모 데이터 초기 생성 완료 (분석 {result['new_analyses']}건, 알림 {result['new_alerts']}건)"))
    db.commit()
    return True
