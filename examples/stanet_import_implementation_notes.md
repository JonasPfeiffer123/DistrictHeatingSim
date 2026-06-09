# STANET CSV Import — Implementation Notes

Describes all changes made to `stanet_import_pandapipes.py` that should be applied
identically to any equivalent STANET importer (e.g. in VICUS).

---

## STANET Export Prerequisite

Before running the import, the STANET project **must** be configured as follows:

| STANET setting | Required value |
|---|---|
| Koordinatensystem Onlinekartographie 10.0 | `EPSG:258*; ETRS89 / UTM` |
| Meridianstreifen/UTM Zone | `32` (western Germany) or `33` (eastern Germany) |
| Meridianstreifen voranstellen auch bei WGS84 | unchecked (N) |

STANET stores the wildcard code `EPSG:258*` in the `COORDSYS4` field of the NET block
and the zone number in `UTMZONE`. The import code resolves this to e.g. `EPSG:25833`
and passes it to the map renderer so OSM background tiles are fetched for the correct
location. **Using any other coordinate system (e.g. DHDN/GK) will cause a systematic
positional offset against the OSM basemap.**

---

## 1 — Object types to parse

Register all seven block types. `KNI` and `NET` are new compared to the original:

```python
object_types = {
    'KNO': 'REM FLDNAM KNO',
    'LEI': 'REM FLDNAM LEI',
    'KNI': 'REM FLDNAM KNI',   # bend points — NEW
    'NET': 'REM FLDNAM NET',   # project metadata / CRS — NEW
    'WAE': 'REM FLDNAM WAE',
    'HEA': 'REM FLDNAM HEA',
    'ZAE': 'REM FLDNAM ZAE',
}
```

---

## 2 — DataFrame parsing: strip column names

After building each DataFrame, strip whitespace from the column names. STANET CSV
headers occasionally include leading/trailing spaces that cause silent `KeyError`s:

```python
df = pd.DataFrame(data, columns=header)
df.columns = df.columns.str.strip()   # NEW
dataframes_dict[obj_type] = df
```

---

## 3 — CRS detection from the NET block

Add the helper function `_detect_crs(dataframes_dict)` **before** the main import
function. It reads `COORDSYS4`, `UTMZONE`, and `ZONEPREFIX` from the NET row and
resolves wildcard codes (e.g. `EPSG:258*`) to a fully qualified EPSG string.

For wildcard codes where `UTMZONE` is not set, the correct zone is determined by
transforming a sample KNO coordinate to WGS84 and checking whether the result falls
within the Central-Europe bounding box (lon 5°–19°E, lat 46°–57°N).

```python
def _detect_crs(dataframes_dict):
    from pyproj import CRS as ProjCRS, Transformer as ProjTransformer

    net_df = dataframes_dict.get('NET')
    if net_df is None or net_df.empty:
        return None, 'J', 0

    row = net_df.iloc[0].str.strip() if net_df.dtypes.eq(object).all() else net_df.iloc[0]

    coordsys4   = str(row.get('COORDSYS4', '') or '').strip()
    utmzone_raw = str(row.get('UTMZONE',   '0') or '0').strip()
    zoneprefix  = str(row.get('ZONEPREFIX','J') or 'J').strip().upper()

    try:
        utmzone = int(float(utmzone_raw))
    except ValueError:
        utmzone = 0

    if not coordsys4:
        return None, zoneprefix, utmzone

    # Exact code (no wildcard) — return immediately
    if not coordsys4.endswith('*'):
        try:
            ProjCRS.from_user_input(coordsys4)
        except Exception:
            pass
        return coordsys4, zoneprefix, utmzone

    base = coordsys4[:-1]  # e.g. 'EPSG:258' or 'EPSG:3146'

    if utmzone > 0:
        digit_order = [utmzone]
    elif base.upper() == 'EPSG:3146':
        # German DHDN GK zones: 31466–31469 before Pulkovo 31461–31465
        digit_order = [6, 7, 8, 9, 1, 2, 3, 4, 5]
    else:
        digit_order = list(range(1, 10))

    # Geographic validation using a sample KNO coordinate
    sample_x = sample_y = None
    kno_df = dataframes_dict.get('KNO')
    if kno_df is not None and not kno_df.empty and 'XRECHTS' in kno_df.columns:
        try:
            import pandas as pd
            sample_x = pd.to_numeric(kno_df['XRECHTS'].str.strip(), errors='coerce').median()
            sample_y = pd.to_numeric(kno_df['YHOCH'].str.strip(),   errors='coerce').median()
        except Exception:
            pass

    bbox = (5.0, 46.0, 19.0, 57.0)  # lon_min, lat_min, lon_max, lat_max

    for digit in digit_order:
        code = base + str(digit)
        try:
            crs = ProjCRS.from_user_input(code)
        except Exception:
            continue

        if sample_x is None or sample_y is None:
            return code, zoneprefix, utmzone  # no data to validate, take first valid

        test_x = sample_x
        if zoneprefix == 'N':
            try:
                false_easting = float(crs.to_dict().get('x_0', 0))
                zone_pref = int(false_easting) // 1_000_000
                if zone_pref > 0:
                    test_x = sample_x + zone_pref * 1_000_000
            except Exception:
                pass

        try:
            t = ProjTransformer.from_crs(code, 'EPSG:4326', always_xy=True)
            lon, lat = t.transform(float(test_x), float(sample_y))
            if bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]:
                return code, zoneprefix, utmzone
        except Exception:
            continue

    return coordsys4, zoneprefix, utmzone  # fallback: raw value
```

