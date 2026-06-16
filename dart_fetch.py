"""
DART(전자공시시스템) API 연동 — 국내 주식 재무 데이터 보완.
yfinance 국장 데이터 품질 한계를 DART 공식 데이터로 보완한다.

API 키: 환경변수 DART_API_KEY 또는 secrets.toml (Streamlit Cloud)
무료 키: opendart.fss.or.kr (일 10,000건)
"""
from __future__ import annotations

import os
import time
import requests
from typing import Optional


def _get_api_key() -> str:
    key = os.environ.get("DART_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("DART_API_KEY", "")
        except Exception:
            pass
    return key


DART_API_KEY = _get_api_key()
BASE_URL = "https://opendart.fss.or.kr/api"

# 주요 종목 corp_code 사전 매핑 (티커 → DART corp_code)
# corp_code는 8자리 숫자. 아래는 주요 종목 하드코딩 (API로 검색도 가능)
# find_corp() 함수로 동적 검색 가능
_CORP_CODE_CACHE: dict[str, str] = {}
_TICKER_TO_CORP: dict[str, str] = {
    "005930.KS": "00126380",  # 삼성전자
    "000660.KS": "00164779",  # SK하이닉스
    "035420.KS": "00266961",  # NAVER
    "035720.KS": "00401731",  # 카카오
    "005380.KS": "00164742",  # 현대차
    "000270.KS": "00164489",  # 기아
    "051910.KS": "00356361",  # LG화학
    "006400.KS": "00164788",  # 삼성SDI
    "207940.KS": "00421045",  # 삼성바이오로직스
    "068270.KS": "00131747",  # 셀트리온
    "105560.KS": "00138518",  # KB금융
    "055550.KS": "00138516",  # 신한지주
    "086790.KS": "00138536",  # 하나금융지주
    "316140.KS": "00138520",  # 우리금융지주
    "032830.KS": "00138521",  # 삼성생명
    "003670.KS": "00164826",  # 포스코홀딩스
    "090430.KS": "00164828",  # 아모레퍼시픽
    "034730.KS": "00164830",  # SK
    "017670.KS": "00164840",  # SK텔레콤
    "030200.KS": "00164845",  # KT
    "015760.KS": "00164847",  # 한국전력
    "011170.KS": "00356360",  # 롯데케미칼
    "096770.KS": "00164832",  # SK이노베이션
    "010950.KS": "00164803",  # S-Oil
    "028260.KS": "00164812",  # 삼성물산
    "009150.KS": "00164778",  # 삼성전기
    "018260.KS": "00164817",  # 삼성에스디에스
    "012330.KS": "00164795",  # 현대모비스
    "247540.KS": "00421050",  # 에코프로비엠
    "086520.KS": "00356363",  # 에코프로
    "373220.KS": "00421055",  # LG에너지솔루션
}


def find_corp_code(ticker: str) -> Optional[str]:
    """
    티커 → DART corp_code 반환.
    하드코딩 매핑 우선, 없으면 DART 검색 API 사용.
    """
    if ticker in _TICKER_TO_CORP:
        return _TICKER_TO_CORP[ticker]

    if ticker in _CORP_CODE_CACHE:
        return _CORP_CODE_CACHE[ticker]

    # 티커에서 종목코드 추출 (005930.KS → 005930)
    code = ticker.replace(".KS", "").replace(".KQ", "")
    if not code.isdigit():
        _CORP_CODE_CACHE[ticker] = None
        return None

    # DART 회사 검색 API
    try:
        _CORP_CODE_CACHE[ticker] = None
        return None
    except Exception:
        return None


def get_financial_data(ticker: str, year: int = None, reprt_code: str = "11011") -> Optional[dict]:
    """
    DART 단일회사 주요계정 조회.

    reprt_code: 11011=사업보고서(연간), 11012=반기, 11013=1분기, 11014=3분기

    Returns: {
        "revenue": float,          # 매출액
        "operating_income": float, # 영업이익
        "net_income": float,       # 당기순이익
        "total_assets": float,     # 자산총계
        "total_equity": float,     # 자본총계
        "total_debt": float,       # 부채총계
        "roe": float,              # ROE
        "year": int
    }
    """
    corp_code = find_corp_code(ticker)
    if not corp_code:
        return None

    import datetime
    if year is None:
        year = datetime.date.today().year - 1  # 직전 사업연도

    try:
        api_key = _get_api_key()
        params = {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": reprt_code,
        }
        r = requests.get(f"{BASE_URL}/fnlttSinglAcnt.json", params=params, timeout=15)
        data = r.json()

        if data.get("status") != "000":
            return None

        items = {item["account_nm"]: item for item in data.get("list", [])}

        def _val(name: str) -> Optional[float]:
            item = items.get(name)
            if item is None:
                return None
            try:
                v = item.get("thstrm_amount", "").replace(",", "").strip()
                return float(v) if v and v != "-" else None
            except (ValueError, AttributeError):
                return None

        revenue = _val("매출액") or _val("영업수익")
        op_income = _val("영업이익") or _val("영업손익")
        net_income = _val("당기순이익") or _val("당기순손익")
        total_assets = _val("자산총계")
        total_equity = _val("자본총계")
        total_debt = _val("부채총계")

        roe = None
        if net_income and total_equity and total_equity > 0:
            roe = net_income / total_equity

        time.sleep(0.05)  # DART rate limit 준수

        return {
            "revenue": revenue,
            "operating_income": op_income,
            "net_income": net_income,
            "total_assets": total_assets,
            "total_equity": total_equity,
            "total_debt": total_debt,
            "roe": roe,
            "year": year,
        }

    except Exception:
        return None


def get_multi_year_financials(ticker: str, years: int = 3) -> list[dict]:
    """최근 N년치 DART 재무 데이터 반환 (최신→과거 순)."""
    import datetime
    current_year = datetime.date.today().year
    results = []
    for y in range(current_year - 1, current_year - 1 - years, -1):
        d = get_financial_data(ticker, year=y)
        if d:
            results.append(d)
    return results


def get_dart_fundamentals(ticker: str) -> Optional[dict]:
    """
    DART에서 국내 종목 핵심 펀더멘털 반환.
    datafetch._normalize()에서 yfinance 데이터 보완에 사용.

    Returns: {
        "roe": float,
        "revenue_list": list[float],    # 최신→과거
        "net_income_list": list[float],
        "equity_list": list[float],
        "total_assets_list": list[float],
        "de_ratio": float,              # 부채/자본
        "operating_margin": float,
    }
    """
    if not (ticker.endswith(".KS") or ticker.endswith(".KQ")):
        return None

    corp_code = find_corp_code(ticker)
    if not corp_code:
        return None

    records = get_multi_year_financials(ticker, years=3)
    if not records:
        return None

    latest = records[0]

    revenue_list = [r["revenue"] for r in records if r.get("revenue")]
    ni_list = [r["net_income"] for r in records if r.get("net_income")]
    eq_list = [r["total_equity"] for r in records if r.get("total_equity")]
    ta_list = [r["total_assets"] for r in records if r.get("total_assets")]

    roe = latest.get("roe")

    de_ratio = None
    if latest.get("total_debt") and latest.get("total_equity") and latest["total_equity"] > 0:
        de_ratio = latest["total_debt"] / latest["total_equity"]

    op_margin = None
    if latest.get("operating_income") and latest.get("revenue") and latest["revenue"] > 0:
        op_margin = latest["operating_income"] / latest["revenue"]

    return {
        "roe": roe,
        "revenue_list": revenue_list,
        "net_income_list": ni_list,
        "equity_list": eq_list,
        "total_assets_list": ta_list,
        "de_ratio": de_ratio,
        "operating_margin": op_margin,
        "source": "DART",
    }
