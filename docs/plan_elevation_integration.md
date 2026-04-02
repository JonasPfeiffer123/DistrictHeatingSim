# Implementierungsplan: Höhendaten-Integration in pandapipes

**Branch:** `feature/elevation-data-integration`
**Erstellt:** 2026-03-24
**Ziel:** Junctions in pandapipes erhalten korrekte `height_m`-Werte, damit hydrostatische Druckunterschiede im Netz korrekt abgebildet werden.

---

## Problemstellung

`pp.create_junction()` hat einen `height_m`-Parameter (Höhe über NN in Metern), der direkt in die hydrostatische Druckberechnung einfließt:

```
ΔP_hydro = ρ · g · Δh
```

Aktuell wird `height_m=0` (Default) für **alle** Junctions verwendet. In hügeligem Gelände (z.B. Görlitz, ~212 m NN, Höhenrelief bis ca. 60 m) führt das zu systematisch falschen Druckberechnungen:
- **~0,6 bar** Druckunterschied pro 6 m Höhendifferenz werden ignoriert
- Pumpenauslegung und Druckzonenplanung sind verfälscht
- Leitungsdruckverluste werden über- oder unterschätzt

---

## Datenpfad (aktueller Zustand)

```
CSV (UTM_X, UTM_Y, ...)
        ↓ load_layers()
heat_consumer_layer (GeoDataFrame, 2D-Punkte)
        ↓ generate_and_export_layers()
flow_lines_gdf, return_lines_gdf (2D-LineStrings)
        ↓ NetworkGeoJSONSchema.create_network_geojson()
Wärmenetz.geojson (2D-Koordinaten: [x, y])
        ↓ initialize_geojson()
        ↓ get_line_coords_and_lengths()   → [(x,y), (x,y), ...]
        ↓ get_all_point_coords_from_line_cords() → {(x,y): id}
        ↓ create_junctions_from_coords()
pp.create_junction(..., height_m=0)  ← FEHLER
```

---

## Lösungsstrategie

### Grundprinzip
- Höhendaten werden aus einem **lokalen DGM (GeoTIFF)** ausgelesen.
- Als optionaler Fallback: **OpenTopoData REST API** (kostenlos, SRTM/EU-DEM).
- Höhe wird als **Z-Koordinate** in die GeoJSON-Geometrien eingeschrieben (`[x, y, z]`).
- Beim Einlesen der GeoJSON werden Z-Werte extrahiert und als `height_m` an jede Junction übergeben.
- **Rückwärtskompatibilität**: Fehlt die Z-Koordinate, bleibt `height_m=0`.

---

## Implementierungsschritte

### Schritt 1 — Neues Modul `elevation_utils.py`
**Datei:** `src/districtheatingsim/net_generation/elevation_utils.py`

```python
def query_elevation_from_geotiff(points_utm: List[Tuple[float,float]],
                                  dem_path: str,
                                  crs_utm: str = "EPSG:25833") -> List[float]:
    """Liest Höhen für UTM-Punkte aus einem lokalen GeoTIFF (DGM) via rasterio.
    Transformiert Koordinaten bei Bedarf in das DEM-CRS."""

def query_elevation_from_api(points_utm: List[Tuple[float,float]],
                              crs_utm: str = "EPSG:25833",
                              dataset: str = "eudem25m") -> List[float]:
    """Fragt Höhen über die OpenTopoData-API ab (Fallback, benötigt Internetzugang).
    Transformiert UTM → WGS84 vor dem API-Call."""

def assign_elevation_to_geodataframe(gdf: gpd.GeoDataFrame,
                                      elevations: List[float]) -> gpd.GeoDataFrame:
    """Fügt Z-Koordinaten zu den Point- oder LineString-Geometrien hinzu."""
```

**Abhängigkeiten (neu):** `rasterio`, `pyproj` (pyproj ist i.d.R. schon via geopandas vorhanden)

---

