#!/usr/bin/env python3
"""
generate_flow_diagram.py

Diagram natężeń ruchu (ładna mapka Orange + relacje skrętne) generowany z
Quantity.csv, zamiast ręcznego eksportu z Visum. Używa tego samego tła co
generate_intersection_map.py (draw_base_layers: tereny, budynki, sieć
kontekstu, lokalna sieć, kropka skrzyżowania) i tych samych ramion
(find_arms), żeby oba rysunki wyglądały spójnie.

Styl wzorowany na oryginalnym eksporcie z Visum: ciasno skadrowana mapa,
krzywe relacji zakotwiczone na REALNEJ drodze (nie na umownym promieniu
kompasowym) blisko środka — żeby trzymały się w kadrze zamiast rozjeżdżać
się na cały obraz — kolor = typ relacji, grubość = wartość, oraz mała,
obrócona równolegle do drogi etykieta z nazwą ulicy + boks z liczbami
(Wprost/Prawo/Lewo/Zawracający w stałej kolejności), przyklejony do jezdni.

4 warianty (--metric):
    sdr       Natężenie ruchu drogowego (poj./dobę) - SDR
    upc       Udział pojazdów ciężkich w ruchu dobowym wg relacji [%]
    am_peak   Godzina szczytu porannego (7:00-8:00) [poj./h]
    pm_peak   Godzina szczytu popołudniowego (15:00-16:00) [poj./h]

Wymaga pliku mapowania JSON (jeden na punkt pomiarowy), np. mapping_p2.json:
{
  "gate_mapping": {"A": ["PD", "Prawo"], "B": ["PD", "Wprost"], ...},
  "wlot_to_arm_direction": {"PD": "Południowo-Wschodni", "WSCH": "Wschodni",
                             "ZACH": "Zachodni", "PN": "Północny"}
}
`gate_mapping` to ta sama mapa co KIERUNEK_MAPPING w drogi.ipynb (relacje:
Wprost/Prawo/Lewo/Zawracający). `wlot_to_arm_direction` łączy skrótowy kod
wlotu z NAZWĄ KIERUNKU wypisaną na bazowej mapce (mapa1/2/3.png) — bo
rzeczywisty azymut ramienia rzadko pokrywa się dokładnie z "czystym" N/E/S/W.

Użycie:
    python3 generate_flow_diagram.py --lat 52.9918949 --lon 18.6325491 \
        --csv ../drogi/Quantity.csv --mapping mapping_p2.json \
        --metric sdr --output ../assets/diagram_sdr_p2.png
"""
import argparse
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.lines
import matplotlib.patches
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
import pandas as pd
from shapely.geometry import Point

from generate_intersection_map import (
    BG, GRAPHITE, load_or_fetch_region, find_arms, draw_base_layers, bearing, point_along, clip_polyline,
    edge_name,
)

KATEGORIE_MECHANICZNE = [
    "b.moto", "c.osobowe", "c3.mikrobusy", "d.dostawcze",
    "e.ciezarowe", "f.ciezarowe.z.naczepami", "g.autobusy", "h.rolne",
]
KATEGORIE_CIEZKIE = ["e.ciezarowe", "f.ciezarowe.z.naczepami"]

METRICS = {
    "sdr": ("Natężenie ruchu drogowego (poj./dobę) – SDR", "poj./dobę", "{:,.0f}"),
    "upc": ("Udział pojazdów ciężkich w ruchu dobowym dla poszczególnych relacji – UPC", "%", "{:.1f}%"),
    "am_peak": ("Natężenie ruchu drogowego w godzinie szczytu porannego (7:00–8:00)", "poj./h", "{:,.0f}"),
    "pm_peak": ("Natężenie ruchu drogowego w godzinie szczytu popołudniowego (15:00–16:00)", "poj./h", "{:,.0f}"),
}

# Kolejność jak w opisie relacji z raportu: Wprost, Prawo, Lewo, (Zawracający jeśli występuje)
TURN_ORDER = ["Wprost", "Prawo", "Lewo", "Zawracający"]
TURN_OFFSET = {"Wprost": 0, "Prawo": 90, "Lewo": -90, "Zawracający": 180}
TURN_COLOR = {"Wprost": "#FF7900", "Prawo": "#0087C1", "Lewo": "#2E8B57", "Zawracający": "#5B4B8A"}


