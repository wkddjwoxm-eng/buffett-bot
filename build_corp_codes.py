"""DART corp_code 전체 다운로드 및 매핑 생성 — 1회 실행용."""
import io
import os
import zipfile
import xml.etree.ElementTree as ET
import requests
import sys

sys.path.insert(0, os.path.dirname(__file__))

DART_API_KEY = "db0ad745fc380f0e7a97a340ac6f148faf34ddf4"


def download_corp_codes() -> dict:
    """stock_code(6자리) → corp_code(8자리) 매핑 반환."""
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={DART_API_KEY}"
    r = requests.get(url, timeout=30)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    xml_data = z.read("CORPCODE.xml")
    root = ET.fromstring(xml_data)

    mapping = {}
    for item in root.findall("list"):
        corp_code = item.findtext("corp_code", "").strip()
        stock_code = item.findtext("stock_code", "").strip()
        if stock_code and len(stock_code) == 6 and stock_code.isdigit():
            mapping[stock_code] = corp_code
    return mapping


if __name__ == "__main__":
    from universe import get_universe

    print("DART corp_code 다운로드 중...")
    mapping = download_corp_codes()
    print(f"총 {len(mapping)}개 상장사 매핑 완료")

    # KR universe 티커들 매핑
    kr_tickers = [tk for tk, _, _ in get_universe("kr")]
    found = {}
    missing = []
    for tk in kr_tickers:
        code = tk.replace(".KS", "").replace(".KQ", "")
        if not code.isdigit():
            missing.append(tk)
            continue
        if code in mapping:
            found[tk] = mapping[code]
        else:
            missing.append(tk)

    print(f"매핑 성공: {len(found)}/{len(kr_tickers)}")
    if missing:
        print(f"미매핑: {missing}")

    # dart_fetch.py의 _TICKER_TO_CORP 출력
    print("\n--- dart_fetch.py에 붙여넣을 코드 ---")
    print("_TICKER_TO_CORP: dict[str, str] = {")
    for tk, cc in sorted(found.items()):
        print(f'    "{tk}": "{cc}",')
    print("}")
