from opinet_briefing.analysis import competition_rank, recommendation
from opinet_briefing.geo import haversine_m, wgs84_to_katec


def test_competition_rank_handles_ties():
    records = [{"price": 1700}, {"price": 1690}, {"price": 1690}, {"price": 1710}]
    competition_rank(records)
    assert [item["rank"] for item in records] == [3, 1, 1, 4]


def test_recommendation_rules():
    assert recommendation(0, 10, 3) == "유지"
    assert recommendation(3, 10, 3) == "인하 검토"
    assert recommendation(10, 10, 3) == "긴급 확인"
    assert recommendation(None, 10, 3) == "긴급 확인"


def test_geo_sanity():
    x, y = wgs84_to_katec(37.6459844, 126.7066566)
    assert 200_000 < x < 500_000
    assert 400_000 < y < 800_000
    assert haversine_m(37.0, 127.0, 37.0, 127.0) == 0

