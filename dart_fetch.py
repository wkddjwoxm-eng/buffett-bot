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

# 국장 유니버스 전종목 corp_code 매핑 (티커 → DART corp_code)
# corp_code는 8자리 숫자. build_corp_codes.py로 자동 생성.
# 동적 fallback: _ensure_corp_codes_loaded() 함수 참조.
_CORP_CODE_CACHE: dict[str, str] = {}
_STOCK_TO_CORP: dict[str, str] = {}  # stock_code(6자리) → corp_code (lazy loaded)

_TICKER_TO_CORP: dict[str, str] = {
    "000080.KS": "00150244",
    "000100.KS": "00145109",
    "000120.KS": "00113410",
    "000150.KS": "00117212",
    "000270.KS": "00106641",
    "000660.KS": "00164779",
    "000720.KS": "00164478",
    "000810.KS": "00139214",
    "000880.KS": "00160588",
    "000990.KS": "00160843",
    "001040.KS": "00148540",
    "001060.KS": "00149947",
    "001230.KS": "00114792",
    "001430.KS": "00106669",
    "001450.KS": "00164973",
    "001680.KS": "00121941",
    "002320.KS": "00163512",
    "002350.KS": "00173874",
    "002380.KS": "00105271",
    "003220.KS": "00111999",
    "003230.KS": "00126955",
    "003490.KS": "00113526",
    "003540.KS": "00110893",
    "003550.KS": "00120021",
    "003670.KS": "00155276",
    "003850.KS": "00123143",
    "004020.KS": "00145880",
    "004100.KS": "00153755",
    "004170.KS": "00136378",
    "004370.KS": "00108241",
    "004800.KS": "00117188",
    "004960.KS": "00162063",
    "004990.KS": "00120562",
    "005070.KS": "00129989",
    "005180.KS": "00124726",
    "005290.KS": "00118804",
    "005300.KS": "00120571",
    "005380.KS": "00164742",
    "005450.KS": "00173740",
    "005490.KS": "00155319",
    "005610.KS": "00125530",
    "005830.KS": "00159102",
    "005850.KS": "00125521",
    "005930.KS": "00126380",
    "005940.KS": "00120182",
    "006260.KS": "00105952",
    "006280.KS": "00129679",
    "006360.KS": "00120030",
    "006400.KS": "00126362",
    "006800.KS": "00111722",
    "007070.KS": "00140177",
    "007310.KS": "00141529",
    "008770.KS": "00165680",
    "009150.KS": "00126371",
    "009420.KS": "00162586",
    "009540.KS": "00164830",
    "009830.KS": "00162461",
    "010060.KS": "00148896",
    "010130.KS": "00102858",
    "010140.KS": "00126478",
    "010620.KS": "00164609",
    "010690.KS": "00166315",
    "010950.KS": "00138279",
    "011070.KS": "00105961",
    "011170.KS": "00165413",
    "011200.KS": "00164645",
    "011210.KS": "00106623",
    "011780.KS": "00106368",
    "011790.KS": "00139889",
    "012330.KS": "00164788",
    "012450.KS": "00126566",
    "014620.KS": "00132318",
    "014790.KS": "00161116",
    "015750.KS": "00132992",
    "015760.KS": "00159193",
    "016360.KS": "00104856",
    "017670.KS": "00159023",
    "017810.KS": "00155355",
    "018260.KS": "00126186",
    "018880.KS": "00161125",
    "020150.KS": "00113997",
    "020560.KS": "00138792",
    "023530.KS": "00120526",
    "026960.KS": "00144395",
    "028150.KS": "00207755",
    "028260.KS": "00149655",
    "028300.KQ": "00199252",
    "028670.KS": "00122737",
    "030200.KS": "00190321",
    "030610.KS": "00113359",
    "031430.KS": "00234412",
    "032640.KS": "00231363",
    "032830.KS": "00126256",
    "033780.KS": "00244455",
    "034020.KS": "00159616",
    "034730.KS": "00181712",
    "035420.KS": "00266961",
    "035720.KS": "00258801",
    "035760.KS": "00265324",
    "035900.KQ": "00258689",
    "036420.KS": "00203315",
    "036460.KS": "00261285",
    "036570.KS": "00261443",
    "036830.KQ": "00247975",
    "036930.KQ": "00252135",
    "039030.KQ": "00246417",
    "039200.KQ": "00263654",
    "039490.KQ": "00296290",
    "041510.KQ": "00260930",
    "041830.KQ": "00269922",
    "042660.KS": "00111704",
    "042700.KS": "00161383",
    "047040.KS": "00124540",
    "047050.KS": "00124504",
    "047810.KS": "00309503",
    "048260.KQ": "00341916",
    "049770.KS": "00340917",
    "051600.KS": "00159218",
    "051910.KS": "00356361",
    "052690.KS": "00159209",
    "053030.KQ": "00216027",
    "055550.KS": "00382199",
    "057050.KS": "00412597",
    "058470.KS": "00369657",
    "064290.KQ": "00479787",
    "064350.KS": "00302926",
    "064760.KQ": "00245472",
    "066570.KS": "00401731",
    "066970.KQ": "00398701",
    "067310.KQ": "00445054",
    "067630.KQ": "00365590",
    "068270.KS": "00413046",
    "069080.KQ": "00405320",
    "069620.KS": "00427483",
    "069960.KS": "00428251",
    "071050.KS": "00432102",
    "073240.KS": "00481454",
    "078020.KQ": "00330424",
    "078150.KS": "00255275",
    "078340.KQ": "00476498",
    "078600.KQ": "00177816",
    "078930.KS": "00500254",
    "079550.KS": "00503668",
    "082740.KS": "00361008",
    "084370.KQ": "00531014",
    "085660.KQ": "00525679",
    "086280.KS": "00360595",
    "086520.KQ": "00536541",
    "086790.KS": "00547583",
    "086900.KQ": "00580199",
    "088350.KS": "00113058",
    "089010.KQ": "00371485",
    "089590.KQ": "00555874",
    "091990.KS": "00554024",
    "095340.KQ": "00572905",
    "095610.KQ": "00524421",
    "095720.KQ": "00628189",
    "096530.KQ": "00788773",
    "096770.KS": "00631518",
    "097950.KS": "00635134",
    "101490.KQ": "00411048",
    "105560.KS": "00688996",
    "112040.KQ": "00444329",
    "120110.KS": "00795135",
    "122870.KQ": "00613318",
    "128940.KS": "00828497",
    "131970.KQ": "00563545",
    "138040.KS": "00860332",
    "138930.KS": "00858364",
    "139130.KS": "00878915",
    "139480.KS": "00872984",
    "140860.KQ": "00244747",
    "141080.KQ": "00842619",
    "145020.KQ": "00888347",
    "145720.KQ": "00526599",
    "160550.KQ": "00974927",
    "161390.KS": "00937324",
    "170900.KS": "00956930",
    "175330.KS": "00980122",
    "183300.KQ": "00997812",
    "185750.KS": "00992871",
    "192080.KQ": "01010110",
    "196170.KQ": "00989619",
    "200880.KS": "01036446",
    "204320.KS": "01042775",
    "206650.KQ": "00927558",
    "207940.KS": "00877059",
    "215200.KQ": "01074862",
    "222800.KQ": "01095722",
    "237690.KQ": "00871833",
    "240810.KS": "01135941",
    "247540.KQ": "01160363",
    "249420.KS": "01168383",
    "251270.KS": "00904672",
    "253450.KQ": "01168684",
    "259960.KS": "00760971",
    "263750.KS": "01152470",
    "267250.KS": "01205709",
    "267980.KS": "01234507",
    "271560.KS": "01238169",
    "278280.KQ": "00897752",
    "280360.KS": "01258507",
    "282330.KS": "01263022",
    "285130.KS": "01267170",
    "294870.KS": "01310269",
    "298050.KS": "01316254",
    "302440.KS": "01319899",
    "307950.KS": "00362441",
    "316140.KS": "01350869",
    "319660.KS": "01365825",
    "322510.KQ": "01153293",
    "323410.KS": "01133217",
    "326030.KS": "00878696",
    "328130.KQ": "01397620",
    "329180.KS": "01390344",
    "336370.KQ": "01412822",
    "338220.KQ": "01344202",
    "352820.KS": "01204056",
    "361610.KS": "01386916",
    "373220.KS": "01515323",
    "375500.KS": "01524093",
    "377300.KS": "01244601",
    "393890.KS": "01291317",
    "402340.KS": "01596425",
    "403870.KS": "01288827",
    "432720.KQ": "01584183",
    "443060.KS": "01194689",
}


def _ensure_corp_codes_loaded() -> None:
    """전체 corp_code 매핑을 DART API에서 lazy load."""
    global _STOCK_TO_CORP
    if _STOCK_TO_CORP:
        return
    try:
        import io
        import zipfile
        import xml.etree.ElementTree as ET
        key = _get_api_key()
        if not key:
            return
        url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={key}"
        r = requests.get(url, timeout=30)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        xml_data = z.read("CORPCODE.xml")
        root = ET.fromstring(xml_data)
        for item in root.findall("list"):
            cc = item.findtext("corp_code", "").strip()
            sc = item.findtext("stock_code", "").strip()
            if sc and len(sc) == 6 and sc.isdigit():
                _STOCK_TO_CORP[sc] = cc
    except Exception:
        pass


def find_corp_code(ticker: str) -> Optional[str]:
    """
    티커 → DART corp_code 반환.
    하드코딩 매핑 우선, 없으면 전체 corp_code 매핑에서 동적 조회.
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

    # lazy load 전체 매핑으로 fallback
    _ensure_corp_codes_loaded()
    result = _STOCK_TO_CORP.get(code)
    _CORP_CODE_CACHE[ticker] = result
    return result


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
