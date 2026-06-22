"""advisor.py — 통화 포맷·확신도·버킷 분류 검증."""
import advisor as A
from buffett import evaluate


def test_money_format_by_currency():
    assert A.money(1234.5, "KRW") == "₩1,234"
    assert A.money(1234.5, "USD") == "$1,234.50"
    assert A.money(None, "USD") == "-"


def test_conviction_stars_shape(quality_cheap):
    v = evaluate(quality_cheap, fetch_tech=False)
    stars = A.conviction_stars(v)
    assert len(stars) == 5
    assert set(stars) <= {"★", "☆"}
    assert 1 <= stars.count("★") <= 5


def test_high_quality_cheap_gets_many_stars(quality_cheap):
    v = evaluate(quality_cheap, fetch_tech=False)
    assert A.conviction_stars(v).count("★") >= 3


def test_bucket_loss_is_avoid(loss_maker):
    v = evaluate(loss_maker, fetch_tech=False)
    assert A._bucket(v) == "avoid"


def test_advise_returns_nonempty_block(quality_cheap):
    v = evaluate(quality_cheap, fetch_tech=False)
    lines = A.advise(v)
    assert isinstance(lines, list) and len(lines) >= 3
    assert any(quality_cheap.name in ln for ln in lines)


def test_portfolio_and_temperature(quality_cheap, loss_maker):
    vs = [evaluate(quality_cheap, fetch_tech=False),
          evaluate(loss_maker, fetch_tech=False)]
    temp = A.market_temperature(vs)
    assert any("시장 온도" in t for t in temp)
    sec_map = {v.f.ticker: v.f.sector for v in vs}
    block = A.portfolio(vs, sec_map)
    assert any("포트폴리오 조언" in b for b in block)
