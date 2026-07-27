from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from .geo import katec_to_wgs84, wgs84_to_katec


API_URL = "https://www.opinet.co.kr/api/aroundAll.do"


class OpinetError(RuntimeError):
    pass


@dataclass(frozen=True)
class PriceRecord:
    station_id: str
    name: str
    price: int
    distance_m: float
    latitude: float
    longitude: float
    brand_code: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "station_id": self.station_id,
            "name": self.name,
            "price": self.price,
            "distance_m": round(self.distance_m, 1),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "brand_code": self.brand_code,
        }


class OpinetClient:
    def __init__(self, api_key: str, timeout_seconds: int = 30) -> None:
        if not api_key:
            raise ValueError("OPINET_API_KEY가 비어 있습니다.")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "opinet-price-briefing/1.0"

    def around(
        self,
        latitude: float,
        longitude: float,
        radius_m: int,
        product_code: str,
    ) -> list[PriceRecord]:
        if radius_m > 5000:
            raise ValueError("오피넷 반경 API의 최대 반경은 5,000m입니다.")
        x, y = wgs84_to_katec(latitude, longitude)
        params = {
            "code": self.api_key,
            "certkey": self.api_key,
            "out": "json",
            "x": x,
            "y": y,
            "radius": radius_m,
            "prodcd": product_code,
            "sort": 1,
        }
        try:
            response = self.session.get(
                API_URL, params=params, timeout=self.timeout_seconds
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise OpinetError(f"오피넷 API 호출 실패: {exc}") from exc

        oils = payload.get("RESULT", {}).get("OIL", [])
        if isinstance(oils, dict):
            oils = [oils]
        if not isinstance(oils, list):
            raise OpinetError(f"예상하지 못한 오피넷 응답 형식: {payload!r}")

        records: list[PriceRecord] = []
        for oil in oils:
            try:
                price = int(float(oil["PRICE"]))
                if price <= 0:
                    continue
                lat, lon = katec_to_wgs84(
                    float(oil["GIS_X_COOR"]), float(oil["GIS_Y_COOR"])
                )
                records.append(
                    PriceRecord(
                        station_id=str(oil["UNI_ID"]).strip(),
                        name=str(oil["OS_NM"]).strip(),
                        price=price,
                        distance_m=float(oil["DISTANCE"]),
                        latitude=lat,
                        longitude=lon,
                        brand_code=str(oil.get("POLL_DIV_CD", "")).strip(),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise OpinetError(f"주유소 레코드 해석 실패: {oil!r}") from exc
        return records