### Schritt 2 — Höhe in den Netzerzeugungspipeline integrieren
**Datei:** `src/districtheatingsim/net_generation/import_and_create_layers.py`

- `load_layers()` bekommt optionalen Parameter `dem_path: Optional[str] = None`
- Nach Erstellung von `heat_consumer_layer` und `heat_generator_layer`:
  - Höhen für alle Punkte abfragen (`query_elevation_from_geotiff` oder API-Fallback)
  - Punkte als 3D-Geometrien speichern: `Point(x, y, z)`
- `generate_and_export_layers()` erhält ebenfalls `dem_path`-Parameter und leitet ihn durch

---

### Schritt 3 — 3D-LineStrings in der Netzgenerierung
**Datei:** `src/districtheatingsim/net_generation/net_generation.py`

- `generate_network()` und `generate_connection_lines()`: Wenn Eingangspunkte 3D-Geometrien haben, sollen erzeugte LineStrings ebenfalls 3D sein (Shapely unterstützt das nativ)
- Bei einfachen Stützpunktinterpolationen entlang von Straßen: Z-Wert per linearer Interpolation der Endpunkte setzen

---

### Schritt 4 — Höhe in GeoJSON-Schema speichern
**Datei:** `src/districtheatingsim/net_generation/network_geojson_schema.py`

- `create_network_line_feature()`: Geometrie wird direkt über `geometry.__geo_interface__` gespeichert — wenn die Shapely-Geometrie 3D ist, enthält GeoJSON automatisch `[x, y, z]`
- Kein Schemabruch, da GeoJSON-Spec 3D-Koordinaten erlaubt
- Optional: In `calculated`-Sektion `elevation_start_m` / `elevation_end_m` ergänzen (Transparenz für User)

---

### Schritt 5 — Extraktion in der pandapipes-Initialisierung
**Datei:** `src/districtheatingsim/net_simulation_pandapipes/pp_net_initialisation_geojson.py`

#### 5a — `get_line_coords_and_lengths()` (Zeile 231)
```python
# Aktuell:
coords = list(line.coords)  # → [(x, y), ...]

# Neu: 3D-Koordinaten werden durchgereicht
coords = list(line.coords)  # → [(x, y, z), ...] bei 3D-GeoJSON
```
Rückgabe bleibt gleich (Koordinaten-Listen), aber Tuples können jetzt 3 Elemente haben.

#### 5b — `get_all_point_coords_from_line_cords()` (Zeile 260)
```python
# Neu: Elevationslookup parallel aufbauen
# Schlüssel = (x, y), Wert = z (oder 0.0 wenn 2D)
def get_all_point_coords_and_elevations(all_line_coords):
    point_coords_2d = set()
    elevation_lookup = {}
    for line in all_line_coords:
        for coord in line:
            xy = coord[:2]
            point_coords_2d.add(xy)
            elevation_lookup[xy] = coord[2] if len(coord) > 2 else 0.0
    return list(point_coords_2d), elevation_lookup
```

#### 5c — `create_junctions_from_coords()` (Zeile 315)
```python
# Aktuell:
junction_id = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=...,
                                  name=..., geodata=coords)

# Neu:
height = elevation_lookup.get(coords, 0.0)
junction_id = pp.create_junction(net_i, pn_bar=1.05, tfluid_k=...,
                                  height_m=height,
                                  name=..., geodata=coords[:2])
```

- `geodata` bekommt weiterhin nur `(x, y)` (pandapipes erwartet 2-Tupel)
- `height_m` wird als separater Parameter übergeben

---

### Schritt 6 — GUI-Integration
**Datei:** `src/districtheatingsim/gui/NetworkGenerationTab/` (relevante Tab-Datei)

- Optionaler Datei-Picker: **"DGM-Datei (GeoTIFF)"** — wenn leer, wird OpenTopoData-API-Fallback genutzt
- Tooltip-Hinweis: Welche Auflösung / welcher Dienst wird verwendet
- Nach Generierung: Logging-Ausgabe mit Höhenstatistik (min/max/range der gefundenen Höhen)

