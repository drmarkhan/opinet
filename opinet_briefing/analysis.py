from __future__ import annotations

import re
from typing import Any

from .geo import haversine_m


def normalize_name(value: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", value.lower())


def competition_rank(records: list[dict[str, Any]]) -> None:
    """동일 가격은 같은 순위(competition ranking: 1, 1, 3)로 처리한다."""
    prices = sorted({int(item["price"]) for item in records})
    rank_by_price = {price: index + 1 for index, price in enumerate(prices)}
    # dense rank보다 현장 해석이 쉬운 1,1,3 순위를 위해 싼 레코드 수를 센다.
    for item in records:
        price = int(item["price"])
        item["rank"] = 1 + sum(1 for other in records if int(other["price"]) < price)


def find_target(
    records: list[dict[str, Any]], target: dict[str, Any]
) -> dict[str, Any] | None:
    names = {normalize_name(target["name"])}
    names.update(normalize_name(alias) for alias in target.get("aliases", []))
    named = [r for r in records if normalize_name(r["name"]) in names]
    candidates = named or records
    if not candidates:
        return None
    nearest = min(
        candidates,
        key=lambda r: haversine_m(
            target["latitude"],
            target["longitude"],
            r["latitude"],
            r["longitude"],
        ),
    )
    distance = haversine_m(
        target["latitude"],
        target["longitude"],
        nearest["latitude"],
        nearest["longitude"],
    )
    if distance <= float(target.get("match_radius_m", 250)):
        return nearest
    return None


def previous_index(previous: dict[str, Any] | None) -> dict[tuple, dict[str, Any]]:
    if not previous:
        return {}
    result: dict[tuple, dict[str, Any]] = {}
    for site in previous.get("sites", []):
        for product in site.get("products", []):
            for radius in product.get("radii", []):
                for record in radius.get("records", []):
                    key = (
                        site["site_id"],
                        product["product_key"],
                        radius["radius_m"],
                        record["station_id"],
                    )
                    result[key] = record
    return result


def recommendation(gap: int | None, urgent_gap: int, review_gap: int) -> str:
    if gap is None:
        return "긴급 확인"
    if gap >= urgent_gap:
        return "긴급 확인"
    if gap >= review_gap:
        return "인하 검토"
    return "유지"