def compute_movements(csv_path, gate_mapping, metric):
    """Zwraca (movements, wlot_totals):
    - movements: (wlot, relacja) -> wartość metryki, sumowana po bramkach
      AISP mapujących się na tę samą (wlot, relacja) — np. zdublowane bramki
      "wprost" bez unikalnej etykiety w AISP.
    - wlot_totals: wlot -> wartość zbiorcza dla WSZYSTKICH relacji z tego
      wlotu (4. liczba w boksie, pod kreską). Dla SDR/szczytów to zwykła
      suma (poj./dobę czy poj./h sumują się sensownie). Dla UPC [%] naiwna
      suma udziałów procentowych nie miałaby sensu — liczona jest właściwa
      średnia ważona: (Σ ciężkie / Σ SDR) po wszystkich relacjach wlotu."""
    df = pd.read_csv(csv_path, sep=";", encoding="cp1250")
    df["Godzina"] = pd.to_datetime(df["Czas"]).dt.hour

    sums, wlot_raw = {}, {}
    for gate, (wlot, relacja) in gate_mapping.items():
        g = df[df["Kierunek"] == gate]
        if metric == "sdr":
            val = g[KATEGORIE_MECHANICZNE].sum().sum()
        elif metric == "am_peak":
            val = g[g["Godzina"] == 7][KATEGORIE_MECHANICZNE].sum().sum()
        elif metric == "pm_peak":
            val = g[g["Godzina"] == 15][KATEGORIE_MECHANICZNE].sum().sum()
        elif metric == "upc":
            sdr = g[KATEGORIE_MECHANICZNE].sum().sum()
            ciezkie = g[KATEGORIE_CIEZKIE].sum().sum()
            s = sums.setdefault((wlot, relacja), [0.0, 0.0])
            s[0] += ciezkie
            s[1] += sdr
            r = wlot_raw.setdefault(wlot, [0.0, 0.0])
            r[0] += ciezkie
            r[1] += sdr
            continue
        else:
            raise ValueError(f"Nieznana metryka: {metric}")
        sums[(wlot, relacja)] = sums.get((wlot, relacja), 0) + val
        wlot_raw[wlot] = wlot_raw.get(wlot, 0) + val

    if metric == "upc":
        movements = {k: (v[0] / v[1] * 100 if v[1] else 0.0) for k, v in sums.items()}
        wlot_totals = {w: (v[0] / v[1] * 100 if v[1] else 0.0) for w, v in wlot_raw.items()}
    else:
        movements, wlot_totals = sums, wlot_raw
    return movements, wlot_totals


def arm_by_direction(arms, direction_label):
    for a in arms:
        if a["direction"] == direction_label:
            return a
    raise SystemExit(
        f"Nie znaleziono ramienia o kierunku '{direction_label}' — dostępne: "
        f"{[a['direction'] for a in arms]}. Sprawdź mapę bazową (mapa*.png) i "
        f"popraw 'wlot_to_arm_direction' w pliku mapowania."
    )


def exit_arm(arms, source_arm, relacja):
    """Ramię wylotowe dla relacji (Prawo/Wprost/Lewo/Zawracający) z geometrii:
    azymut ramienia startowego + 180° (przejazd przez skrzyżowanie) +
    odchylenie skrętu, dopasowany do najbliższego azymutem RZECZYWISTEGO
    ramienia. Zawracający wypada z powrotem w to samo ramię."""
    if relacja == "Zawracający":
        return source_arm
    target = (source_arm["bearing"] + 180 + TURN_OFFSET[relacja]) % 360
    others = [a for a in arms if a is not source_arm]

    def bdist(a):
        d = abs(a["bearing"] - target) % 360
        return min(d, 360 - d)

    return min(others, key=bdist)