### Usage in the main function

```python
crs_epsg, _, _ = _detect_crs(dataframes_dict)
print(f"Detected CRS: {crs_epsg}")

# Pass to the map renderer (e.g. config_plot / contextily).
# Falls back to EPSG:25833 if NET block is absent.
display_crs = crs_epsg or "EPSG:25833"
```

---

## 4 — Optional blocks: WAE, HEA, ZAE

These blocks are absent in many STANET exports. Use `.get()` with empty-DataFrame
fallbacks so a missing block does not raise `KeyError`:

```python
wae_df = dataframes_dict.get('WAE', pd.DataFrame())
hea_df = dataframes_dict.get('HEA', pd.DataFrame())
zae_df = dataframes_dict.get('ZAE', pd.DataFrame())
```

Guard all downstream processing with `if not <df>.empty:` checks.
The WAE/ZAE merge and the heat-consumer loop are no-ops on empty DataFrames.

Also initialise `yearly_time_steps = None` before the consumer loop so the return
statement is valid even when no consumers are found:

```python
yearly_time_steps = None
total_heat_W = []
max_heat_requirement_W = []
for idx, row in merged_wae_zae_df.iterrows():
    ...
    yearly_time_steps = df_bdew.index.values
    ...
```

---

## 5 — KNI (Knickpunkte / bend points)

### 5.1 Parse `kni_df`

After extracting the DataFrames, parse KNI into typed columns:

```python
kni_df = dataframes_dict.get('KNI')
if kni_df is not None and not kni_df.empty:
    kni_df = kni_df.apply(lambda col: col.str.strip() if col.dtype == object else col)
    kni_df['SNUM']    = pd.to_numeric(kni_df['SNUM'],    errors='coerce').astype('Int64')
    kni_df['KNICKNO'] = pd.to_numeric(kni_df['KNICKNO'], errors='coerce').astype('Int64')
    kni_df['XRECHTS'] = pd.to_numeric(kni_df['XRECHTS'], errors='coerce')
    kni_df['YHOCH']   = pd.to_numeric(kni_df['YHOCH'],   errors='coerce')
else:
    kni_df = None
```

### 5.2 Add `SNUM` to `filtered_lei_df`

`KNI.SNUM` is the 1-based record number of the associated LEI row (`!RECNO` in STANET).
Use the LEI table's own `!RECNO` column when present; fall back to sequential index:

```python
filtered_lei_df = filtered_lei_df.reset_index(drop=True)
if '!RECNO' in lei_df.columns:
    filtered_lei_df['SNUM'] = pd.to_numeric(
        lei_df['!RECNO'].str.strip(), errors='coerce'
    ).reset_index(drop=True).astype('Int64')
else:
    filtered_lei_df['SNUM'] = filtered_lei_df.index + 1
```

> **Note:** `ANFNAM`/`ENDNAM` in KNI rows are **not reliable join keys** — they
> sometimes use short node name variants (`K1026`) while the LEI row uses a longer
> form (`RK1026`). Always join on `SNUM`.

### 5.3 Build polyline geodata in the pipe-creation loop

```python
from_coords = (float(row["ANF_X"]), float(row["ANF_Y"]))
to_coords   = (float(row["END_X"]), float(row["END_Y"]))

if kni_df is not None:
    snum     = int(row["SNUM"])
    kni_rows = kni_df[kni_df['SNUM'] == snum].sort_values('KNICKNO')
    kni_coords = [(float(r['XRECHTS']), float(r['YHOCH'])) for _, r in kni_rows.iterrows()]
else:
    kni_coords = []

line_coords = [from_coords] + kni_coords + [to_coords]
# pass line_coords as geodata= to pp.create_pipe / pp.create_pipe_from_parameters
```

Pipes with no KNI rows naturally fall back to `[from_coords, to_coords]`.

---