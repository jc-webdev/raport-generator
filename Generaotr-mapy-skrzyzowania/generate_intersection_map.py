#!/usr/bin/env python3
"""
generate_intersection_map.py

Generuje mapkę PNG skrzyżowania z etykietami wlotów wg stron świata
(nazwa ulicy + kierunek), w stylu Orange.

Użycie:
    python3 generate_intersection_map.py --lat 52.9895245606357 --lon 18.635362309395227 --output mapa.png

Wymaga: osmnx, geopandas, shapely, matplotlib (już w venv generator-mapek).
"""
import argparse
import logging
import math
import time
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import osmnx as ox
from shapely.geometry import Point, box

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Publiczny overpass-api.de bywa niedostępny na całe minuty (nie tylko wolny —
# realnie nie odpowiada, co potwierdza też zwykły curl w tym samym oknie
# czasowym). Retry na tym samym serwerze wtedy nie pomaga, więc próbujemy po
# kolei kilku niezależnych luster Overpass.
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api",
    "https://overpass.kumi.systems/api",
    "https://overpass.private.coffee/api",
    "https://maps.mail.ru/osm/tools/overpass/api",
]
ox.settings.requests_timeout = 45


def fetch_graph_from_point(*args, retries_per_mirror=2, delay=5, **kwargs):
    last_error = None
    for mirror in OVERPASS_MIRRORS:
        ox.settings.overpass_url = mirror
        for attempt in range(1, retries_per_mirror + 1):
            try:
                return ox.graph_from_point(*args, **kwargs)
            except Exception as e:
                last_error = e
                logging.warning("%s próba %d/%d nieudana (%s)", mirror, attempt, retries_per_mirror, e)
                time.sleep(delay)
    raise SystemExit(
        f"Nie udało się pobrać danych z OpenStreetMap — żadne z {len(OVERPASS_MIRRORS)} luster "
        f"Overpass nie odpowiedziało. Ostatni błąd: {last_error}\nSpróbuj ponownie za chwilę."
    )


GRAPHITE = "#333333"
ROAD_COLOR = "#B5B5B5"
ROAD_HIGHLIGHT = "#F16E00"
BG = "#F2EFE9"  # ciepły, stonowany odcień terenu (jak domyślne tło Google Maps) —
                # zamiast bieli, żeby brak konkretnego tagu landuse w OSM (pole,
                # nieużytek) nie wyglądał jak dziura w mapie
LABEL_COLORS = ["#0087C1", "#FF7900", "#2E8B57", "#5B4B8A", "#C1272D"]

# Szerokie sektory kardynalne (N/E/S/W), wąskie ukośne tylko blisko dokładnych 45°
DIRECTION_SECTORS = [
    (35, "Północny"), (55, "Północno-Wschodni"), (125, "Wschodni"),
    (145, "Południowo-Wschodni"), (215, "Południowy"), (235, "Południowo-Zachodni"),
    (305, "Zachodni"), (325, "Północno-Zachodni"), (360, "Północny"),
]