def road_rotation(bearing_deg):
    """Kąt obrotu tekstu (stopnie, konwencja matplotlib) tak, żeby czytało
    się go wzdłuż drogi o danym azymucie kompasowym — i zawsze do góry
    nogami w dobrą stronę (nigdy odwrócone o 180°)."""
    ang = (90 - bearing_deg + 180) % 360 - 180
    if ang > 90:
        ang -= 180
    elif ang < -90:
        ang += 180
    return ang


def offset_point(pt, bearing_deg, dist_deg):
    rad = math.radians(bearing_deg)
    return (pt[0] + dist_deg * math.sin(rad), pt[1] + dist_deg * math.cos(rad))


def curve_sign(p0, p1, desired_bearing_deg):
    """Znak krzywizny dla matplotlib `arc3` (rad dodatni wygina łuk na LEWO
    od kierunku p0->p1) tak, żeby łuk realnie wybrzuszał się w stronę
    `desired_bearing_deg` (azymut kompasowy) — a NIE stały znak per typ
    relacji, bo sens "lewo/prawo" na ekranie zależy od tego, w którą stronę
    faktycznie biegnie odcinek p0->p1 dla KONKRETNEJ pary wlot-wylot, więc
    stały znak wyginał część skrętów w złą stronę."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    perp_left = (-dy, dx)
    rad = math.radians(desired_bearing_deg)
    desired = (math.sin(rad), math.cos(rad))
    return 1 if (desired[0] * perp_left[0] + desired[1] * perp_left[1]) > 0 else -1


def _nearest_node(G, x, y, max_dist_deg):
    """Najbliższy węzeł grafu — NIE porównanie na równość współrzędnych:
    współrzędne z arm['far'] i z węzłów wczytanych z GraphML (zapis/odczyt
    XML) różnią się czasem o >1e-9 mimo że to fizycznie ten sam punkt, więc
    dokładne porównanie float zawodziło dla części ramion."""
    best, best_d = None, None
    for n, d in G.nodes(data=True):
        dd = (d["x"] - x) ** 2 + (d["y"] - y) ** 2
        if best_d is None or dd < best_d:
            best, best_d = n, dd
    if best is not None and best_d ** 0.5 <= max_dist_deg:
        return best
    return None


def extend_along_road(G, arm, target_dist_m, center_xy, travel="out", max_turn_deg=70):
    """Przedłuża polilinię wlotu (arm['coords'], start=środek skrzyżowania)
    przez KOLEJNE węzły grafu — żeby zewnętrzny koniec krzywej relacji leżał
    NA realnej, często zakrzywionej drodze widocznej na mapie, a nie na
    umownym promieniu kompasowym. find_arms() sam zatrzymuje się na pierwszym
    napotkanym węźle topologicznym, a na gęstych skrzyżowaniach bywa on
    zaledwie kilka-kilkanaście metrów od środka. Węzeł centralny jest
    wykluczony z kandydatów — inaczej krótkie boczne wloty potrafią "zawrócić"
    z powrotem przez skrzyżowanie zamiast kontynuować swoją ulicę.

    Spośród krawędzi mieszczących się w progu odchylenia kąta PREFEROWANA
    jest ta o TEJ SAMEJ NAZWIE co wlot (nie tylko najmniejsze odchylenie
    kątowe) — samo "najmniejszy kąt" na gęstej siatce potrafi w jednym z
    kolejnych węzłów skręcić na równoległą boczną uliczkę.

    `travel` rozróżnia DWIE jezdnie drogi dwujezdniowej jednokierunkowej
    (częste na drogach klasy secondary+): "out" idzie krawędziami
    skierowanymi OD środka (jezdnia wylotowa), "in" krawędziami skierowanymi
    DO środka (jezdnia wlotowa) — to osobne obiekty w OSM z osobną geometrią,
    czasem wyraźnie rozsuniętą wokół wyspy/pasa dzielącego. Chodzenie po
    grafie NIESKIEROWANYM (jak poprzednio) losowo trafiało na którąś z nich,
    więc druga jezdnia w ogóle nie była pokrywana przez żadną krzywą."""
    arm_name = arm.get("name")
    coords = list(arm["coords"])
    target_deg = target_dist_m / 111_000
    total = sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(coords, coords[1:]))
    Gu = G.to_undirected()
    fx, fy = arm["far"]
    last_node = _nearest_node(G, fx, fy, max_dist_deg=3 / 111_000)
    if total >= target_deg:
        return coords, last_node
    if last_node is None:
        return coords, last_node

    current = last_node
    prev_xy = coords[-2] if len(coords) >= 2 else coords[0]
    visited = {current}
    # Węzeł NAJBLIŻSZY zadanej odległości (nie ostatni odwiedzony) — pojedynczy
    # realny odcinek bywa dużo dłuższy niż target_dist_m (widziałem odcinki
    # 70m+ jednym skokiem), więc "ostatni węzeł pętli" potrafił wylądować
    # kilkadziesiąt metrów dalej niż proszony zasięg. To WĘZEŁ (nie
    # interpolowany punkt) jest potrzebny do routingu (real_route_coords),
    # więc nie można go po prostu przyciąć jak polilinię współrzędnych.
    closest_node, closest_diff = current, abs(total - target_deg)
    while total < target_deg:
        last_xy = coords[-1]
        last_bearing = bearing(prev_xy[1], prev_xy[0], last_xy[1], last_xy[0])
        best = None
        for nxt in Gu.neighbors(current):
            if nxt in visited:
                continue
            px, py = G.nodes[nxt]["x"], G.nodes[nxt]["y"]
            if math.hypot(px - center_xy[0], py - center_xy[1]) < 5 / 111_000:
                continue  # nie zawracaj przez środek skrzyżowania
            nxt_bearing = bearing(last_xy[1], last_xy[0], py, px)
            db = abs(nxt_bearing - last_bearing) % 360
            db = min(db, 360 - db)
            if db > max_turn_deg:
                continue
            # Wersja skierowana (ta konkretna jezdnia) ma pierwszeństwo nad
            # nieskierowanym fallbackiem (gdy droga faktycznie dwukierunkowa
            # na jednej geometrii, albo brak osobnej jezdni w danych OSM).
            directed_data = G.get_edge_data(current, nxt) if travel == "out" else G.get_edge_data(nxt, current)
            edge_data = directed_data if directed_data else Gu.get_edge_data(current, nxt)
            has_directed = directed_data is not None
            same_name = arm_name is not None and any(
                edge_name(d) == arm_name for d in edge_data.values())
            key = (0 if same_name else 1, 0 if has_directed else 1, db)
            if best is None or key < best[0]:
                best = (key, nxt, px, py)
        if best is None:
            break
        _, nxt, px, py = best
        coords.append((px, py))
        total += math.hypot(px - last_xy[0], py - last_xy[1])
        visited.add(nxt)
        prev_xy, current = last_xy, nxt
        last_node = current
        diff = abs(total - target_deg)
        if diff < closest_diff:
            closest_diff, closest_node = diff, current

    return coords, closest_node


def real_route_coords(G, src_node, dst_node):
    """Rzeczywista trasa PO PRAWDZIWYCH KRAWĘDZIACH grafu (z poszanowaniem
    kierunków jednokierunkowych) między dwoma węzłami — używana zamiast
    syntetycznego łuku Beziera, żeby relacja skrętna szła dokładnie tak, jak
    faktycznie da się przejechać przez rdzeń skrzyżowania (wysepki, pasy
    skrętu widoczne jako gęsty klaster węzłów blisko środka), a nie po
    umownej krzywiźnie. Zwraca None, gdy w grafie brak takiej trasy."""
    try:
        path = nx.shortest_path(G, src_node, dst_node, weight="length")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None
    coords = []
    for u, v in zip(path, path[1:]):
        edge_data = min(G.get_edge_data(u, v).values(), key=lambda d: d.get("length", 0))
        geom = edge_data.get("geometry")
        seg = list(geom.coords) if geom is not None else [
            (G.nodes[u]["x"], G.nodes[u]["y"]), (G.nodes[v]["x"], G.nodes[v]["y"])]
        if coords and coords[-1] == seg[0]:
            coords.extend(seg[1:])
        else:
            coords.extend(seg)
    return coords


def plot_flow_diagram(G_local, center, arms, wlot_to_arm_direction, gate_mapping, movements, wlot_totals,
                       metric, output_path, context_graph=None, buildings=None, landuse=None, aspect=(4, 3),
                       view_radius_deg=48 / 111_000, G_topology=None):
    title, unit, fmt = METRICS[metric]
    fig, ax = plt.subplots(figsize=(10, 10 * aspect[1] / aspect[0]))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    cx, cy = draw_base_layers(ax, G_local, center, context_graph, buildings, landuse)
    G_topology = G_topology if G_topology is not None else G_local
    view_radius_m = view_radius_deg * 111_000

    relations_by_wlot = {}
    for gate, (wlot, relacja) in gate_mapping.items():
        relations_by_wlot.setdefault(wlot, set()).add(relacja)
    used_relations = [r for r in TURN_ORDER if any(r in rels for rels in relations_by_wlot.values())]

    # Krzywe relacji mają pokrywać drogę na TĘ SAMĄ długość co widoczna na
    # bazowej mapie (hug_reach_m, blisko krawędzi kadru) — nie tylko
    # kilkunastometrowy fragment przy środku. turn_m/reach_m (krótkie)
    # zostają WYŁĄCZNIE jako skala fallbacku: schematycznego łuku Beziera
    # dla skrętu, gdy w grafie brak sensownego bezpośredniego przejazdu —
    # ten łuk tnie przez otwarte wnętrze skrzyżowania, więc nie ma sensu
    # ciągnąć go do krawędzi kadru.
    hug_reach_m = view_radius_m * 0.85
    reach_m = view_radius_m * 0.34
    turn_m = reach_m
    through_m = hug_reach_m
    label_walk_m = view_radius_m * 0.9
    # Drogi klasy secondary+ bywają dwujezdniowe jednokierunkowe — jezdnia
    # "od środka" (out) i "do środka" (in) to osobne krawędzie w OSM, czasem
    # fizycznie rozsunięte wokół wyspy/pasa dzielącego. extended_by_direction
    # (out) służy do etykiet/boksów i jako wylotowa połowa "Wprost" (fallback);
    # extended_in_by_direction tylko jako wlotowa połowa "Wprost" (fallback)
    # — żeby OBIE jezdnie były faktycznie pokryte krzywą, a nie tylko ta, na
    # którą trafił przypadkiem chodzący po grafie algorytm. outer_node_out/in
    # (na hug_reach_m) to punkty startu/celu prawdziwego routingu — długie,
    # żeby pokrywał całą widoczną drogę; turn_anchor (krótkie, reach_m)
    # zostaje tylko jako zakotwiczenie fallbackowego łuku skrętu.
    extended_by_direction, extended_in_by_direction = {}, {}
    outer_node_out, outer_node_in, turn_anchor = {}, {}, {}
    for arm_direction in wlot_to_arm_direction.values():
        arm = arm_by_direction(arms, arm_direction)
        extended, _ = extend_along_road(
            G_topology, arm, label_walk_m, center_xy=(cx, cy), travel="out")
        ext_in, _ = extend_along_road(
            G_topology, arm, label_walk_m, center_xy=(cx, cy), travel="in")
        extended_by_direction[arm_direction] = extended
        extended_in_by_direction[arm_direction] = ext_in
        _, node_out = extend_along_road(G_topology, arm, hug_reach_m, center_xy=(cx, cy), travel="out")
        _, node_in = extend_along_road(G_topology, arm, hug_reach_m, center_xy=(cx, cy), travel="in")
        outer_node_out[arm_direction] = node_out
        outer_node_in[arm_direction] = node_in
        turn_anchor[arm_direction] = point_along(extended, turn_m / 111_000)

    # Boczne przesunięcie o pas ruchu (jak prawdziwa dwukierunkowa jezdnia):
    # bez niego relacja "Wprost" w jedną stronę i "Wprost" z powrotem mają
    # DOKŁADNIE te same dwa punkty i zerową krzywiznę — czyli jedna linia
    # rysuje się idealnie na drugiej i połowa relacji wizualnie znika.
    lane_offset_deg = 0.3 / 111_000

    def lane_point(pt, travel_bearing_deg):
        return offset_point(pt, travel_bearing_deg + 90, lane_offset_deg)

    # Dodatkowy, WIĘKSZY rozstaw wachlarzowy PRZY WLOCIE — Wprost/Prawo/Lewo
    # mają każde swoje miejsce zamiast zbiegać się w jednym punkcie na
    # granicy skrzyżowania (stąd wyglądało to jak supeł, nie jak wachlarz
    # relacji). Kierunek "w prawo od wjazdu" dla Prawo, "w lewo" dla Lewo.
    FAN_SIDE = {"Wprost": 0, "Prawo": 1, "Lewo": -1, "Zawracający": 0}
    fan_offset_deg = 5.0 / 111_000

    def fan_point(pt, arm_bearing_deg, relacja_):
        if FAN_SIDE[relacja_] == 0:
            return pt
        return offset_point(pt, arm_bearing_deg + 180 + 90 * FAN_SIDE[relacja_], fan_offset_deg)

    values = list(movements.values())
    vmax = max(values) if values else 1
    # Podłoga grubości dużo wyższa niż poprzednio — skręty o mniejszej
    # wartości niż "Wprost" wcześniej wychodziły jako cienkie, dekoracyjne
    # kreski obok grubych linii przelotowych; teraz każda relacja jest
    # wyraźna, a grubość dalej rośnie z wartością.
    min_lw, max_lw = 2.6, 6.5

    for (wlot, relacja), value in movements.items():
        arm_direction = wlot_to_arm_direction[wlot]
        source = arm_by_direction(arms, arm_direction)
        lw = min_lw + (max_lw - min_lw) * (value / vmax if vmax else 0)
        color = TURN_COLOR[relacja]

        arrow_scale = 6 + lw  # grot proporcjonalny do grubości, ale nigdy niewidocznie mały

        if relacja == "Zawracający":
            p0 = lane_point(turn_anchor[arm_direction], source["bearing"] + 180)
            p1 = offset_point(p0, source["bearing"] + 40, (turn_m * 0.4) / 111_000)
            arrow = matplotlib.patches.FancyArrowPatch(
                p0, p1, connectionstyle="arc3,rad=1.4", color=color, linewidth=lw,
                arrowstyle="-|>", mutation_scale=arrow_scale, alpha=0.8, zorder=5, capstyle="round",
            )
            ax.add_patch(arrow)
            continue

        dest = exit_arm(arms, source, relacja)

        # KAŻDA relacja (Wprost i skręty) próbuje najpierw jechać po
        # PRAWDZIWEJ drodze — prawdziwy routing po grafie (z poszanowaniem
        # kierunków jednokierunkowych) między zakotwiczeniami na wlocie i
        # wylocie, żeby krzywa faktycznie leżała na zaznaczonych na mapie
        # drogach, a nie cięła przez otwartą przestrzeń skrzyżowania. Gdy w
        # grafie brak sensownej trasy (albo prowadzi na kilometrowy objazd
        # przez inne kwartały — bo dane OSM nie mają wprost zakodowanego
        # bezpośredniego przejazdu) — dopiero wtedy syntetyczny fallback:
        # dla Wprost dotychczasowa para jezdni (in/out), dla skrętów łuk
        # Beziera przez wnętrze skrzyżowania.
        src_node, dst_node = outer_node_in[arm_direction], outer_node_out[dest["direction"]]
        route = real_route_coords(G_topology, src_node, dst_node) if src_node and dst_node else None
        if route is not None:
            route_m = sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(route, route[1:])) * 111_000
            if route_m > hug_reach_m * 2.5:
                route = None

        if route is not None:
            route = [lane_point(pt, source["bearing"] + 180) for pt in route]
            xs, ys = zip(*route)
            ax.plot(xs, ys, color=color, linewidth=lw, alpha=0.8, zorder=5, solid_capstyle="round")
            # Subtelny grot kierunku na końcu, liczony na STAŁYM dystansie od
            # końca liczonym od RZECZYWISTEJ długości trasy — przy krótkich
            # trasach oba punkty inaczej lądowały w tym samym miejscu i grot
            # miał zerową długość, więc znikał.
            route_len_deg = sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(route, route[1:]))
            tail = point_along(route, max(route_len_deg - 3 / 111_000, 0))
            ax.annotate("", xy=route[-1], xytext=tail, zorder=6,
                        arrowprops=dict(arrowstyle="-|>", color=color, lw=0, alpha=0.8,
                                         mutation_scale=arrow_scale, shrinkA=0, shrinkB=0))
        elif relacja == "Wprost":
            src_half = list(reversed(
                clip_polyline(extended_in_by_direction[arm_direction], through_m / 111_000)))
            dst_half = clip_polyline(extended_by_direction[dest["direction"]], through_m / 111_000)
            route = [lane_point(pt, source["bearing"] + 180) for pt in src_half + dst_half[1:]]
            xs, ys = zip(*route)
            ax.plot(xs, ys, color=color, linewidth=lw, alpha=0.8, zorder=5, solid_capstyle="round")
            route_len_deg = sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(route, route[1:]))
            tail = point_along(route, max(route_len_deg - 3 / 111_000, 0))
            ax.annotate("", xy=route[-1], xytext=tail, zorder=6,
                        arrowprops=dict(arrowstyle="-|>", color=color, lw=0, alpha=0.8,
                                         mutation_scale=arrow_scale, shrinkA=0, shrinkB=0))
        else:
            p0 = fan_point(lane_point(turn_anchor[arm_direction], source["bearing"] + 180),
                            source["bearing"], relacja)
            # Ten sam wachlarzowy rozstaw też na KOŃCU krzywej (wylot) — bez
            # tego różne relacje docierające do tego samego ramienia zbiegały
            # się z powrotem w jeden punkt, dając wrażenie, że wszystko biegnie
            # tylko wzdłuż dwóch osi zamiast wyraźnie do 4 różnych wlotów.
            p1 = fan_point(lane_point(turn_anchor[dest["direction"]], dest["bearing"]),
                            dest["bearing"] - 180, relacja)
            # Znak krzywizny z GEOMETRII tej konkretnej pary (p0->p1), nie ze
            # stałego znaku per typ relacji — inaczej połowa skrętów wyginała
            # się w złą stronę, zależnie od przypadkowego układu wlotów.
            # Prawo ma wybrzuszać się w stronę "na prawo od kierunku jazdy"
            # (azymut wlotu+180+90), Lewo w przeciwną (+180-90).
            desired_bearing = source["bearing"] + 180 + (90 if relacja == "Prawo" else -90)
            rad = curve_sign(p0, p1, desired_bearing) * 0.42
            arrow = matplotlib.patches.FancyArrowPatch(
                p0, p1, connectionstyle=f"arc3,rad={rad}", color=color, linewidth=lw,
                arrowstyle="-|>", mutation_scale=arrow_scale, alpha=0.8, zorder=5, shrinkA=0, shrinkB=0,
                capstyle="round",
            )
            ax.add_patch(arrow)

    # Nazwa ulicy + boks z liczbami PRZYKLEJONE do realnej drogi i obrócone
    # równolegle do niej — jak w oryginale z Visum — zamiast poziomych kart
    # wiszących w pustej przestrzeni.
    for wlot, arm_direction in wlot_to_arm_direction.items():
        arm = arm_by_direction(arms, arm_direction)
        extended = extended_by_direction[arm_direction]
        rot = road_rotation(arm["bearing"])

        name_pt = point_along(extended, (view_radius_m * 0.68) / 111_000)
        ax.text(*name_pt, arm["name"], rotation=rot, rotation_mode="anchor", fontsize=7.5,
                color="#6b6b6b", style="italic", ha="center", va="center", zorder=6)

        box_pt = point_along(extended, (view_radius_m * 0.50) / 111_000)
        box_pt = offset_point(box_pt, arm["bearing"] + 90, 9.0 / 111_000)

        values = [fmt.format(movements.get((wlot, r), 0)) for r in used_relations
                  if r in relations_by_wlot.get(wlot, set())]
        text = "\n".join(values) + "\n" + "─" * 5 + "\n" + fmt.format(wlot_totals.get(wlot, 0))

        ax.text(*box_pt, text, rotation=rot, rotation_mode="anchor", fontsize=9,
                fontweight="bold", color=GRAPHITE, ha="center", va="center", zorder=9, linespacing=1.3,
                bbox=dict(boxstyle="square,pad=0.35", fc="white", ec=GRAPHITE, lw=1.0))

    target_ratio = aspect[0] / aspect[1]
    half_h = view_radius_deg
    half_w = half_h * target_ratio
    ax.set_xlim(cx - half_w, cx + half_w)
    ax.set_ylim(cy - half_h, cy + half_h)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    ax.annotate("N", xy=(0.95, 0.92), xytext=(0.95, 0.85), xycoords="axes fraction",
                ha="center", va="center", fontsize=12, fontweight="bold", color=GRAPHITE,
                arrowprops=dict(arrowstyle="-|>", color=GRAPHITE, lw=2))

    handles = [matplotlib.lines.Line2D([0], [0], color=TURN_COLOR[r], lw=3, label=r) for r in used_relations]
    ax.legend(handles=handles, loc="lower left", fontsize=9, framealpha=0.9,
              title="Kolejność w boksie (pod kreską: suma)", title_fontsize=9)

    ax.set_title(f"{title}\n[{unit}]", fontsize=12, color=GRAPHITE, pad=10)

    fig.subplots_adjust(left=0.02, right=0.98, top=0.90, bottom=0.02)
    plt.savefig(output_path, dpi=300, facecolor=BG)
    plt.close(fig)
    print(f"Zapisano: {output_path}")


def main():
    p = argparse.ArgumentParser(description="Diagram natężeń ruchu (mapka + relacje) z Quantity.csv")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--csv", type=str, required=True, help="ścieżka do Quantity.csv danego punktu")
    p.add_argument("--mapping", type=str, required=True, help="plik JSON z gate_mapping i wlot_to_arm_direction")
    p.add_argument("--metric", type=str, required=True, choices=list(METRICS))
    p.add_argument("--output", type=str, required=True)
    p.add_argument("--aspect", type=str, default="4:3")
    p.add_argument("--region-cache", type=str, default="region_cache")
    p.add_argument("--region-radius", type=int, default=4000)
    p.add_argument("--local-radius", type=int, default=150)
    p.add_argument("--view-radius", type=int, default=48)
    args = p.parse_args()
    aw, ah = (float(x) for x in args.aspect.split(":"))

    mapping = json.loads(open(args.mapping, encoding="utf-8").read())

    G_drive, G_all, buildings, landuse = load_or_fetch_region(
        args.region_cache, args.lat, args.lon, args.region_radius)
    center_node, arms = find_arms(G_drive, args.lat, args.lon, max_arm_dist_m=args.local_radius)
    if not arms:
        raise SystemExit("Nie znaleziono dróg w pobliżu podanych współrzędnych.")

    # Przycięcie PO LINII PROSTEJ (bbox), nie po odległości sieciowej —
    # truncate_graph_dist liczy dystans w liczbie skrętów/krawędzi, co na
    # rzadkiej, jednokierunkowej siatce potrafi odciąć realnie bliskie drogi
    # (dla tego skrzyżowania zostawiało zaledwie 8 węzłów w promieniu 150 m).
    # Krzywe relacji (extend_along_road, po pełnym G_drive) wtedy wychodziły
    # poza to, co w ogóle narysowane na mapie pod spodem — stąd wrażenie, że
    # "nie leżą na drogach", choć leżały na drogach, tylko nienarysowanych.
    west, south, east, north = ox.utils_geo.bbox_from_point(
        (args.lat, args.lon), dist=args.local_radius)
    G_local = ox.truncate.truncate_graph_bbox(G_drive, (west, south, east, north), truncate_by_edge=True)
    center = Point(args.lon, args.lat)

    movements, wlot_totals = compute_movements(args.csv, mapping["gate_mapping"], args.metric)
    plot_flow_diagram(G_local, center, arms, mapping["wlot_to_arm_direction"], mapping["gate_mapping"],
                       movements, wlot_totals, args.metric, args.output, G_all, buildings, landuse,
                       aspect=(aw, ah), view_radius_deg=args.view_radius / 111_000, G_topology=G_drive)


if __name__ == "__main__":
    main()
