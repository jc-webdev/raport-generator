#!/usr/bin/env python3
"""
generate_map.py

Generates a PNG map showing city boundary, inner administrative/place boundaries,
and a marker at given coordinates. Includes reverse geocoding and robust fallbacks.

Usage example:
    python generate_map.py --lat 52.2319 --lon 21.0067 --output mapa.png

Requirements (see bottom of file for pip list): requests, geopandas, shapely,
matplotlib, osmnx
"""
import sys
import os
import argparse
import logging
from typing import Optional, Tuple

import requests
import tempfile
import math
import time
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, mapping
from shapely.ops import unary_union

#!/usr/bin/env python3
"""
generate_map.py

Minimal map generator: reverse geocodes a point, fetches the city boundary
via osmnx (if available) and renders a PNG with the city border and a marker.

Usage:
    python generate_map.py --lat <lat> --lon <lon> --output mapa.png

Dependencies: requests, geopandas, shapely, matplotlib, osmnx (optional but
recommended for accurate city boundaries).
"""
import sys
import os
import argparse
import logging
from typing import Optional

import requests
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.path as mpath
import numpy as np
from shapely.geometry import Point

try:
    import osmnx as ox
except Exception:
    ox = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def parse_args():
    p = argparse.ArgumentParser(description="Generate simple city map PNG with boundary and marker")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--output", type=str, default="map.png")
    return p.parse_args()


