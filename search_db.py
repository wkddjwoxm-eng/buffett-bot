"""
종목 검색 DB — 회사명(한글·영문) → 티커 매핑.

시총 기준 tier(1=최대)로 정렬해 검색 결과 상위에 대형주가 뜨도록 한다.
필드: (한글명, 영문명, 티커, tier)
"""
from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────
# 국장 (KOSPI / KOSDAQ 주요 종목)
# ─────────────────────────────────────────────────────────────────────────
KR_STOCKS: list[tuple[str, str, str, int]] = [
    # (한글명, 영문명, 티커, 시총tier)
    # 반도체·IT
    ("삼성전자", "Samsung Electronics", "005930.KS", 1),
    ("SK하이닉스", "SK Hynix", "000660.KS", 1),
    ("삼성전기", "Samsung Electro-Mechanics", "009150.KS", 2),
    ("삼성SDI", "Samsung SDI", "006400.KS", 2),
    ("LG전자", "LG Electronics", "066570.KS", 2),
    ("DB하이텍", "DB HiTek", "000990.KS", 3),
    ("리노공업", "Leeno Industrial", "058470.KS", 3),
    ("HPSP", "HPSP", "403870.KS", 3),
    ("피에스케이", "PSK", "319660.KS", 3),
    # 인터넷·플랫폼
    ("NAVER", "Naver", "035420.KS", 1),
    ("카카오", "Kakao", "035720.KS", 1),
    ("카카오뱅크", "KakaoBank", "323410.KS", 2),
    ("카카오페이", "KakaoPay", "377300.KS", 2),
    ("크래프톤", "Krafton", "259960.KS", 2),
    ("넷마블", "Netmarble", "251270.KS", 2),
    ("엔씨소프트", "NCSoft", "036570.KS", 2),
    ("펄어비스", "Pearl Abyss", "263750.KS", 3),
    # 2차전지·소재
    ("LG에너지솔루션", "LG Energy Solution", "373220.KS", 1),
    ("LG화학", "LG Chem", "051910.KS", 1),
    ("포스코퓨처엠", "POSCO Future M", "003670.KS", 2),
    ("에코프로비엠", "EcoPro BM", "247540.KQ", 2),
    ("에코프로", "EcoPro", "086520.KQ", 2),
    ("엘앤에프", "L&F", "066970.KQ", 2),
    ("SKC", "SKC", "011790.KS", 2),
    ("일진머티리얼즈", "Iljin Materials", "020150.KS", 3),
    # 자동차
    ("현대차", "Hyundai Motor", "005380.KS", 1),
    ("기아", "KIA Corp", "000270.KS", 1),
    ("현대모비스", "Hyundai Mobis", "012330.KS", 1),
    ("한온시스템", "Hanon Systems", "018880.KS", 2),
    ("현대위아", "Hyundai WIA", "011210.KS", 2),
    ("HL만도", "HL Mando", "204320.KS", 2),
    # 금융
    ("KB금융", "KB Financial", "105560.KS", 1),
    ("신한지주", "Shinhan Financial", "055550.KS", 1),
    ("하나금융지주", "Hana Financial", "086790.KS", 1),
    ("우리금융지주", "Woori Financial", "316140.KS", 1),
    ("삼성생명", "Samsung Life Insurance", "032830.KS", 1),
    ("삼성화재", "Samsung Fire & Marine", "000810.KS", 2),
    ("메리츠금융지주", "Meritz Financial", "138040.KS", 2),
    ("미래에셋증권", "Mirae Asset Securities", "006800.KS", 2),
    ("한국투자금융지주", "Korea Investment Holdings", "071050.KS", 2),
    ("DB손해보험", "DB Insurance", "005830.KS", 2),
    # 필수소비재·식품
    ("CJ제일제당", "CJ CheilJedang", "097950.KS", 2),
    ("오리온", "Orion", "271560.KS", 2),
    ("KT&G", "KT&G", "033780.KS", 2),
    ("농심", "Nongshim", "004370.KS", 2),
    ("오뚜기", "Ottogi", "007310.KS", 2),
    ("하이트진로", "Hite Jinro", "000080.KS", 2),
    ("롯데칠성음료", "Lotte Chilsung", "005300.KS", 2),
    ("빙그레", "Binggrae", "005180.KS", 3),
    # 바이오·헬스
    ("삼성바이오로직스", "Samsung Biologics", "207940.KS", 1),
    ("셀트리온", "Celltrion", "068270.KS", 1),
    ("셀트리온헬스케어", "Celltrion Healthcare", "091990.KS", 2),
    ("유한양행", "Yuhan Corp", "000100.KS", 2),
    ("한미약품", "Hanmi Pharm", "128940.KS", 2),
    ("종근당", "Chong Kun Dang", "185750.KS", 2),
    ("대웅제약", "Daewoong Pharma", "069620.KS", 2),
    ("동아에스티", "Dong-A ST", "170900.KS", 3),
    ("휴젤", "Hugel", "145020.KQ", 2),
    ("클래시스", "Classys", "214150.KQ", 3),
    # 지주·소재·철강
    ("POSCO홀딩스", "POSCO Holdings", "005490.KS", 1),
    ("LG", "LG Corp", "003550.KS", 1),
    ("SK", "SK Inc", "034730.KS", 1),
    ("롯데케미칼", "Lotte Chemical", "011170.KS", 2),
    ("효성첨단소재", "Hyosung Advanced Materials", "298050.KS", 2),
    ("고려아연", "Korea Zinc", "010130.KS", 2),
    ("현대제철", "Hyundai Steel", "004020.KS", 2),
    ("동국제강", "Dongkuk Steel", "001230.KS", 3),
    # 통신
    ("SK텔레콤", "SK Telecom", "017670.KS", 1),
    ("KT", "KT Corp", "030200.KS", 1),
    ("LG유플러스", "LG Uplus", "032640.KS", 2),
    # 건설·부동산
    ("삼성물산", "Samsung C&T", "028260.KS", 1),
    ("현대건설", "Hyundai E&C", "000720.KS", 2),
    ("GS건설", "GS Engineering", "006360.KS", 2),
    ("DL이앤씨", "DL E&C", "375500.KS", 2),
    # 유통·소비
    ("롯데쇼핑", "Lotte Shopping", "023530.KS", 2),
    ("이마트", "E-Mart", "139480.KS", 2),
    ("BGF리테일", "BGF Retail", "282330.KS", 2),
    ("CJ ENM", "CJ ENM", "035760.KS", 2),
    ("호텔신라", "Hotel Shilla", "008770.KS", 2),
    # 에너지
    ("한국전력", "KEPCO", "015760.KS", 1),
    ("두산에너빌리티", "Doosan Enerbility", "034020.KS", 2),
    ("한국가스공사", "KOGAS", "036460.KS", 2),
    # 조선·기계
    ("HD한국조선해양", "HD KSOE", "009540.KS", 1),
    ("삼성중공업", "Samsung Heavy Industries", "010140.KS", 2),
    ("한화오션", "Hanwha Ocean", "042660.KS", 2),
    ("HD현대중공업", "HD Hyundai Heavy Industries", "329180.KS", 2),
    # 항공·운수
    ("대한항공", "Korean Air", "003490.KS", 2),
    ("아시아나항공", "Asiana Airlines", "020560.KS", 2),
    ("HMM", "HMM", "011200.KS", 2),
]

