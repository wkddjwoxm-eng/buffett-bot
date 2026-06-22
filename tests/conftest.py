"""공용 테스트 픽스처 — 금융 엔진 검증용 가상 Fundamentals.

레포 루트를 import 경로에 넣어 `import buffett` 같은 평면 import가 동작하게 한다
(앱이 루트 평면 모듈 구조라 tests/에서 실행해도 동일 경로를 보장).
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from buffett import Fundamentals  # noqa: E402


@pytest.fixture
def quality_cheap():
    """고품질·저가 우량주 — 강력매수~매수검토가 나와야 하는 종합 케이스.

    숫자는 서로 정합적으로 맞춰 둔다(EPS×주식수=순이익, BPS×주식수=자기자본 등)
    → 점수뿐 아니라 ROIC·오너이익·DCF까지 한 번에 검증 가능.
    """
    shares = 1000.0
    price = 120.0
    eps = 10.0          # 순이익 10,000
    bps = 80.0          # 자기자본 80,000  → PBR 1.5
    return Fundamentals(
        ticker="TEST.KS", name="테스트우량", market="KR", currency="KRW",
        sector="필수소비재·식품·음료", industry="Beverages",
        price=price, market_cap=price * shares,
        roe=0.22, roe_history=[0.22, 0.21, 0.20, 0.23],
        gross_margin=0.50, operating_margin=0.26, net_margin=0.20,
        revenue_cagr=0.12, earnings_cagr=0.12,
        debt_to_equity=0.20, current_ratio=2.5, fcf=9000.0, fcf_yield=0.075,
        dividend_yield=0.03, payout_ratio=0.4,
        interest_coverage=15.0,
        per=price / eps, pbr=price / bps, eps=eps, bps=bps, shares=shares,
        hist={
            "net_income":          [10000, 9000, 8000, 7000],
            "revenue":             [50000, 45000, 41000, 38000],
            "gross_profit":        [25000, 22000, 20000, 18000],
            "equity":              [80000, 72000, 65000, 60000],
            "shares_bs":           [1000, 1000, 1000, 1000],
            "ocf":                 [12000, 10500, 9500, 8500],
            "fcf":                 [9000, 8000, 7000, 6000],
            "ebit":                [13000, 11700, 10500, 9500],
            "pretax":              [12000, 10800, 9700, 8800],
            "tax":                 [2640, 2376, 2134, 1936],
            "total_assets":        [120000, 110000, 100000, 95000],
            "current_assets":      [50000, 45000, 41000, 38000],
            "current_liabilities": [20000, 19000, 18000, 17000],
            "total_debt":          [16000, 15000, 14000, 13000],
            "long_term_debt":      [10000, 11000, 12000, 13000],
            "cash":                [10000, 9000, 8000, 7000],
            "capex":               [-3000, -2700, -2400, -2200],
            "dep_amort":           [3000, 2700, 2400, 2200],
        },
    )


@pytest.fixture
def loss_maker():
    """적자 기업 — 무조건 '회피'로 강등돼야 하는 케이스."""
    shares = 1000.0
    price = 30.0
    return Fundamentals(
        ticker="LOSS.KS", name="적자기업", market="KR", currency="KRW",
        sector="건설·부동산", industry="Construction",
        price=price, market_cap=price * shares,
        roe=-0.08, roe_history=[-0.08, -0.02, 0.01, 0.03],
        gross_margin=0.08, net_margin=-0.05,
        revenue_cagr=-0.03, earnings_cagr=-0.30,
        debt_to_equity=2.5, current_ratio=0.9, fcf=-4000.0, fcf_yield=-0.10,
        per=None, pbr=0.6, eps=-1.5, bps=50.0, shares=shares,
        hist={
            "net_income":          [-1500, 800, 1200, 1500],
            "revenue":             [40000, 42000, 43000, 41000],
            "gross_profit":        [3200, 5000, 6000, 6500],
            "equity":              [50000, 51500, 50700, 49500],
            "shares_bs":           [1000, 1000, 1000, 1000],
            "ocf":                 [-2000, 1000, 1400, 1600],
            "fcf":                 [-4000, -500, 200, 600],
            "ebit":                [-1000, 1500, 2000, 2400],
            "pretax":              [-1300, 1100, 1600, 2000],
            "tax":                 [0, 240, 350, 440],
            "total_assets":        [180000, 175000, 170000, 165000],
            "current_assets":      [40000, 42000, 43000, 44000],
            "current_liabilities": [44000, 42000, 40000, 39000],
            "total_debt":          [125000, 120000, 115000, 110000],
            "long_term_debt":      [90000, 88000, 85000, 82000],
            "cash":                [3000, 4000, 5000, 6000],
            "capex":               [-2000, -1500, -1200, -1000],
            "dep_amort":           [2500, 2300, 2100, 2000],
        },
    )


@pytest.fixture
def bank():
    """은행 — 금융업 특례(부채/FCF 잣대 미적용)가 적용돼야 하는 케이스."""
    shares = 2000.0
    price = 60.0
    return Fundamentals(
        ticker="BANK.KS", name="테스트은행", market="KR", currency="KRW",
        sector="금융·보험·증권", industry="Banks - Regional",
        price=price, market_cap=price * shares,
        roe=0.13, roe_history=[0.13, 0.12, 0.11, 0.12],
        gross_margin=None, net_margin=0.25,
        revenue_cagr=0.05, earnings_cagr=0.06,
        debt_to_equity=8.0, current_ratio=None, fcf=None, fcf_yield=None,
        dividend_yield=0.05,
        per=6.0, pbr=0.5, eps=10.0, bps=120.0, shares=shares,
        hist={
            "net_income":   [20000, 18000, 16000, 17000],
            "total_assets": [1500000, 1450000, 1400000, 1380000],
            "equity":       [240000, 225000, 210000, 200000],
            "revenue":      [80000, 76000, 72000, 70000],
        },
    )
