from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .analysis import competition_rank, find_target, previous_index, recommendation
from .geo import haversine_m
from .opinet import OpinetClient
from .report import build_map, build_message


ROOT = Path(__file__).resolve().parents[1]
KST = ZoneInfo("Asia/Seoul")


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as file_obj:
        return yaml.safe_load(file_obj) or {}


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as file_obj:
        return json.load(file_obj)


def atomic_json_dump(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as file_obj:
        json.dump(data, file_obj, ensure_ascii=False, indent=2)
        file_obj.write("\n")
    temporary.replace(path)


def carwash_records(
    center: dict, radius_m: int, carwash_config: dict
) -> list[dict]:
    records = []
    for station_id, item in carwash_config.get("stations", {}).items():
        if item.get("price") is None:
            continue
        distance = haversine_m(
            center["latitude"],
            center["longitude"],
            float(item["latitude"]),
            float(item["longitude"]),
        )
        if distance <= radius_m:
            records.append(
                {
                    "station_id": f"carwash:{station_id}",
                    "name": item["name"],
                    "price": int(item["price"]),
                    "distance_m": round(distance, 1),
                    "latitude": float(item["latitude"]),
                    "longitude": float(item["longitude"]),
                    "brand_code": "",
                }
            )
    return records


def create_snapshot(config: dict, carwash: dict, client: OpinetClient) -> dict:
    now = datetime.now(KST)
    previous = load_json(ROOT / "data" / "latest.json")
    prior = previous_index(previous)
    rules = config["rules"]
    threshold = int(rules["highlight_change_won"])
    snapshot = {
        "schema_version": 1,
        "generated_at_kst": now.isoformat(timespec="seconds"),
        "date_kst": now.date().isoformat(),
        "alerts": [],
        "sites": [],
    }

    product_definitions = list(config["products"].items()) + [
        ("carwash", {"name": "세차비", "opinet_code": None})
    ]
    for site in config["stations"]:
        site_result = {
            "site_id": site["id"],
            "site_name": site["name"],
            "address": site["address"],
            "latitude": site["latitude"],
            "longitude": site["longitude"],
            "products": [],
        }
        for product_key, product in product_definitions:
            product_result = {
                "product_key": product_key,
                "product_name": product["name"],
                "source": "manual" if product_key == "carwash" else "opinet",
                "radii": [],
            }
            for radius_m in config["radii_m"]:
                if product_key == "carwash":
                    records = carwash_records(site, radius_m, carwash)
                else:
                    records = [
                        record.as_dict()
                        for record in client.around(
                            site["latitude"],
                            site["longitude"],
                            int(radius_m),
                            product["opinet_code"],
                        )
                    ]
                competition_rank(records)
                target = find_target(records, site)
                cheapest_ids = {
                    record["station_id"]
                    for record in records
                    if records and record["price"] == min(r["price"] for r in records)
                }
                old_cheapest_ids = set()
                for key, old in prior.items():
                    if (
                        key[0] == site["id"]
                        and key[1] == product_key
                        and key[2] == int(radius_m)
                        and old.get("rank") == 1
                    ):
                        old_cheapest_ids.add(old["station_id"])
                lowest_changed = bool(old_cheapest_ids) and cheapest_ids != old_cheapest_ids
                if lowest_changed:
                    snapshot["alerts"].append(
                        f"{site['name']} {product['name']} {int(radius_m)//1000}km "
                        "최저가 주유소 변경"
                    )
                for item in records:
                    key = (site["id"], product_key, int(radius_m), item["station_id"])
                    old = prior.get(key)
                    item["delta"] = (
                        item["price"] - int(old["price"]) if old is not None else None
                    )
                    item["is_target"] = bool(
                        target and item["station_id"] == target["station_id"]
                    )
                    item["lowest_changed"] = lowest_changed
                    target_gap = (
                        abs(int(item["price"]) - int(target["price"]))
                        if target is not None
                        else None
                    )
                    item["gap_from_target_won"] = target_gap
                    item["is_lowest"] = item["station_id"] in cheapest_ids
                    item["highlight"] = (
                        item["is_lowest"]
                        or (target_gap is not None and target_gap >= threshold)
                        or lowest_changed
                        or (
                            item["delta"] is not None
                            and abs(item["delta"]) >= threshold
                        )
                    )
                    if item["delta"] is not None and abs(item["delta"]) >= threshold:
                        snapshot["alerts"].append(
                            f"{site['name']} {product['name']} {int(radius_m)//1000}km "
                            f"{item['name']} {item['delta']:+d}원"
                        )
                product_result["radii"].append(
                    {"radius_m": int(radius_m), "records": records}
                )

            five_km = next(
                radius for radius in product_result["radii"] if radius["radius_m"] == 5000
            )
            target_5km = find_target(five_km["records"], site)
            product_result["target_5km"] = target_5km
            if target_5km and five_km["records"]:
                cheapest = min(item["price"] for item in five_km["records"])
                gap = int(target_5km["price"]) - int(cheapest)
            else:
                gap = None
            product_result["gap_to_lowest_won"] = gap
            product_result["opinion"] = recommendation(
                gap,
                int(rules["urgent_gap_won"]),
                int(rules["review_gap_won"]),
            )
            site_result["products"].append(product_result)
        snapshot["sites"].append(site_result)
    snapshot["alerts"] = list(dict.fromkeys(snapshot["alerts"]))
    return snapshot


def main() -> int:
    try:
        config = load_yaml(ROOT / "config" / "stations.yml")
        carwash = load_yaml(ROOT / "config" / "carwash_prices.yml")
        client = OpinetClient(os.environ["OPINET_API_KEY"])
        snapshot = create_snapshot(config, carwash, client)
        date_key = snapshot["date_kst"]
        latest_path = ROOT / "data" / "latest.json"
        archive_path = ROOT / "data" / "history" / f"{date_key}.json"
        map_path = ROOT / "reports" / f"opinet-map-{date_key}.html"
        atomic_json_dump(snapshot, latest_path)
        atomic_json_dump(snapshot, archive_path)
        atomic_json_dump(
            {
                "status": "success",
                "generated_at_kst": snapshot["generated_at_kst"],
                "date_kst": snapshot["date_kst"],
                "message": build_message(snapshot),
                "report_file": str(map_path.relative_to(ROOT)),
            },
            ROOT / "data" / "status.json",
        )
        build_map(snapshot, map_path)
        message = build_message(snapshot)
        print(message)
        return 0
    except Exception as exc:
        error = (
            "❌ 오피넷 가격 브리핑 실행 오류\n"
            f"{type(exc).__name__}: {exc}\n"
            "GitHub Actions 로그를 확인하십시오."
        )
        logging.exception("브리핑 생성 실패")
        atomic_json_dump(
            {
                "status": "error",
                "generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
                "message": error,
            },
            ROOT / "data" / "status.json",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
