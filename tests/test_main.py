import opinet_briefing.main as main_module
from opinet_briefing.opinet import PriceRecord


class FakeClient:
    """오피넷 API를 호출하지 않는 테스트용 클라이언트."""

    def around(self, latitude, longitude, radius_m, product_code):
        if radius_m < 3000:
            return [PriceRecord("geolpo", "걸포주유소", 1827, 16.0, latitude, longitude)]
        return [
            PriceRecord("geolpo", "걸포주유소", 1827, 16.0, latitude, longitude),
            PriceRecord("rival", "경쟁주유소", 1790, 900.0, latitude + 0.01, longitude),
        ]


def _config():
    return {
        "stations": [
            {
                "id": "geolpo",
                "name": "알뜰 걸포주유소",
                "aliases": ["걸포주유소"],
                "address": "경기 김포시 금포로 1117-6",
                "latitude": 37.6459844,
                "longitude": 126.7066566,
                "match_radius_m": 250,
            }
        ],
        "radii_m": [1000, 3000, 5000],
        "products": {
            "gasoline": {"name": "휘발유", "opinet_code": "B027"},
            "diesel": {"name": "경유", "opinet_code": "D047"},
            "kerosene": {"name": "등유", "opinet_code": "C004"},
        },
        "rules": {
            "highlight_change_won": 3,
            "urgent_gap_won": 10,
            "review_gap_won": 3,
            "target_match_radius_m": 250,
        },
    }


def test_main_generates_docs_index_html(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "ROOT", tmp_path)
    monkeypatch.setenv("OPINET_API_KEY", "dummy-not-used")
    monkeypatch.setattr(
        main_module, "load_yaml",
        lambda path: _config() if path.name == "stations.yml" else {"stations": {}},
    )
    monkeypatch.setattr(main_module, "OpinetClient", lambda api_key: FakeClient())

    exit_code = main_module.main()

    assert exit_code == 0
    map_path = tmp_path / "docs" / "index.html"
    assert map_path.exists()
    status = main_module.load_json(tmp_path / "data" / "status.json")
    assert status["status"] == "success"
    assert status["report_file"] == "docs/index.html"
    assert status["report_url"] == "https://drmarkhan.github.io/opinet/"