def reverse_geocode(lat: float, lon: float) -> Optional[dict]:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"format": "jsonv2", "lat": lat, "lon": lon, "addressdetails": 1}
    headers = {"User-Agent": "generate_map.py - minimal"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.warning("Reverse geocode failed: %s", e)
        return None


def get_city_name(geocode_data: Optional[dict]) -> Optional[str]:
    if not geocode_data:
        return None
    addr = geocode_data.get("address", {})
    for key in ("city", "town", "village", "municipality", "county"):
        if addr.get(key):
            return addr.get(key)
    if geocode_data.get("display_name"):
        return geocode_data.get("display_name").split(",")[0]
    return None


def fetch_city_boundary(city_name: Optional[str], lat: float, lon: float) -> Optional[gpd.GeoDataFrame]:
    if ox is None:
        logging.warning("osmnx not installed — city polygon lookup unavailable")
        return None
    queries = []
    if city_name:
        queries.append(city_name)
        queries.append(f"{city_name}, {lat}, {lon}")
    queries.append(f"{lat}, {lon}")
    for q in queries:
        try:
            logging.info("Geocoding place: %s", q)
            gdf = ox.geocoder.geocode_to_gdf(q)
            if gdf is not None and not gdf.empty:
                polys = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
                if not polys.empty:
                    try:
                        polys = polys.to_crs(epsg=4326)
                    except Exception:
                        pass
                    logging.info("Found city polygon for: %s", q)
                    return polys
        except Exception as e:
            logging.debug("geocode attempt failed for %s: %s", q, e)
    logging.warning("City polygon not found via osmnx")
    return None


ORANGE = "#FF7900"
ORANGE_FILL = "#FFF1E0"
GRAPHITE = "#000000"
ROAD_COLOR = "#8C8C8C"
RIVER_COLOR = "#5B9BD5"

MAIN_ROAD_TAGS = {"highway": ["motorway", "trunk", "primary", "secondary"]}
WATER_TAGS = {"waterway": "river", "natural": "water"}


def fetch_features(polygon, tags: dict) -> Optional[gpd.GeoDataFrame]:
    """Fetch OSM features (roads/rivers) clipped to the given polygon, if osmnx is available."""
    if ox is None or polygon is None:
        return None
    try:
        gdf = ox.features_from_polygon(polygon, tags)
        if gdf is None or gdf.empty:
            return None
        gdf = gpd.clip(gdf, polygon)
        return gdf if not gdf.empty else None
    except Exception as e:
        # WAŻNE: był poziom debug, a logger jest skonfigurowany na INFO -
        # błąd pobierania dróg/rzek (np. timeout Overpass dla całego miasta,
        # inny niż region_cache w schemacie/Sankeyu) był całkowicie
        # niewidoczny, mapa po prostu wychodziła bez nich bez śladu w konsoli.
        logging.warning("features_from_polygon failed for tags %s: %s", tags, e)
        return None


def pin_marker_path() -> mpath.Path:
    """A classic map-pin shape (circular head, tapered tail) anchored at its tip (0, 0)."""
    circle = mpath.Path.unit_circle()
    head = circle.vertices * 0.55 + np.array([0, 1.0])
    verts = np.vstack([head, [[0.22, 0.42], [0, 0], [-0.22, 0.42], head[0]]])
    codes = np.concatenate([circle.codes, [mpath.Path.LINETO, mpath.Path.LINETO, mpath.Path.LINETO, mpath.Path.CLOSEPOLY]])
    return mpath.Path(verts, codes)


def plot_map(city_gdf: Optional[gpd.GeoDataFrame], point: Point, label: str, output_path: str):
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor("white")
    city_polygon = None
    if city_gdf is not None and not city_gdf.empty:
        try:
            city_gdf.plot(ax=ax, facecolor=ORANGE_FILL, edgecolor=ORANGE, linewidth=2.5, zorder=1)
            bounds = city_gdf.total_bounds
            city_polygon = unary_union(city_gdf.geometry)
        except Exception:
            try:
                gpd.GeoSeries(city_gdf.geometry).plot(ax=ax, facecolor=ORANGE_FILL, edgecolor=ORANGE, linewidth=2.5, zorder=1)
                bounds = city_gdf.total_bounds
                city_polygon = unary_union(city_gdf.geometry)
            except Exception:
                bounds = (point.x - 0.01, point.y - 0.01, point.x + 0.01, point.y + 0.01)
    else:
        bounds = (point.x - 0.01, point.y - 0.01, point.x + 0.01, point.y + 0.01)

    rivers_gdf = fetch_features(city_polygon, WATER_TAGS)
    if rivers_gdf is not None:
        try:
            rivers_gdf.plot(ax=ax, facecolor=RIVER_COLOR, edgecolor=RIVER_COLOR, linewidth=1.5, alpha=0.6, zorder=2)
        except Exception as e:
            logging.warning("river plot failed: %s", e)

    roads_gdf = fetch_features(city_polygon, MAIN_ROAD_TAGS)
    if roads_gdf is not None:
        try:
            roads_gdf[roads_gdf.geometry.type.isin(["LineString", "MultiLineString"])].plot(
                ax=ax, color=ROAD_COLOR, linewidth=1.0, zorder=3
            )
        except Exception as e:
            logging.warning("road plot failed: %s", e)

    ax.plot(
        point.x, point.y,
        marker=pin_marker_path(), markersize=32,
        markerfacecolor="#E4002B", markeredgecolor="#7A0019", markeredgewidth=1.3,
        linestyle="none", zorder=6,
    )
    ax.set_title(label, fontsize=12, pad=12, color=GRAPHITE)
    minx, miny, maxx, maxy = bounds
    dx = maxx - minx if maxx - minx != 0 else 0.02
    dy = maxy - miny if maxy - miny != 0 else 0.02
    margin = max(dx, dy) * 0.08
    ax.set_xlim(minx - margin, maxx + margin)
    ax.set_ylim(miny - margin, maxy + margin)
    ax.axis("off")
    try:
        plt.savefig(output_path, bbox_inches="tight", dpi=300)
        logging.info("Saved map to %s", output_path)
    except Exception as e:
        logging.error("Failed to save map: %s", e)
        # Re-raise (nie tylko zaloguj) — inaczej skrypt kończy się kodem 0
        # mimo że plik PNG nigdy nie powstał, a wołający (Node) uzna to za
        # sukces i będzie próbował wstawić do raportu nieistniejący obrazek.
        raise
    finally:
        plt.close(fig)


def main():
    args = parse_args()
    lat = args.lat
    lon = args.lon
    output = args.output
    geocode = reverse_geocode(lat, lon)
    city = get_city_name(geocode)
    if city:
        logging.info("Detected city: %s", city)
    else:
        logging.info("City not detected; using point buffer for extent")

    city_gdf = None
    try:
        city_gdf = fetch_city_boundary(city, lat, lon)
    except Exception as e:
        logging.warning("fetch_city_boundary error: %s", e)

    pt = Point(lon, lat)
    if city_gdf is None or city_gdf.empty:
        buffer_deg = 0.02
        city_gdf = gpd.GeoDataFrame([{"geometry": pt.buffer(buffer_deg)}], crs="EPSG:4326")

    label = f"Lokalizacja pomiaru: {city}" if city else "Lokalizacja pomiaru: nieznana lokalizacja"
    plot_map(city_gdf, pt, label, output)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        sys.exit(1)