def bearing(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def direction_name(brg):
    b = brg % 360
    for upper, name in DIRECTION_SECTORS:
        if b < upper:
            return name
    return "Północny"


def edge_name(data):
    name = data.get("name", "Droga bez nazwy")
    if isinstance(name, list):
        name = name[0]
    return name


def point_along(coords, target_dist):
    """Punkt leżący dokładnie na polilinii `coords` (lista (x,y), start=coords[0]),
    w odległości target_dist (w stopniach) od początku — żeby znacznik pokrywał się
    z narysowaną drogą, a nie z linią prostą do węzła końcowego."""
    remaining = target_dist
    for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
        seg_len = math.hypot(x2 - x1, y2 - y1)
        if seg_len >= remaining:
            frac = remaining / seg_len if seg_len else 0
            return (x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac)
        remaining -= seg_len
    return coords[-1]


# Tereny tła (tak jak Google barwi mapę) — bez tego np. las/park/woda to po
# prostu biała dziura w kadrze, przez którą kadr "ucieka" w puste miejsce.
LANDUSE_TAGS = {
    "natural": ["wood", "water", "wetland", "scrub", "grassland"],
    "landuse": ["forest", "meadow", "farmland", "grass", "orchard", "cemetery", "allotments"],
    "leisure": ["park", "garden", "nature_reserve", "pitch"],
}
LANDUSE_COLORS = {
    "wood": "#D3E6C9", "forest": "#D3E6C9", "scrub": "#DCEBD1",
    "water": "#BEE0F1", "wetland": "#CFE7EE",
    "grassland": "#E3EFD8", "meadow": "#E3EFD8", "grass": "#E3EFD8",
    "farmland": "#EDF0E0", "orchard": "#E3EFD8", "allotments": "#E3EFD8",
    "park": "#DDEDD3", "garden": "#DDEDD3", "nature_reserve": "#D3E6C9", "pitch": "#CDE7C8",
    "cemetery": "#E3E6DC",
}


def _landuse_color(row):
    for col in ("natural", "landuse", "leisure"):
        val = row.get(col)
        if val in LANDUSE_COLORS:
            return LANDUSE_COLORS[val]
    return "#E5EDE0"


def load_or_fetch_region(cache_dir, lat, lon, radius):
    """Sieć drogowa (drive + all), budynki i tereny (lasy/parki/wody) dla całego
    regionu, pobrane RAZ i zcache'owane na dysku — kolejne skrzyżowania w tym
    samym mieście czytają z dysku, zero zapytań do Overpass. Klucz do
    generowania masy punktów bez zależności od niestabilnego publicznego API."""
    cache_dir = Path(cache_dir)
    drive_path = cache_dir / "region_drive.graphml"
    all_path = cache_dir / "region_all.graphml"
    buildings_path = cache_dir / "region_buildings.gpkg"
    landuse_path = cache_dir / "region_landuse.gpkg"

    if drive_path.exists() and all_path.exists():
        logging.info("Wczytuję zcache'owany region z %s (bez sieci)", cache_dir)
        G_drive = ox.load_graphml(drive_path)
        G_all = ox.load_graphml(all_path)
        buildings = gpd.read_file(buildings_path) if buildings_path.exists() else None
        if landuse_path.exists():
            landuse = gpd.read_file(landuse_path)
        else:
            landuse = _fetch_landuse(lat, lon, radius, landuse_path)
        return G_drive, G_all, buildings, landuse

    cache_dir.mkdir(parents=True, exist_ok=True)
    logging.info("Brak cache w %s — pobieram region (promień %dm) z OSM jednorazowo...", cache_dir, radius)
    G_drive = fetch_graph_from_point((lat, lon), dist=radius, network_type="drive", simplify=True)
    G_all = fetch_graph_from_point((lat, lon), dist=radius, network_type="all", simplify=True)
    ox.save_graphml(G_drive, drive_path)
    ox.save_graphml(G_all, all_path)

    buildings = None
    try:
        buildings = ox.features_from_point((lat, lon), tags={"building": True}, dist=radius)
        buildings = buildings[buildings.geometry.type.isin(["Polygon", "MultiPolygon"])][["geometry"]]
        buildings.to_file(buildings_path, driver="GPKG")
    except Exception as e:
        logging.warning("Nie udało się pobrać budynków dla regionu: %s", e)

    landuse = _fetch_landuse(lat, lon, radius, landuse_path)

    logging.info("Region zapisany w %s — kolejne punkty w tym obszarze pójdą bez sieci.", cache_dir)
    return G_drive, G_all, buildings, landuse


def _fetch_landuse(lat, lon, radius, save_path):
    try:
        landuse = ox.features_from_point((lat, lon), tags=LANDUSE_TAGS, dist=radius)
        landuse = landuse[landuse.geometry.type.isin(["Polygon", "MultiPolygon"])]
        # Duże relacje OSM (rzeka, kompleks leśny) bywają zwracane z pełną
        # geometrią wykraczającą daleko poza zapytany obszar — przycinamy do
        # bboxa, inaczej pojedynczy wielokąt potrafi zaburzyć cały widok.
        west, south, east, north = ox.utils_geo.bbox_from_point((lat, lon), dist=radius)
        landuse = gpd.clip(landuse, box(west, south, east, north))
        keep_cols = [c for c in ("natural", "landuse", "leisure") if c in landuse.columns]
        landuse = landuse[keep_cols + ["geometry"]]
        landuse["_color"] = landuse.apply(_landuse_color, axis=1)
        landuse.to_file(save_path, driver="GPKG")
        return landuse
    except Exception as e:
        logging.warning("Nie udało się pobrać terenów (lasy/parki/wody) dla regionu: %s", e)
        return None


def clip_polyline(coords, max_dist):
    """Przycina polilinię `coords` (start=coords[0]) do długości max_dist —
    używane, żeby wlot na rysunku sięgał kawałek za skrzyżowanie, a nie aż do
    następnego prawdziwego skrzyżowania (które przy simplify=True na grafie
    całego regionu bywa kilometr dalej)."""
    out = [coords[0]]
    remaining = max_dist
    for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
        seg_len = math.hypot(x2 - x1, y2 - y1)
        if seg_len >= remaining:
            frac = remaining / seg_len if seg_len else 0
            out.append((x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac))
            return out
        out.append((x2, y2))
        remaining -= seg_len
    return out


def find_arms(G, lat, lon, max_arm_dist_m=250, bearing_sample_m=18):
    """Zwraca (center_node, arms) dla skrzyżowania najbliższego (lat, lon) w grafie G."""
    max_arm_dist_deg = max_arm_dist_m / 111_000
    bearing_sample_deg = bearing_sample_m / 111_000
    # Graf nieskierowany do wykrywania topologii (stopnia węzła) i wlotów — inaczej
    # ulice jednokierunkowe wchodzące DO skrzyżowania (bez krawędzi wychodzącej z
    # danego węzła) w ogóle by się nie pojawiły jako wloty.
    Gu = G.to_undirected()

    # Gęste skrzyżowania (wysepki, przejścia dla pieszych, pasy skrętu) w OSM bywają
    # zbudowane z kilku bliskich węzłów — zwykły "najbliższy węzeł" łatwo trafia w
    # ślepy zaułek/wysepkę zamiast w prawdziwe skrzyżowanie. Dlatego szukamy
    # najbliższego węzła, który realnie ma 3+ dróg, i dopiero gdy takiego brak,
    # cofamy się do zwykłego najbliższego węzła.
    coslat = math.cos(math.radians(lat))

    def dist2(n):
        dy = G.nodes[n]["y"] - lat
        dx = (G.nodes[n]["x"] - lon) * coslat
        return dx * dx + dy * dy

    junctions = [n for n in G.nodes if Gu.degree(n) >= 3]
    center_node = min(junctions or G.nodes, key=dist2)
    center_x, center_y = G.nodes[center_node]["x"], G.nodes[center_node]["y"]

    snap_dist_m = math.sqrt(dist2(center_node)) * 111_000  # zgrubne stopnie->metry
    if snap_dist_m > 60:
        logging.warning(
            "Najbliższe skrzyżowanie jest ~%.0fm od podanych współrzędnych — "
            "sprawdź, czy to na pewno ten punkt (albo czy mieści się w zcache'owanym regionie).",
            snap_dist_m,
        )

    arms = []
    seen_far = set()
    for u, v, data in Gu.edges(center_node, data=True):
        far_node = v if u == center_node else u
        if far_node == center_node or far_node in seen_far:
            continue
        seen_far.add(far_node)

        far_lat, far_lon = G.nodes[far_node]["y"], G.nodes[far_node]["x"]

        geom = data.get("geometry")
        if geom is not None:
            coords = list(geom.coords)
            if math.hypot(coords[0][0] - center_x, coords[0][1] - center_y) > \
               math.hypot(coords[-1][0] - center_x, coords[-1][1] - center_y):
                coords = coords[::-1]
        else:
            coords = [(center_x, center_y), (far_lon, far_lat)]

        # Kierunek liczymy z geometrii TUŻ przy skrzyżowaniu (kilkanaście metrów),
        # nie do odległego węzła topologicznego — przy simplify=True na grafie
        # regionu najbliższy węzeł bywa daleko za zakrętem drogi, więc kierunek
        # "do węzła" bywa zupełnie inny niż kierunek, w którym droga faktycznie
        # odchodzi od skrzyżowania.
        near_x, near_y = point_along(coords, bearing_sample_deg)
        brg = bearing(lat, lon, near_y, near_x)

        name = edge_name(data)
        if name == "Droga bez nazwy":
            # Sam odcinek przy skrzyżowaniu bywa nienazwaną krótką wstawką (np.
            # przy wyspie/pasie skrętu) — nazwa tej samej ulicy pojawia się dopiero
            # na kolejnym węźle. Patrzymy tam i bierzemy krawędź kontynuującą ten
            # sam kierunek (nie zawracającą do skrzyżowania).
            # Kierunek "dojścia" do far_node (a nie styczna sprzed setek metrów
            # przy skrzyżowaniu) — dla zakrzywionej wstawki liczy się to, gdzie
            # droga faktycznie zmierza tuż przed tym węzłem.
            arrival_x, arrival_y = point_along(coords[::-1], bearing_sample_deg)
            arrival_brg = bearing(arrival_y, arrival_x, far_lat, far_lon)

            best = None
            for u2, v2, data2 in Gu.edges(far_node, data=True):
                nxt = v2 if u2 == far_node else u2
                if nxt == center_node:
                    continue
                nxt_name = edge_name(data2)
                if nxt_name == "Droga bez nazwy":
                    continue
                nxt_brg = bearing(far_lat, far_lon, G.nodes[nxt]["y"], G.nodes[nxt]["x"])
                db = abs(nxt_brg - arrival_brg) % 360
                db = min(db, 360 - db)
                if best is None or db < best[0]:
                    best = (db, nxt_name, nxt, data2)
            if best and best[0] < 60:
                _, name, nxt, data2 = best
                # Doklejamy też geometrię tego dalszego odcinka — inaczej wlot
                # rysowałby się tylko na długość krótkiej nienazwanej wstawki
                # (czasem kilkanaście metrów), rażąco krótszy niż inne wloty.
                geom2 = data2.get("geometry")
                if geom2 is not None:
                    coords2 = list(geom2.coords)
                    if math.hypot(coords2[0][0] - far_lon, coords2[0][1] - far_lat) > \
                       math.hypot(coords2[-1][0] - far_lon, coords2[-1][1] - far_lat):
                        coords2 = coords2[::-1]
                else:
                    coords2 = [(far_lon, far_lat), (G.nodes[nxt]["x"], G.nodes[nxt]["y"])]
                coords = coords + coords2[1:]

        if math.hypot(coords[-1][0] - center_x, coords[-1][1] - center_y) > max_arm_dist_deg:
            coords = clip_polyline(coords, max_arm_dist_deg)

        arms.append({
            "direction": direction_name(brg),
            "name": name,
            "bearing": brg,
            "far": coords[-1],
            "coords": coords,
        })

    # Gdy jeden wlot nie ma nazwy w OSM, a wlot leżący "na wprost" (różnica
    # kierunku bliska 180°) ma nazwę — to zwykle ta sama ulica przechodząca
    # przez skrzyżowanie, więc przejmujemy nazwę.
    for arm in arms:
        if arm["name"] != "Droga bez nazwy":
            continue
        for other in arms:
            if other is arm or other["name"] == "Droga bez nazwy":
                continue
            db = abs(arm["bearing"] - other["bearing"]) % 360
            db = min(db, 360 - db)
            if abs(db - 180) < 30:
                arm["name"] = other["name"]
                break

    return center_node, arms


def _resolve_label_collisions(fig, ax, labels, iterations=40, pad_px=4):
    """Rozsuwa etykiety na podstawie NAPRAWDĘ wyrenderowanych ramek (nie
    zgadywania kąta/odległości) — inaczej boxy nakładają się na siebie albo
    wychodzą poza kadr, gdy kilka wlotów trafi blisko siebie na ekranie."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def bbox(txt):
        return txt.get_window_extent(renderer)

    def shift_px(txt, dx, dy):
        x, y = txt.get_position()
        disp = ax.transData.transform((x, y))
        new_data = ax.transData.inverted().transform((disp[0] + dx, disp[1] + dy))
        txt.set_position((new_data[0], new_data[1]))

    ax_bbox = ax.get_window_extent(renderer)
    for _ in range(iterations):
        moved = False

        for lab in labels:
            b = bbox(lab["text"])
            dx = dy = 0
            if b.x0 < ax_bbox.x0 + pad_px:
                dx = (ax_bbox.x0 + pad_px) - b.x0
            elif b.x1 > ax_bbox.x1 - pad_px:
                dx = (ax_bbox.x1 - pad_px) - b.x1
            if b.y0 < ax_bbox.y0 + pad_px:
                dy = (ax_bbox.y0 + pad_px) - b.y0
            elif b.y1 > ax_bbox.y1 - pad_px:
                dy = (ax_bbox.y1 - pad_px) - b.y1
            if dx or dy:
                shift_px(lab["text"], dx, dy)
                moved = True

        boxes = [bbox(lab["text"]) for lab in labels]
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                bi, bj = boxes[i], boxes[j]
                if bi.x0 - pad_px < bj.x1 and bi.x1 + pad_px > bj.x0 and \
                   bi.y0 - pad_px < bj.y1 and bi.y1 + pad_px > bj.y0:
                    moved = True
                    cix, ciy = (bi.x0 + bi.x1) / 2, (bi.y0 + bi.y1) / 2
                    cjx, cjy = (bj.x0 + bj.x1) / 2, (bj.y0 + bj.y1) / 2
                    vx, vy = cjx - cix, cjy - ciy
                    if vx == 0 and vy == 0:
                        vx = 1
                    norm = math.hypot(vx, vy)
                    ux, uy = vx / norm, vy / norm
                    shift_px(labels[i]["text"], -ux * 3, -uy * 3)
                    shift_px(labels[j]["text"], ux * 3, uy * 3)

        if not moved:
            break
        fig.canvas.draw()

    for lab in labels:
        ax_, ay_ = lab["anchor"]
        lx, ly = lab["text"].get_position()
        lab["line"].set_data([ax_, lx], [ay_, ly])


def draw_base_layers(ax, G, center, context_graph=None, buildings=None, landuse=None):
    """Tło mapki (tereny, budynki, sieć drogowa kontekstu i lokalna, kropka
    skrzyżowania) — wspólne dla mapki bazowej i diagramów natężeń, żeby oba
    wyglądały jak ta sama rodzina rysunków zamiast dwóch różnych stylów."""
    if landuse is not None and not landuse.empty:
        try:
            for color, group in landuse.groupby("_color"):
                group.plot(ax=ax, facecolor=color, edgecolor="none", zorder=-1)
        except Exception as e:
            logging.debug("landuse plot failed: %s", e)

    if buildings is not None and not buildings.empty:
        try:
            polys = buildings[buildings.geometry.type.isin(["Polygon", "MultiPolygon"])]
            polys.plot(ax=ax, facecolor="#ECECEC", edgecolor="#D8D8D8", linewidth=0.5, zorder=0)
        except Exception as e:
            logging.debug("buildings plot failed: %s", e)

    if context_graph is not None:
        try:
            ox.plot_graph(
                context_graph, ax=ax, show=False, close=False, node_size=0,
                edge_color="#DADADA", edge_linewidth=1.2, bgcolor=BG,
            )
        except Exception as e:
            logging.debug("context graph plot failed: %s", e)

    ox.plot_graph(
        G, ax=ax, show=False, close=False, node_size=0,
        edge_color=ROAD_COLOR, edge_linewidth=3.0, bgcolor=BG,
    )

    cx, cy = center.x, center.y
    ax.plot(cx, cy, marker="o", markersize=11, color=GRAPHITE, zorder=6,
             markeredgecolor="white", markeredgewidth=1.5)
    return cx, cy


def plot_intersection(G, center, arms, output_path, context_graph=None, buildings=None, landuse=None,
                       aspect=(4, 3), view_radius_deg=150 / 111_000):
    fig, ax = plt.subplots(figsize=(9, 9 * aspect[1] / aspect[0]))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    cx, cy = draw_base_layers(ax, G, center, context_graph, buildings, landuse)

    # Etykieta każdego wlotu siada tuż za jego własnym końcem (a nie na jednym
    # globalnym promieniu) — skrzyżowania typu "T" czy asymetryczne wloty nie
    # marnują wtedy połowy kadru na pustą stronę bez dróg.
    # Gdy kilka wlotów ma zbliżony kierunek (< 50° różnicy), ich etykiety by się
    # nałożyły (samo odsunięcie promienia nie rozdziela punktów leżących na
    # niemal tej samej półprostej) — więc w takiej grupie rozstawiamy je
    # wachlarzowo na kilka stopni od siebie zamiast dalej wzdłuż tego samego kierunku.
    order = sorted(range(len(arms)), key=lambda i: arms[i]["bearing"])
    clusters, current = [], [order[0]]
    for k in range(1, len(order)):
        i, prev_i = order[k], order[k - 1]
        db = abs(arms[i]["bearing"] - arms[prev_i]["bearing"]) % 360
        db = min(db, 360 - db)
        if db < 50:
            current.append(i)
        else:
            clusters.append(current)
            current = [i]
    clusters.append(current)

    label_angle = {}
    for cluster in clusters:
        base = sum(arms[i]["bearing"] for i in cluster) / len(cluster)
        spread = min(45, 16 * (len(cluster) - 1))
        for k, i in enumerate(cluster):
            offset = -spread / 2 + (spread * k / (len(cluster) - 1) if len(cluster) > 1 else 0)
            label_angle[i] = base + offset

    # Kadr to STAŁY promień wokół skrzyżowania (niezależny od tego, jak daleko
    # akurat sięga najdłuższy wlot) — bo dociąganie zasięgu do najdłuższego
    # wlotu potrafi wyjść poza zabudowany obszar (puste pole) i zostawić białe
    # pasy. Stały, umiarkowany promień prawie zawsze trafia w gęstą okolicę.
    target_ratio = aspect[0] / aspect[1]
    half_h = view_radius_deg
    half_w = half_h * target_ratio
    ax.set_xlim(cx - half_w, cx + half_w)
    ax.set_ylim(cy - half_h, cy + half_h)
    # ox.plot_graph() (wywołane wyżej dla G/context_graph) przelicza kształt
    # PROSTOKĄTA OSI na podstawie SWOJEGO grafu (cały region, kilometry) i go
    # zwęża/dopasowuje — nasze set_xlim/set_ylim zmieniają tylko zakres danych,
    # nie przywracają already-zwężonego prostokąta. Stąd tło figury prześwitywało
    # po bokach mimo poprawnego xlim/ylim. Wymuszamy ponowne przeliczenie na
    # podstawie NASZEGO właściwego widoku.
    ax.set_aspect("equal", adjustable="box")

    # Etykiety zawsze mieszczą się w kadrze — ale odległość do krawędzi ZALEŻY OD
    # KIERUNKU: pozioma etykieta może odjechać aż do half_w (szerokość), pionowa
    # tylko do half_h (wysokość). Wcześniej capping brał min(half_w, half_h) dla
    # WSZYSTKICH etykiet, więc poszerzenie proporcji (np. z 4:3 na 3:2) w ogóle
    # nie dawało etykietom więcej miejsca w bok — tylko dokładało tło.
    def rect_edge_dist(angle_deg):
        rad = math.radians(angle_deg)
        sx, sy = abs(math.sin(rad)), abs(math.cos(rad))
        candidates = []
        if sx > 1e-9:
            candidates.append(half_w / sx)
        if sy > 1e-9:
            candidates.append(half_h / sy)
        return min(candidates) if candidates else min(half_w, half_h)

    dists = [math.hypot(a["far"][0] - cx, a["far"][1] - cy) for a in arms]
    label_dist_caps = [rect_edge_dist(label_angle[i]) * 0.85 for i in range(len(arms))]
    global_min_cap = min(label_dist_caps) if label_dist_caps else min(half_w, half_h) * 0.85

    label_positions = []
    for i, arm in enumerate(arms):
        min_label_dist = min(max(dists) * 0.5, global_min_cap) if dists else global_min_cap
        dist = min(max(dists[i], min_label_dist) * 1.25, label_dist_caps[i])
        rad = math.radians(label_angle[i])
        label_positions.append((cx + dist * math.sin(rad), cy + dist * math.cos(rad)))

    labels = []
    for i, arm in enumerate(arms):
        color = LABEL_COLORS[i % len(LABEL_COLORS)]
        lx, ly = label_positions[i]

        # Per-wlot, nie globalna odległość — inaczej przy ciasnym kadrze punkt
        # na krótszym wlocie (liczony ułamkiem NAJDŁUŻSZEGO wlotu) wypada poza
        # widoczną ramką i linia-odnośnik po prostu znika.
        anchor_dist = min(dists[i] * 0.55, label_dist_caps[i] * 0.9)
        anchor_x, anchor_y = point_along(arm["coords"], anchor_dist)

        line, = ax.plot([anchor_x, lx], [anchor_y, ly], color=color, lw=1.8, zorder=7)
        txt = ax.text(
            lx, ly, f"{arm['name']} – Wlot {arm['direction']}",
            ha="center", va="center", fontsize=9.5, fontweight="bold", color=GRAPHITE,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=color, lw=2),
            zorder=8,
        )
        ax.plot(anchor_x, anchor_y, marker="o", markersize=7, color=color, zorder=6)
        labels.append({"text": txt, "line": line, "anchor": (anchor_x, anchor_y)})

    _resolve_label_collisions(fig, ax, labels)
    ax.axis("off")

    ax.annotate("N", xy=(0.94, 0.90), xytext=(0.94, 0.83), xycoords="axes fraction",
                ha="center", va="center", fontsize=12, fontweight="bold", color=GRAPHITE,
                arrowprops=dict(arrowstyle="-|>", color=GRAPHITE, lw=2))

    # bez tytułu/podpisu górny i dolny margines osi mogą być równe — stąd
    # margines boczny może być taki sam jak góra/dół bez psucia aspect='equal'
    margin = 0.02
    fig.subplots_adjust(left=margin, right=1 - margin, top=1 - margin, bottom=margin)
    plt.savefig(output_path, dpi=300, facecolor=BG)
    plt.close(fig)
    logging.info("Zapisano mapę do %s", output_path)


def main():
    p = argparse.ArgumentParser(description="Generuj mapkę skrzyżowania z wlotami wg stron świata (Orange)")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--output", type=str, default="mapa_skrzyzowania.png")
    p.add_argument("--aspect", type=str, default="3:2", help="proporcje obrazu, np. 3:2, 4:3 lub 16:9")
    p.add_argument("--region-cache", type=str, default="region_cache",
                    help="folder z zapisaną siecią drogową całego regionu (pobierany z OSM tylko raz)")
    p.add_argument("--region-radius", type=int, default=4000,
                    help="promień regionu w metrach, pobierany JEDNORAZOWO przy pierwszym uruchomieniu "
                         "(dobierz tak, by objąć wszystkie planowane skrzyżowania w mieście)")
    p.add_argument("--local-radius", type=int, default=150,
                    help="promień pogrubionych (podświetlonych) dróg wokół skrzyżowania na rysunku")
    p.add_argument("--view-radius", type=int, default=90,
                    help="stały promień kadru w metrach — kadr NIE zależy od długości "
                         "wlotów (te dłuższe niż promień po prostu wychodzą poza kadr, "
                         "a ich etykiety i tak zostają w środku)")
    args = p.parse_args()
    aw, ah = (float(x) for x in args.aspect.split(":"))

    G_drive, G_all, buildings, landuse = load_or_fetch_region(
        args.region_cache, args.lat, args.lon, args.region_radius)

    center_node, arms = find_arms(G_drive, args.lat, args.lon, max_arm_dist_m=args.local_radius)
    if not arms:
        raise SystemExit("Nie znaleziono dróg w pobliżu podanych współrzędnych w zcache'owanym regionie.")

    G_local = ox.truncate.truncate_graph_dist(G_drive, center_node, args.local_radius)
    center = Point(args.lon, args.lat)
    plot_intersection(G_local, center, arms, args.output, G_all, buildings, landuse, aspect=(aw, ah),
                       view_radius_deg=args.view_radius / 111_000)


if __name__ == "__main__":
    main()
