from opinet_briefing.report import build_map, build_message


def _record(station_id, name, price, distance_m, rank, *, is_target=False,
            delta=None, highlight=False, lat=37.0, lon=127.0):
    return {
        "station_id": station_id,
        "name": name,
        "price": price,
        "distance_m": distance_m,
        "latitude": lat,
        "longitude": lon,
        "brand_code": "",
        "rank": rank,
        "delta": delta,
        "is_target": is_target,
        "lowest_changed": False,
        "gap_from_target_won": None,
        "is_lowest": rank == 1,
        "highlight": highlight,
    }


def _snapshot():
    five_km_records = [
        _record("s1", "1위주유소", 1790, 230, 1, delta=-3),
        _record("geolpo", "걸포주유소", 1827, 16, 2, is_target=True, delta=0),
        _record("s3", "3위주유소", 1830, 900, 3, delta=5, highlight=True),
        _record("s4", "4위주유소", 1850, 1500, 4),
        _record("s5", "5위주유소", 1860, 2100, 5),
        _record("s6", "6위주유소", 1870, 3200, 6),
        _record("s7", "7위주유소", 1880, 4800, 7),
    ]
    three_km_records = [
        _record("geolpo", "걸포주유소", 1827, 16, 1, is_target=True, delta=0),
        _record("s3", "3위주유소", 1830, 900, 2, delta=5, highlight=True),
    ]
    one_km_records = [
        _record("geolpo", "걸포주유소", 1827, 16, 1, is_target=True, delta=0),
    ]
    gasoline = {
        "product_key": "gasoline",
        "product_name": "휘발유",
        "source": "opinet",
        "radii": [
            {"radius_m": 1000, "records": one_km_records},
            {"radius_m": 3000, "records": three_km_records},
            {"radius_m": 5000, "records": five_km_records},
        ],
        "target_5km": five_km_records[1],
        "gap_to_lowest_won": 37,
        "opinion": "인하 검토",
    }
    kerosene = {
        "product_key": "kerosene",
        "product_name": "등유",
        "source": "opinet",
        "radii": [
            {"radius_m": 1000, "records": []},
            {"radius_m": 3000, "records": []},
            {"radius_m": 5000, "records": []},
        ],
        "target_5km": None,
        "gap_to_lowest_won": None,
        "opinion": "긴급 확인",
    }
    site = {
        "site_id": "geolpo",
        "site_name": "알뜰 걸포주유소",
        "address": "경기 김포시 금포로 1117-6",
        "latitude": 37.6459844,
        "longitude": 126.7066566,
        "products": [gasoline, kerosene],
    }
    return {
        "generated_at_kst": "2026-07-28T07:10:00+09:00",
        "alerts": [],
        "sites": [site],
    }


def test_build_message_includes_all_radius_top5_sections():
    message = build_message(_snapshot())
    assert "1km TOP5" in message
    assert "3km TOP5" in message
    assert "5km TOP5" in message


def test_build_message_includes_competitor_names_and_own_marker():
    message = build_message(_snapshot())
    assert "1위주유소" in message
    assert "걸포주유소" in message
    assert "[운영점]" in message


def test_build_message_marks_missing_price_data_explicitly():
    message = build_message(_snapshot())
    assert "가격 자료 없음" in message
    assert "대상 가격 미확인" in message


def test_build_message_ends_with_map_link():
    message = build_message(_snapshot())
    assert message.strip().endswith(
        "🗺 전체 지도·순위표: https://drmarkhan.github.io/opinet/"
    )


def test_build_map_html_contains_competitors_and_full_ranking_table(tmp_path):
    output_path = tmp_path / "docs" / "index.html"
    build_map(_snapshot(), output_path)
    assert output_path.exists()
    html_text = output_path.read_text(encoding="utf-8")
    for name in ["1위주유소", "걸포주유소", "3위주유소", "6위주유소", "7위주유소"]:
        assert name in html_text
    assert "가격 자료 없음" in html_text
    assert html_text.count("<table>") >= 5
