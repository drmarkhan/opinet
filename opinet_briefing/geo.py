from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from pyproj import CRS, Transformer


# 오피넷의 KATEC(TM128/Bessel) 좌표계.
KATEC = CRS.from_proj4(
    "+proj=tmerc +lat_0=38 +lon_0=128 +k=0.9999 "
    "+x_0=400000 +y_0=600000 +ellps=bessel "
    "+towgs84=-146.43,507.89,681.46,0,0,0,0 +units=m +no_defs"
)
WGS84 = CRS.from_epsg(4326)
TO_KATEC = Transformer.from_crs(WGS84, KATEC, always_xy=True)
FROM_KATEC = Transformer.from_crs(KATEC, WGS84, always_xy=True)


def wgs84_to_katec(latitude: float, longitude: float) -> tuple[float, float]:
    x, y = TO_KATEC.transform(longitude, latitude)
    return round(x, 2), round(y, 2)


def katec_to_wgs84(x: float, y: float) -> tuple[float, float]:
    longitude, latitude = FROM_KATEC.transform(x, y)
    return latitude, longitude


def haversine_m(
    latitude1: float, longitude1: float, latitude2: float, longitude2: float
) -> float:
    radius = 6_371_000.0
    p1, p2 = radians(latitude1), radians(latitude2)
    dp = radians(latitude2 - latitude1)
    dl = radians(longitude2 - longitude1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * radius * asin(sqrt(a))