# ─────────────────────────────────────────────────────────────────────────
# 미장 (US 주요 종목)
# ─────────────────────────────────────────────────────────────────────────
US_STOCKS: list[tuple[str, str, str, int]] = [
    # (한글명, 영문명, 티커, 시총tier)
    # 빅테크
    ("애플", "Apple", "AAPL", 1),
    ("마이크로소프트", "Microsoft", "MSFT", 1),
    ("엔비디아", "NVIDIA", "NVDA", 1),
    ("알파벳·구글", "Alphabet Google", "GOOGL", 1),
    ("아마존", "Amazon", "AMZN", 1),
    ("메타", "Meta", "META", 1),
    ("테슬라", "Tesla", "TSLA", 1),
    ("브로드컴", "Broadcom", "AVGO", 1),
    ("오라클", "Oracle", "ORCL", 1),
    ("TSMC", "TSMC", "TSM", 1),
    # 금융
    ("버크셔해서웨이", "Berkshire Hathaway", "BRK-B", 1),
    ("JP모건", "JPMorgan Chase", "JPM", 1),
    ("비자", "Visa", "V", 1),
    ("마스터카드", "Mastercard", "MA", 1),
    ("무디스", "Moody's", "MCO", 1),
    ("S&P글로벌", "S&P Global", "SPGI", 1),
    ("아메리칸익스프레스", "American Express", "AXP", 1),
    ("골드만삭스", "Goldman Sachs", "GS", 1),
    ("모건스탠리", "Morgan Stanley", "MS", 1),
    ("웰스파고", "Wells Fargo", "WFC", 1),
    ("뱅크오브아메리카", "Bank of America", "BAC", 1),
    ("씨티그룹", "Citigroup", "C", 1),
    ("블랙록", "BlackRock", "BLK", 1),
    ("CME그룹", "CME Group", "CME", 2),
    ("인터컨티넨탈익스체인지", "ICE", "ICE", 2),
    # 헬스케어
    ("일라이릴리", "Eli Lilly", "LLY", 1),
    ("유나이티드헬스", "UnitedHealth", "UNH", 1),
    ("존슨앤존슨", "Johnson & Johnson", "JNJ", 1),
    ("애브비", "AbbVie", "ABBV", 1),
    ("머크", "Merck", "MRK", 1),
    ("화이자", "Pfizer", "PFE", 1),
    ("써모피셔", "Thermo Fisher", "TMO", 1),
    ("애보트", "Abbott Labs", "ABT", 1),
    ("다나허", "Danaher", "DHR", 1),
    ("인튜이티브서지컬", "Intuitive Surgical", "ISRG", 1),
    ("엘레반스헬스", "Elevance Health", "ELV", 1),
    ("CVS헬스", "CVS Health", "CVS", 2),
    ("메드트로닉", "Medtronic", "MDT", 2),
    ("암젠", "Amgen", "AMGN", 2),
    ("길리어드", "Gilead Sciences", "GILD", 2),
    ("바이오젠", "Biogen", "BIIB", 2),
    ("모더나", "Moderna", "MRNA", 2),
    # 필수소비재
    ("코카콜라", "Coca-Cola", "KO", 1),
    ("펩시코", "PepsiCo", "PEP", 1),
    ("P&G", "Procter & Gamble", "PG", 1),
    ("코스트코", "Costco", "COST", 1),
    ("월마트", "Walmart", "WMT", 1),
    ("몬델리즈", "Mondelez", "MDLZ", 2),
    ("콜게이트", "Colgate-Palmolive", "CL", 2),
    ("크로거", "Kroger", "KR", 2),
    ("제너럴밀스", "General Mills", "GIS", 2),
    ("켈라노바", "Kellanova", "K", 2),
    ("허쉬", "Hershey", "HSY", 2),
    ("처치앤드와이트", "Church & Dwight", "CHD", 2),
    # 산업·소비재
    ("홈디포", "Home Depot", "HD", 1),
    ("맥도날드", "McDonald's", "MCD", 1),
    ("나이키", "Nike", "NKE", 1),
    ("스타벅스", "Starbucks", "SBUX", 1),
    ("캐터필러", "Caterpillar", "CAT", 1),
    ("허니웰", "Honeywell", "HON", 1),
    ("유니온퍼시픽", "Union Pacific", "UNP", 1),
    ("3M", "3M", "MMM", 1),
    ("GE에어로스페이스", "GE Aerospace", "GE", 1),
    ("RTX", "RTX Corp", "RTX", 1),
    ("록히드마틴", "Lockheed Martin", "LMT", 1),
    ("보잉", "Boeing", "BA", 1),
    ("유나이티드파셀서비스", "UPS", "UPS", 1),
    ("페덱스", "FedEx", "FDX", 1),
    ("에어비앤비", "Airbnb", "ABNB", 2),
    ("힐튼", "Hilton", "HLT", 2),
    ("로우스", "Lowe's", "LOW", 1),
    ("타겟", "Target", "TGT", 1),
    # IT·소프트웨어
    ("어도비", "Adobe", "ADBE", 1),
    ("세일즈포스", "Salesforce", "CRM", 1),
    ("서비스나우", "ServiceNow", "NOW", 1),
    ("인튜이트", "Intuit", "INTU", 1),
    ("어플라이드머티리얼즈", "Applied Materials", "AMAT", 1),
    ("ASML", "ASML", "ASML", 1),
    ("인텔", "Intel", "INTC", 1),
    ("AMD", "AMD", "AMD", 1),
    ("퀄컴", "Qualcomm", "QCOM", 1),
    ("마이크론", "Micron Technology", "MU", 1),
    ("텍사스인스트루먼트", "Texas Instruments", "TXN", 1),
    ("인피니언", "Infineon", "IFNNY", 2),
    ("클라우드플레어", "Cloudflare", "NET", 2),
    ("스노우플레이크", "Snowflake", "SNOW", 2),
    ("팔란티어", "Palantir", "PLTR", 2),
    ("코인베이스", "Coinbase", "COIN", 2),
    ("넷플릭스", "Netflix", "NFLX", 1),
    ("스포티파이", "Spotify", "SPOT", 2),
    ("우버", "Uber", "UBER", 1),
    ("리프트", "Lyft", "LYFT", 3),
    ("줌", "Zoom", "ZM", 2),
    ("어도비", "Adobe", "ADBE", 1),
    ("페이팔", "PayPal", "PYPL", 1),
    ("스퀘어블록", "Block", "SQ", 2),
    # 에너지
    ("엑슨모빌", "ExxonMobil", "XOM", 1),
    ("셰브론", "Chevron", "CVX", 1),
    ("코노코필립스", "ConocoPhillips", "COP", 1),
    ("슐럼버거", "Schlumberger SLB", "SLB", 2),
    ("할리버튼", "Halliburton", "HAL", 2),
    ("EOG리소시스", "EOG Resources", "EOG", 2),
    ("파이어니어내추럴리소스", "Pioneer Natural Resources", "PXD", 2),
    # 통신
    ("버라이즌", "Verizon", "VZ", 1),
    ("AT&T", "AT&T", "T", 1),
    ("T모바일", "T-Mobile", "TMUS", 1),
    ("컴캐스트", "Comcast", "CMCSA", 1),
    ("월트디즈니", "Walt Disney", "DIS", 1),
    ("워너브라더스", "Warner Bros Discovery", "WBD", 2),
    # 부동산·리츠
    ("아메리칸타워", "American Tower", "AMT", 2),
    ("프롤로지스", "Prologis", "PLD", 2),
    ("에퀴닉스", "Equinix", "EQIX", 2),
    ("사이먼프로퍼티", "Simon Property", "SPG", 2),
]

ALL_STOCKS = KR_STOCKS + US_STOCKS


def search(query: str, max_results: int = 10) -> list[dict]:
    """
    회사명(한글·영문) 부분 일치 검색.
    시총 tier 오름차순(대형주 우선)으로 정렬해서 반환.
    """
    if not query or len(query.strip()) < 1:
        return []

    q = query.strip().lower()
    results = []
    seen = set()

    for kor, eng, ticker, tier in ALL_STOCKS:
        if ticker in seen:
            continue
        if q in kor.lower() or q in eng.lower() or q in ticker.lower():
            results.append({
                "kor": kor,
                "eng": eng,
                "ticker": ticker,
                "tier": tier,
                "display": f"{kor} ({ticker})",
                "label": f"{kor}  ·  {eng}  [{ticker}]",
            })
            seen.add(ticker)

    results.sort(key=lambda x: x["tier"])
    return results[:max_results]
