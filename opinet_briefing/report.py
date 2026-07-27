from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import folium


COLORS = {"휘발유": "red", "경유": "blue", "등유": "orange", "세차비": "purple"}


def delta_text(value: int | None) -> str:
    if value is None:
        return "전일자료 없음"
    if value > 0:
        return f"+{value}원"
    return f"{value}원"


def build_message(snapshot: dict[str, Any]) -> str:
    lines = [f"⛽ 가격 브리핑 · {snapshot['generated_at_kst']}", ""]
    for site in snapshot["sites"]:
        lines.append(f"📍 {site['site_name']}")
        for product in site["products"]:
            target = product.get("target_5km")
            if target:
                marker = " ⚠️" if target.get("highlight") else ""
                lines.append(
                    f"• {product['product_name']}: {target['price']:,}원 "
                    f"(5km {target['rank']}위, 전일 {delta_text(target.get('delta'))})"
                    f"{marker} → {product['opinion']}"
                )
            else:
                lines.append(
                    f"• {product['product_name']}: 대상 가격 미확인 → 긴급 확인"
                )
            for radius in product["radii"]:
                records = sorted(
                    radius["records"],
                    key=lambda item: (item["rank"], item["distance_m"]),
                )
                if not records:
                    continue
                competitors = []
                for item in records[:5]:
                    owned = " [운영점]" if item.get("is_target") else ""
                    change = delta_text(item.get("delta"))
                    competitors.append(
                        f"{item['rank']}위 {item['name']} {item['price']:,}원"
                        f"·{item['distance_m']:.0f}m·{change}{owned}"
                    )
                lines.append(
                    f"  └ {radius['radius_m']//1000}km TOP5: "
                    + " / ".join(competitors)
                )
        lines.append("")
    if snapshot.get("alerts"):
        lines.append("🚨 주요 변화")
        lines.extend(f"• {alert}" for alert in snapshot["alerts"][:12])
    lines.append("")
    lines.append("🗺 전체 지도·순위표: https://drmarkhan.github.io/opinet/")
    return "\n".join(lines)


def build_map(snapshot: dict[str, Any], output_path: Path) -> None:
    center_lat = sum(s["latitude"] for s in snapshot["sites"]) / len(snapshot["sites"])
    center_lon = sum(s["longitude"] for s in snapshot["sites"]) / len(snapshot["sites"])
    map_obj = folium.Map(
        location=[center_lat, center_lon], zoom_start=10, tiles="CartoDB positron"
    )
    seen: set[tuple[str, str, int, str]] = set()
    for site in snapshot["sites"]:
        folium.Marker(
            [site["latitude"], site["longitude"]],
            tooltip=f"운영 주유소: {site['site_name']}",
            icon=folium.Icon(color="green", icon="star"),
        ).add_to(map_obj)
        for radius_m in (1000, 3000, 5000):
            folium.Circle(
                [site["latitude"], site["longitude"]],
                radius=radius_m,
                color="#64748b",
                weight=1,
                fill=False,
                tooltip=f"{site['site_name']} {radius_m // 1000}km",
            ).add_to(map_obj)
        for product in site["products"]:
            for radius in product["radii"]:
                layer_name = (
                    f"{site['site_name']} · {product['product_name']} · "
                    f"{radius['radius_m'] // 1000}km"
                )
                layer = folium.FeatureGroup(name=layer_name, show=radius["radius_m"] == 5000)
                for item in radius["records"]:
                    key = (
                        site["site_id"],
                        product["product_key"],
                        radius["radius_m"],
                        item["station_id"],
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    change = delta_text(item.get("delta"))
                    popup = (
                        f"<b>{html.escape(item['name'])}</b><br>"
                        f"{product['product_name']} {item['rank']}위 · "
                        f"{item['price']:,}원<br>"
                        f"직선거리 {item['distance_m']:.0f}m · 전일 {change}"
                    )
                    folium.CircleMarker(
                        [item["latitude"], item["longitude"]],
                        radius=7 if item.get("is_target") else 4,
                        color=COLORS.get(product["product_name"], "gray"),
                        fill=True,
                        fill_opacity=0.9 if item.get("highlight") else 0.55,
                        popup=folium.Popup(popup, max_width=340),
                        tooltip=f"{item['rank']}위 {item['name']} {item['price']:,}원",
                    ).add_to(layer)
                layer.add_to(map_obj)
    folium.LayerControl(collapsed=True).add_to(map_obj)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    map_obj.save(str(output_path))

    # Folium이 만든 지도 아래에 반경별 상세 테이블을 붙인다.
    table_parts = [
        """
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#172033}
.briefing{max-width:1500px;margin:24px auto;padding:0 20px 60px}
.briefing h1{font-size:28px}.briefing h2{margin-top:36px}
.briefing h3{margin-top:24px}.briefing table{width:100%;border-collapse:collapse;
font-size:14px;margin:10px 0 24px}.briefing th,.briefing td{border-bottom:1px solid #ddd;
padding:8px;text-align:right}.briefing th:first-child,.briefing td:first-child{text-align:left}
.briefing tr.highlight{background:#fff1b8;font-weight:700}
.briefing tr.target{outline:2px solid #16803c;outline-offset:-2px}
.muted{color:#667085}.opinion{font-weight:700}
</style>
<section class="briefing">
""",
        f"<h1>오피넷 가격 브리핑</h1><p>{html.escape(snapshot['generated_at_kst'])}</p>",
    ]
    for site in snapshot["sites"]:
        table_parts.append(f"<h2>{html.escape(site['site_name'])}</h2>")
        table_parts.append(f"<p class='muted'>{html.escape(site['address'])}</p>")
        for product in site["products"]:
            gap = product.get("gap_to_lowest_won")
            gap_text = "미확인" if gap is None else f"{gap:+,}원"
            table_parts.append(
                f"<h3>{html.escape(product['product_name'])} "
                f"<span class='opinion'>→ {html.escape(product['opinion'])}</span></h3>"
                f"<p>5km 최저가 대비 운영점 차이: {gap_text}</p>"
            )
            for radius in product["radii"]:
                table_parts.append(f"<h4>반경 {radius['radius_m']//1000}km</h4>")
                table_parts.append(
                    "<table><thead><tr><th>주유소명</th><th>순위</th><th>가격</th>"
                    "<th>직선거리</th><th>전일 차이</th></tr></thead><tbody>"
                )
                if not radius["records"]:
                    table_parts.append(
                        "<tr><td colspan='5'>가격 자료 없음</td></tr>"
                    )
                for item in radius["records"]:
                    classes = []
                    if item.get("highlight"):
                        classes.append("highlight")
                    if item.get("is_target"):
                        classes.append("target")
                    table_parts.append(
                        f"<tr class='{' '.join(classes)}'>"
                        f"<td>{html.escape(item['name'])}</td>"
                        f"<td>{item['rank']}</td><td>{item['price']:,}원</td>"
                        f"<td>{item['distance_m']:.0f}m</td>"
                        f"<td>{html.escape(delta_text(item.get('delta')))}</td></tr>"
                    )
                table_parts.append("</tbody></table>")
    table_parts.append("</section>")
    document = output_path.read_text(encoding="utf-8")
    tables = "\n".join(table_parts)
    if "</body>" in document:
        document = document.replace("</body>", f"{tables}\n</body>", 1)
    else:
        document += tables
    output_path.write_text(document, encoding="utf-8")