---

### Schritt 7 — Validierung und Tests

#### Validierungscheck nach Netzaufbau
In `create_network()` nach Junction-Erstellung:
```python
if net.junction["height_m"].std() > 0:
    h_min = net.junction["height_m"].min()
    h_max = net.junction["height_m"].max()
    dh = h_max - h_min
    dp_hydro_bar = 1000 * 9.81 * dh / 1e5  # ρ·g·Δh in bar
    logging.info(f"Höhenrelief im Netz: {dh:.1f} m → hydrostatischer Druckunterschied: {dp_hydro_bar:.2f} bar")
    if dp_hydro_bar > 0.5 * lift_pressure_pump:
        logging.warning("Hydrostatischer Druckunterschied ist >50% des Pumpenhubs — Druckzonenplanung prüfen!")
```

#### Unit-Tests
- Test mit bekannten Höhenwerten: Netz mit 2 Junctions auf 0 m und 10 m → prüfe dass `net.junction.height_m` korrekt gesetzt ist
- Test der `elevation_utils.py` mit einer kleinen Testdatei (Mocking oder kleines Dummy-GeoTIFF)
- Regressionstest: Flaches Netz (alle height_m=0) → identisches Ergebnis wie bisher

---

## Dateien im Überblick

| Datei | Änderungstyp | Beschreibung |
|-------|-------------|--------------|
| `net_generation/elevation_utils.py` | **NEU** | DGM-Abfrage (GeoTIFF + API-Fallback) |
| `net_generation/import_and_create_layers.py` | Erweiterung | `dem_path`-Parameter, 3D-Punkte erzeugen |
| `net_generation/net_generation.py` | Erweiterung | 3D-LineStrings durchreichen |
| `net_generation/network_geojson_schema.py` | Minimal | ggf. `elevation_start_m/end_m` in `calculated` |
| `net_simulation_pandapipes/pp_net_initialisation_geojson.py` | **Kernänderung** | Z-Extraktion + `height_m` an Junction übergeben |
| `gui/.../network_generation_tab.py` | Erweiterung | DGM-Datei-Picker |
| `tests/test_elevation_integration.py` | **NEU** | Unit- und Regressionstests |

---

## Abhängigkeiten

```toml
# pyproject.toml ergänzen:
[project.dependencies]
rasterio = ">=1.3"   # Für lokale GeoTIFF-Abfrage (optional, mit graceful fallback)
requests = ">=2.28"  # Für OpenTopoData-API (ggf. bereits vorhanden)
```

`rasterio` als optionale Abhängigkeit (`[project.optional-dependencies]`), API-Fallback ohne zusätzliche Deps.

---

## Offene Fragen / Design-Entscheidungen

1. **DGM-Auflösung**: SRTM hat 30 m Auflösung, EU-DEM 25 m — für Fernwärmenetze im Stadtbereich ggf. zu grob. Empfehlung: Nutzer kann hochaufgelöstes Landes-DGM (1 m, z.B. von BKG oder Landesamt) als GeoTIFF liefern.

2. **Mittelpunkt-Junction bei Sekundärerzeuger** (Zeile 423): `mid_coord` wird aus 2 Punkten interpoliert — Höhe sollte ebenfalls interpoliert werden.

3. **Rücklauf-Netz**: Vor- und Rücklauf verlaufen parallel → gleiche Höhen. Kein separates Höhenmodell nötig; die Junction-Dicts für VL und RL bekommen die gleichen `height_m`-Werte.

4. **Bestehende GeoJSONs**: Alte `Wärmenetz.geojson`-Dateien ohne Z-Koordinaten → Fallback auf `height_m=0` (keine Breaking Change).

5. **Druckzonen**: Bei sehr großem Höhenrelief (>30 m) empfiehlt sich eine Druckzonenplanung — das ist ein separates Feature (z.B. Druckminderventile), nicht Teil dieses Plans.
