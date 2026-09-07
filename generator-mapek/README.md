generate_map.py
================

Krótki opis

Skrypt `generate_map.py` generuje prostą mapkę PNG z granicą miasta (jeśli dostępna) i pinezką dla podanych współrzędnych.

Szybka instalacja (virtualenv, pip)

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Uwaga: `geopandas` i jego zależności (gdal/fiona/pyproj) czasami łatwiej zainstalować przez conda. Jeśli napotkasz błędy przy `pip install`, użyj instrukcji conda poniżej.

Zalecana instalacja (conda / conda-forge)

```bash
conda create -n mapenv python=3.9 -y
conda activate mapenv
conda install -c conda-forge geopandas osmnx matplotlib requests -y
```

Uruchomienie

```bash
python3 generate_map.py --lat 52.99204691558239 --lon 18.642194499056817 --output p1-mapa.png
python3 generate_map.py --lat 52.99196632649376 --lon 18.632410403178802 --output p2-mapa.png
python3 generate_map.py --lat 52.98953303343776 --lon 18.635362309395227 --output p3-mapa.png
```
python3 generate_intersection_map.py --lat 52.99204691558239 --lon 18.642194499056817 --output mapa1.png
python3 generate_intersection_map.py --lat 52.99196632649376 --lon 18.632410403178802 --output mapa2.png
python3 generate_intersection_map.py --lat 52.98953303343776 --lon 18.63538561619794 --output mapa3.png

p1 52.99204691558239, 18.642194499056817
p2 52.99196632649376, 18.632410403178802
p3 52.98953303343776, 18.63538561619794
52.9895245606357, 18.635362309395227

Dodatkowe uwagi

- Jeśli nie zainstalowano `osmnx`, skrypt nadal działa, lecz zamiast granicy miasta użyje małego bufora wokół punktu jako obszaru mapy.
- Jeśli chcesz przywrócić lub dodać bardziej zaawansowane źródła granic (Overpass, polygons.openstreetmap.fr, Geofabrik), daj znać — mogę dodać opcjonalne mechanizmy z cache.
