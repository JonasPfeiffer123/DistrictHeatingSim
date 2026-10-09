# Anwendertest DistrictHeatingSim – Volltest aus Erstnutzer-Sicht

Stand: 2026-10-08 · Version 2.0.0 (`main`, Commit 194b774) · Windows 11, Python 3.12

## 1. Kurzfazit

Die Software deckt den kompletten Planungsweg ab – vom Gebäude-CSV über OSM-Straßen,
automatische Trassenführung und pandapipes-Hydraulik bis zur Erzeugerauslegung mit
VDI-2067-Wirtschaftlichkeit, Optimierung, Sensitivität und Variantenvergleich. Mit dem
mitgelieferten Görlitz-Beispiel und einem sauber vorbereiteten Ost-Sachsen-Projekt kommt man
bis zu belastbar aussehenden Zahlen.

Ein Erstnutzer mit eigenen Daten stolpert aber bei fast jedem Schritt, und an mehreren Stellen
**rechnet die Software falsch, ohne dass man es merkt**:

1. **Netzverluste werden um den Faktor 2–4 überschätzt** (Außendurchmesser bleibt nach der
   Rohrdimensionierung auf DN100 stehen). Im Testprojekt Zittau führte das zu 47–49 %
   „Verteilverlusten“, die alle Folgegrößen verfälschen (Erzeugerlast, WGK, CO₂, Vergleich).
2. **Projekte außerhalb der UTM-Zone 33 (Westdeutschland, Bayern, BW, NRW …) sind nicht
   konsistent bearbeitbar**: Standard-CRS 25833 ohne Warnung, CRS-Wechsel rechnet vorhandene
   Koordinaten nicht um, Erzeuger-Geocoding und OSMnx-Export ignorieren die Projekt-CRS.
3. **Der Dateneinstieg ist der größte Stolperstein**: „CSV importieren“ übernimmt eine korrekte
   Datei nicht ins Projekt (und das Geocoding überschreibt danach die Quelldatei des Nutzers),
   Excel-CSVs (Windows-1252, Dezimalkomma) scheitern, der OSM-Weg liefert 239 Gebäude mit
   identischem Wärmebedarf und – nach Nominatim-Sperre – 212-fach derselben Adresse.
4. **Die Voreinstellung der Jahreszeitreihe ist praktisch unbenutzbar** (detailliert, 1 Prozess:
   86–170 min für 15 Gebäude, ohne Fortschritt, ohne Abbruch; Speichern währenddessen beschädigt
   das Projekt).
5. **Externe Dienste sind nicht abgesichert**: Die voreingestellte CARTO-Hintergrundkarte
   liefert nur „API KEY REQUIRED“-Kacheln, Overpass-Ausfälle und Nominatim-Sperren landen als
   rohe Tracebacks beim Nutzer.

Die gute Nachricht: Die meisten kritischen Punkte sind lokal und mit wenigen Zeilen behebbar
(Abschnitt 6, Stufe 1). Der größere Hebel liegt danach in einem geführten Daten-Einstieg und in
automatisierten End-to-End-Tests der GUI – das Test-Harness aus diesem Lauf ist dafür eine
fertige Grundlage.

## 2. Vorgehen

### 2.1 Rolle und Methode

Rolle: Energieberater/Planer, der die Software zum ersten Mal nutzt und nur den groben Ablauf
kennt („Gebäude → Wärmebedarf → Straßen → Netz → Hydraulik → Erzeuger → Vergleich“).

Methode: Die **echte GUI** wurde headless (Qt `offscreen`) per Skript bedient – dieselben Slots
wie bei Klicks, alle Meldungen/Datei-/Eingabedialoge wurden protokolliert und skriptgesteuert
beantwortet, jeder Schritt per Screenshot geprüft. Wo Laufzeiten oder Rechenfehler zu klären
waren, wurden die Domänenfunktionen zusätzlich direkt aufgerufen. Internet (Nominatim,
Overpass/OSMnx, Kartenkacheln) war verfügbar und wurde real genutzt.

### 2.2 Testplan und Abdeckung

| ID | Projekt / Ort | Charakter | Datenweg | Geprüft |
|----|---------------|-----------|----------|---------|
| P0 | Görlitz (Beispiel) | mitgeliefert | Projekt öffnen | Erster Eindruck aller 6 Tabs |
| P1 | Zittau Altstadt | 15 Gebäude, BDEW-Mix (GKO, GHA, GBD, GBH, HMF, HEF) | Adress-CSV → Geocoding | Kern-Workflow komplett; OSMnx-Netz; Hydraulik (detailliert/vereinfacht/parallel); 4 Erzeugerkonfigurationen; Optimierung; Sensitivität; Variante 2 (statisch 75 °C); Variantenvergleich |
| P2 | Ostritz Dorfkern | 239 OSM-Gebäude | OSM-Gebäudeabfrage (Polygon) → „CSV aus OSM-GeoJSON“ | OSM-Weg, Datenqualität, Performance bei ~240 Gebäuden |
| P3 | Freiburg-Vauban | 12 Gebäude, VDI 4655 (EFH/MFH), UTM 32 | Excel-Export mit eigenen Spaltennamen → Mapping-Dialog | Import-Robustheit, CRS-Handling, Geocoding, MST/Advanced MST/OSMnx, Konnektivität |
| R1–R8 | – | Bedienfehler | – | Abbrechen, Doppelklick im Baum, doppelter Projektname, falsche Eingaben, Schließen/Speichern, Variantenwechsel |

Nicht oder nur eingeschränkt prüfbar: händisches Editieren auf der Leaflet-Karte, Plotly-Ansichten
(Netzplot, Sankey rendern headless leer – nicht als Fehler gewertet), PyInstaller-EXE,
DGM-GeoTIFF, Flusswärmepumpe mit Wassertemperatur-CSV, Holzgas-BHKW, mehrere Erzeuger im Netz,
„kaltes Netz“.

## 3. Wie ich als Erstnutzer vorgegangen bin – und wo es hakte

**Start.** Der Willkommensbildschirm ist aufgeräumt und startet schnell (< 1 s). Angeboten wird
das „Görlitz Beispielprojekt“ – allerdings direkt aus dem Installationsordner, d. h. Speichern
überschreibt die mitgelieferten Daten. Ein „Was mache ich jetzt?“-Leitfaden fehlt; „Dokumentation
öffnen“ führt auf eine API-Referenz ohne Benutzerhandbuch.

**Beispiel ansehen.** Alle Tabs laden. Auffällig sofort: Die Karte zeigt flächig
„API KEY REQUIRED“, das Netz erscheint dreifach in der Layerliste, der Variantenvergleich zeigt
„--“ obwohl Konfigurationen angehakt sind.

**Eigenes Projekt Zittau.** Neues Projekt → zwei Erfolgsmeldungen, eine mit Pfad
`…\Variante 1\..\Definition Quartier IST\…`. Ich importiere meine fertige Adress-CSV mit
„CSV importieren“: Die Tabelle zeigt 15 Gebäude, der Status sagt gleichzeitig
„❌ Quartier IST.csv: Datei fehlt“. „Geokoordinaten berechnen“ meldet Erfolg – geschrieben wurde
aber in **meine Originaldatei** außerhalb des Projekts. Im Tab „Wärmebedarf“ wird die leere
Projektdatei geladen, die Berechnung bricht mit englischem Traceback ab („Unknown building types:
nan“). Erst nach manuellem Kopieren der Datei ins Projekt ging es weiter.

**Straßen und Netz.** Der OSM-Straßendialog ist mit „Zittau“ vorbelegt. Der erste Download
brach nach 58 s ab (Overpass „Remote end closed connection“, Roh-Traceback). Die Netzgenerierung
im Modus OSMnx lief trotzdem – sie lädt Straßen selbst; der Fortschrittstracker verlangt den
Straßendownload aber als eigenen Schritt. Im Netzdialog ist eine Erzeugerkoordinate vorbelegt,
die eine Ziffer zu viel hat (Y = 55 666 161), und eine Adresse in Bad Muskau. Nach der Generierung
zoomt die Karte auf den Erzeugerpunkt in maximaler Vergrößerung – vom Netz sieht man eine Linie.
Die Konnektivitätsprüfung meldet für das frisch erzeugte Netz „74 fast-zusammenfallende
Endpunkt-Gruppen – wahrscheinliche Ursache der Trennung“, obwohl das Netz rechenbar ist.

**Hydraulik.** Der Dialog „Netz generieren“ hat keine Einheiten an den Feldern. Die
Initialisierung (30 s) erhöht die Pumpenförderhöhe stillschweigend von 1,5 auf 3,3 bar. Die
Zeitreihe in der Voreinstellung (detailliert, ganzes Jahr, 1 Prozess) lief nach 60 min ohne
jedes Lebenszeichen weiter – hochgerechnet 86–170 min. Ein Speichern in dieser Zeit
(z. B. „Speichern und schließen“) sicherte einen Zwischenzustand, der danach nie wieder
konvergierte.

**Erzeuger.** Vier Konfigurationen ließen sich in Sekunden anlegen und rechnen, die Optimierung
läuft in ~5 s, Sensitivität mit 125 Rechnungen in 32 s. Fachlich auffällig: Der Lastgang ist
doppelt so groß wie der Gebäudebedarf (Ursache: Befund K1), der Primärenergiefaktor *steigt* mit
BHKW, der Optimierer wählt 773 m² Kollektor mit 16 m³ Speicher. Die Infrastrukturkosten sind
Platzhalter (Wärmenetz pauschal 2 Mio. €), solange man nicht „Kosten aus geoJSON berechnen“ klickt.

**Freiburg (UTM 32).** Die Excel-Datei (Windows-1252) bricht den Import mit
`UnicodeDecodeError` ab. Als UTF-8 erkennt der Mapping-Dialog „Nutzung“ und „Anteil WW“ nicht,
Straße und Hausnummer lassen sich nicht kombinieren, das Dezimalkomma rutscht durch und lässt
erst die Wärmebedarfsrechnung abstürzen. Geocoding im voreingestellten CRS 25833 liefert für
Freiburg x = −35 643 m ohne Warnung; „Vorschlagen“ stellt auf 25832 um, rechnet die Koordinaten
aber nicht um. Der Erzeuger, per Adresse geocodiert, landet ~450 km entfernt. Das OSMnx-Netz wird
auf der Karte bei Gmunden (Österreich) gezeichnet. MST/Advanced MST erzeugen Netze, in denen ein
Hausanschluss nicht angebunden ist – welcher, sagt die Meldung nicht.

**Dorf Ostritz über OSM.** Die Gebäudeabfrage scheiterte viermal („Server load too high“) und
lief erst eine Stunde später. Die Umwandlung in die Gebäude-CSV dauerte ~20 min für
239 Gebäude, alle mit 30 MWh/a und Typ HMF (auch Kirche und Garagen), 212 mit derselben Adresse,
weil Nominatim wegen fehlender Drosselung mit HTTP 429 sperrte. Das Ergebnis landet nicht im
Projekt-CSV, sondern in `Gebäudedaten/OSM_building_data.csv` – wieder manuell kopieren. Danach
lief die Kette aber auch mit 239 Gebäuden durch (Netz 72 s, Hydraulik-Initialisierung 177 s,
vereinfachte Zeitreihe 5 s) – inklusive der Kirche als 30-MWh-Abnehmer „Spanntigstraße 5“.

## 4. Befunde

Schweregrad: **K** = falsche Ergebnisse, Datenverlust oder Workflow nicht abschließbar ·
**H** = großer Stolperstein / Blocker mit Umweg · **M** = Bedienbarkeit/Robustheit ·
**N** = Kosmetik. Alle K- und H-Befunde wurden im Lauf reproduziert, die Code-Stellen sind
verifiziert.

### 4.1 Kritisch (K)

**K1 – Wärmeverluste der Rohre 2–4× zu hoch.**
Die Dimensionierung setzt `std_type`, `inner_diameter_mm`, `u_w_per_m2k`, `k_mm`, aber nicht
`outer_diameter_mm` ([utilities.py:541](src/districtheatingsim/net_simulation_pandapipes/utilities.py#L541),
720, 739, 774). Der u-Wert wird mit dem Außendurchmesser des *neuen* Typs auf W/(m²K) umgerechnet,
pandapipes multipliziert aber mit dem im Netz stehenden Außendurchmesser des Starttyps
(`alpha * π * DO`, pandapipes `pf/derivative_toolbox.py:97`). Zittau: 130 von 146 Rohren falsch,
Rohrverluste im Auslegungsfall 126 kW statt 54 kW; Jahresbilanz 49 % Verlust (vereinfachte
Zeitreihe), Sommerwoche 57 % (detailliert). Für DN20-Hausanschlüsse beträgt der Fehler Faktor 4,25.
→ `outer_diameter_mm` an allen vier Stellen mitsetzen, Migration für gespeicherte Netze,
Regressionstest „Rohrverlust W/m je DN gegen Katalogwert“. Der Golden-Master-Test hat den
Fehler vermutlich eingefroren.

**K2 – CRS-Behandlung für Projekte außerhalb UTM 33 inkonsistent.**
- Neue Projekte bekommen immer EPSG:25833, ohne Hinweis. Freiburg geocodiert zu x = −35 643 m.
- CRS-Wechsel (Combo oder „Vorschlagen“, [project_tab.py:273](src/districtheatingsim/gui/ProjectTab/project_tab.py#L273))
  speichert nur das neue CRS; vorhandene `UTM_X/UTM_Y` werden **nicht** umprojiziert.
- „Adresse geocodieren“ im Netzdialog ruft `get_coordinates` ohne Ziel-CRS auf → immer 25833
  ([layer_generation_dialog.py:493](src/districtheatingsim/gui/LeafletTab/layer_generation_dialog.py#L493),
  [geocoding.py:27](src/districtheatingsim/geocoding/geocoding.py#L27)). Freiburg: Erzeuger bei
  (−35 094 / 5 338 444) statt (412 551 / 5 314 169).
- Der OSMnx-Export übergibt keine CRS ([osmnx_steiner_network.py:678](src/districtheatingsim/net_generation/osmnx_steiner_network.py#L678);
  MST tut es, [import_and_create_layers.py:262](src/districtheatingsim/net_generation/import_and_create_layers.py#L262))
  → `Wärmenetz.geojson` ist als 25833 etikettiert, die Karte zeichnet das Freiburger Netz bei
  Gmunden.

→ CRS beim ersten Geocoding automatisch aus dem Ort bestimmen und dann sperren oder bei Wechsel
alle Projektgeometrien umprojizieren; alle Defaults `EPSG:25833` in Funktionssignaturen durch
explizite Übergabe ersetzen (29 Fundstellen mit fest kodiertem 25833-Default).

**K3 – „CSV importieren“ übernimmt korrekt formatierte Dateien nicht ins Projekt.**
Der Fast-Path lädt die Quelldatei direkt und setzt sie als aktuelle Datei
([project_tab.py:332](src/districtheatingsim/gui/ProjectTab/project_tab.py#L332)); nur der
Mapping-Pfad speichert nach `Quartier IST.csv`. Folgen: Projektdatei bleibt leer,
Wärmebedarf scheitert, und „Geokoordinaten berechnen“/„CSV speichern“ **überschreiben die
Originaldatei des Nutzers** außerhalb des Projekts.
→ Fast-Path ebenfalls ins Projekt kopieren; Tabellenkopf zeigt immer, welche Datei bearbeitet wird.

**K4 – Speichern während laufender Berechnung beschädigt das Projekt.**
`saveNet`/`save_all_project_results` prüfen nicht, ob ein Netz-Thread läuft. Das gespeicherte
Zwischen-Netz (Controller/Zeitreihenzustand) konvergiert danach weder detailliert noch
vereinfacht („design-state … NaN“). Gleiches gilt für „Speichern und schließen“.
→ Speichern/Schließen sperren oder Berechnung vorher sauber beenden; Netz immer aus einer Kopie
ohne Controller speichern.

**K5 – OSM → Gebäude-CSV erzeugt unbrauchbare Daten.**
- Reverse-Geocoding je Gebäude ohne Ratenbegrenzung
  ([building_csv.py:153](src/districtheatingsim/geocoding/building_csv.py#L153); das normale
  Geocoding nutzt `RateLimiter`) → Nominatim HTTP 429; jede Fehlanfrage fällt stillschweigend auf
  die im Dialog vorbelegte Adresse des *ersten* Gebäudes zurück → 212 von 239 Gebäuden
  „Spanntigstraße 5“.
- Vorhandene OSM-Adressen (`addr:street`/`addr:housenumber`, bei 183 Gebäuden vorhanden) werden
  ignoriert.
- Alle Gebäude erhalten denselben Wärmebedarf (30 MWh) und Typ (HMF) – auch Kirche, Garagen,
  Nebengebäude; Grundfläche/Geschosse werden nicht genutzt. Ostritz: 4,2 GWh/a für einen Dorfkern.
- Ergebnis landet in `Gebäudedaten/OSM_building_data.csv`, nicht im Projekt-CSV.
- Die GeoJSON wird ohne Encoding geöffnet ([building_csv.py:118](src/districtheatingsim/geocoding/building_csv.py#L118)).
→ OSM-Adressen zuerst nutzen, Rest gedrosselt nachschlagen, Fehlschläge leer lassen und melden;
Nebengebäude filtern; Bedarf aus Grundfläche × Geschosse × spezifischem Kennwert vorschlagen;
Ergebnis als Projekt-CSV übernehmen (mit Rückfrage).

**K6 – Nicht beschreibbarer Installationsordner → Projekte öffnen lautlos nicht.**
`recent_projects.json` liegt im Paketordner ([main_data_manager.py:64](src/districtheatingsim/gui/MainTab/main_data_manager.py#L64)),
`save_config` reicht Schreibfehler weiter, `on_project_selected` verschluckt sie
(`except Exception: pass`, [main_view.py:291](src/districtheatingsim/gui/MainTab/main_view.py#L291)).
Mit schreibgeschützter Datei reproduziert: Statuszeile „Kein Projektordner ausgewählt“, keine
Daten, keine Meldung. Betrifft Installationen unter „C:\Programme“ und schreibgeschützte
site-packages. Dasselbe gilt für das Beispielprojekt (wird im Installationsordner geöffnet und
überschrieben).
→ Benutzerkonfiguration nach `%APPDATA%\DistrictHeatingSim`; Beispielprojekt beim ersten Öffnen in
`Dokumente\DistrictHeatingSim` kopieren; keine stummen `except: pass` um Projekt öffnen.

### 4.2 Hoch (H)

**H1 – Voreinstellung der Jahreszeitreihe.** Detailliert/1 Prozess: 24 h = 15–28 s,
168 h = 99 s → 86–170 min/Jahr für 15 Gebäude; mit 4 Prozessen 34 min/Jahr; vereinfacht 0,2–2 s.
Keine Fortschrittsanzeige (nur Endlosbalken), kein Abbruch; `NetCalculationThread.stop()` setzt
`requestInterruption()`, das `run()` nie prüft, und wartet dann – Schließen der App während der
Rechnung friert ein ([net_calculation_threads.py:150](src/districtheatingsim/gui/NetSimulationTab/net_calculation_threads.py#L150)).
Die vereinfachte Rechnung überschätzt Sommerverluste ~2× gegenüber der detaillierten.
→ Default „vereinfacht“ oder Worker = Kernzahl−1; Fortschritt + Restzeit über pandapipes-Callback;
Abbruch zwischen Zeitschritten.

**H2 – Hintergrundkarte.** Standard-Layer CARTO Light/Dark liefern „API KEY REQUIRED“
([main.js:20](src/districtheatingsim/leaflet/main.js#L20)); OSM-Kacheln funktionierten im Test.
→ OSM (mit Attribution) oder ein schlüsselfreier Dienst als Default, Fallback bei Kachelfehlern.

**H3 – Overpass/Nominatim ohne Fehlerstrategie.** Ein einziger Overpass-Endpunkt, kein Retry
([import_osm_data_geojson.py:19](src/districtheatingsim/osm/import_osm_data_geojson.py#L19));
2 von 3 Download-Sitzungen scheiterten zunächst (RemoteDisconnected, „Server load too high“),
der Nutzer sieht Tracebacks. OSMnx (das selbst wiederholt) lief dagegen durch.
→ Retry mit Backoff, verständliche Meldung („Server überlastet – in X min erneut versuchen“),
lokaler Cache.

**H4 – Netzgenerierung und Konnektivität.** MST/Advanced MST erzeugen in Freiburg Netze mit
12 nicht angebundenen Hausanschlüssen + Erzeuger; nach Auto-Snap bleibt 1 Hausanschluss getrennt.
Die Meldung nennt das Gebäude nicht; auf der Karte wird es nicht markiert. Gleichzeitig meldet
die Prüfung bei rechenbaren OSMnx-Netzen „74“ bzw. „463 fast-zusammenfallende Endpunkt-Gruppen –
wahrscheinliche Ursache der Trennung“ (Fehlalarm; beide Netze ließen sich initialisieren). „Advanced MST“ startet ohne Prüfung, ob
`Straßen.geojson` existiert, und scheitert mit Traceback.
→ Snap direkt im Generator; betroffene Gebäude namentlich + auf der Karte markieren;
Warnstufe nur bei echter Trennung; Modi ohne Straßendatei deaktivieren.

**H5 – Import realer Tabellen.** Excel-CSV (cp1252) → `UnicodeDecodeError`
([csv_import_dialog.py:177](src/districtheatingsim/gui/ProjectTab/csv_import_dialog.py#L177));
Dezimalkomma passiert Vorschau und Import und bricht erst die Wärmebedarfsrechnung ab; Straße +
Hausnummer nicht kombinierbar; Aliase fehlen („Nutzung“, „Anteil WW“); Pflichtfeld WW-Anteil
ohne Standardwert.
→ Encoding-Erkennung (utf-8-sig → cp1252), Dezimalkomma normalisieren, Spalten kombinieren,
Typvalidierung schon im Dialog.

**H6 – Geocoding-Qualität wird nicht gemeldet.** Der Projekt-Tab verwirft die Zusammenfassung
(`fname, _summary = result`, [project_tab.py:626](src/districtheatingsim/gui/ProjectTab/project_tab.py#L626)),
nur der Karten-Tab zeigt fehlgeschlagene Adressen. Nicht gemeldet werden außerdem: identische
Koordinaten (4× Vaubanallee ohne Hausnummer), Rückfall auf Straßenmittelpunkt (Kurt-Tucholsky-
Straße 9 liegt exakt auf der Straßenachse), Koordinaten außerhalb der CRS-Zone.

**H7 – BOM wächst bei jedem Laden/Speichern.** Projekt-Tab liest `utf-8`, schreibt `utf-8-sig`
([project_tab.py:68](src/districtheatingsim/gui/ProjectTab/project_tab.py#L68)/85); nach drei
Zyklen heißt die erste Spalte für pandas `'\ufeff\ufeffLand'` – Import-Fast-Path und
`Land`-Attribut im Netz ([net_generation.py:328](src/districtheatingsim/net_generation/net_generation.py#L328))
gehen still verloren. Das Geocoding (`process_data`) verhält sich ebenso.

**H8 – Doppelklick im Projektbaum zerstört den Projektzustand.** Doppelklick auf einen
Nicht-Varianten-Ordner macht ihn zum Projekt
([project_tab.py:255](src/districtheatingsim/gui/ProjectTab/project_tab.py#L255)): TRY/COP = None,
CRS auf Default, Unterordner in „Zuletzt geöffnet“.

**H9 – Klima- und Standortdaten nur für Görlitz.** Mitgeliefert ist ein TRY (Görlitz), jedes neue
Projekt bekommt es ohne Hinweis; VDI 4655 mit fester Klimazone 9 und 2 Personen/Haushalt
([heat_requirement_calculation_csv.py:165](src/districtheatingsim/heat_requirement/heat_requirement_calculation_csv.py#L165));
Solarthermie-Standort von Hand, vorbelegt mit Görlitz.
→ Beim Anlegen Ort abfragen, TRY-Region/Klimazone vorschlagen bzw. Download-Hinweis (DWD),
Solarstandort aus Erzeugerkoordinate übernehmen.

**H10 – Ergebnisse veralten unbemerkt.** Die Variantenkopie übernimmt alle Erzeugerergebnisse;
nach Änderung von Netz/Lastgang erscheinen sie im Vergleich unverändert als
„Variante 2 · …“. Keine Kennzeichnung „veraltet“ entlang der Kette Gebäude → Lastgang → Netz →
Erzeuger.

### 4.3 Mittel (M)

| ID | Befund | Beleg / Ort |
|----|--------|-------------|
| M1 | Fehlermeldungen als rohe, oft englische Tracebacks („Unknown building types: nan“, „unsupported operand … NoneType“, „No optimization parameters available“, „[WinError 183]“) | heat_demand_thread, net_calculation_threads, _06 thread, main_presenter |
| M2 | Einheiten fehlen (Netzkonfiguration: Druck, ΔT; BHKW: Leistung, Speicher); Netzspeicher-Dialog komplett englisch; Standardknöpfe „OK/Cancel“ (keine Qt-Übersetzung); englische Reste: Dateibaum „Name/Size/Type“, Karte „Click on the map…“, Diagramm „Second y-Axis“, Netzlegende „pipe/heat_consumer/circ_pump“, Rohrnamen „flow line 0“ | network_config_tab, technology_dialogs/_storage, main.js |
| M3 | Karte: Netz-Layer beim Öffnen 3× (jeder Ordnerwechsel hängt einen weiteren `loadFinished`-Callback an, [leaflet_tab.py:605](src/districtheatingsim/gui/LeafletTab/leaflet_tab.py#L605)); alte Layer bleiben bei Neugenerierung; `fitBounds` je Layer endet auf dem Einzelpunkt Erzeuger ([geojsonHandler.js:220](src/districtheatingsim/leaflet/geojsonHandler.js#L220)); leerer „Neuer Layer (0)“ | Screenshots p0/p1b/p3c |
| M4 | Projektfremde/falsche Vorbelegungen: Erzeugerkoordinate mit Tippfehler `55666161` ([layer_generation_dialog.py:222](src/districtheatingsim/gui/LeafletTab/layer_generation_dialog.py#L222)), Adresse Bad Muskau, Straßendialog „Zittau“, Solarthermie Lon −14,42 / STD +15 (inkonsistentes Vorzeichen → Stundenprofil ~1 h verschoben, Jahressumme +0,2 %) | _schemas.py, osm_dialogs.py:94 |
| M5 | „Projekt öffnen“ abbrechen → trotzdem Speicherfrage, dann „Projektpfad '' nicht gefunden“ | main_view.py:732 |
| M6 | Speichern ohne Änderungserkennung; jedes Schließen fragt und warnt „keine Versionierung implementiert“; Default-Knopf „Speichern“ überschreibt | main_view.py:1020 |
| M7 | Variantenvergleich: Kennzahlen „--“ bis „Projekte aktualisieren“; Kreisdiagramme im Reiter „Energie“ auf Punktgröße kollabiert; PtH und Gaskessel gleiche Farbe | comparison_tab |
| M8 | Zeitreihe startbar trotz gescheiterter Initialisierung; Energiesystem mit fehlendem Lastgang → unbehandelte `FileNotFoundError` (`preprocessData` fängt nur ValueError/KeyError) | net_simulation_tab.py:259, _01 main tab:571 |
| M9 | „Ergebnisse als CSV exportieren…“ öffnet keinen Dialog, schreibt immer `calculated_heat_generation.csv`, unabhängig von der Konfiguration | _01 main tab:789 |
| M10 | Ergebnisdiagramm: y-Achse nicht bei 0 (150-kW-BHKW fast unsichtbar); Auswahlliste zeigt interne Namen („BHKW_1_betrieb_mask“) | _07_results_tab |
| M11 | Infrastrukturkosten sind Platzhalter (Netz 2 Mio. €, Planung 0,5 Mio. €) statt aus dem Netz berechnet; Spalten „T_N, F_inst, F_w_insp“ unerklärt | _05_cost_tab |
| M12 | Pumpe: Vorgabe 1,5 bar wird nach Dimensionierung stillschweigend 3,3 bar; v_max = 1 m/s auch für DN20-Hausanschlüsse | utilities.py |
| M13 | Zwei Gebäude-Editoren mit verschiedenen Vorlagen (Projekt-Tab 13 Spalten, Wärmebedarf-Tab 18 Spalten mit Beispiel „MFH“) | building_tab.py:213 |
| M14 | Fortschrittstracker: Straßendownload als Pflichtschritt (OSMnx braucht ihn nicht), „Schritt 3“ doppelt, Tab-Namen im Text veraltet; Status widerspricht Tabelle | project_tab.py:161 |
| M15 | Fachliche Plausibilität: PEF steigt mit BHKW (1,46 vs. 1,22) während CO₂ sinkt (Stromgutschrift nur bei CO₂?); Optimierer wählt 773 m² Kollektor / 16 m³ Speicher; Gewichtungsdialog ohne Erklärung; Netzspeicher 50 €/m³ vs. 750 €/m³ bei Solar-/Pufferspeicher | chp.py:393, _schemas.py |
| M16 | Sensitivität: Standardbereich Gas 30–60 €/MWh schließt den Basispreis 70 nicht ein; 3D-Fläche mit überlappender Legende schwer lesbar | _08_sensitivity_tab |
| M17 | Projektname existiert → technischer Fehler „[WinError 183]“; Variantenwechsel fragt jedes Mal nach Erzeugerkonfiguration | main_presenter |

### 4.4 Niedrig (N)

- Tippfehler „Sensivitätsuntersuchung“; „Niedertemperaturnetz“ mit 85/70 °C.
- Projekt-Tab: Dateibaum-Spalten abgeschnitten („Definit…“); Fortschrittstext auf blauem Balken
  kaum lesbar; zwei Erfolgsmeldungen beim Anlegen.
- Netzdialog: Vorschau beschriftet UTM-Meter als „Latitude/Longitude“; Combo „Importtyp“ mit nur
  einer Option; Erzeuger heißt „Erzeugerstandort 162“ statt „1“.
- Doku: kein Benutzerhandbuch; README verspricht PDF-Bericht, den es nicht gibt;
  `docs/source/gui_framework.rst` verweist auf nicht existierende `districtheatingsim.guiexamples.rst`.

## 5. Messwerte

| Schritt | Umfang | Dauer |
|---------|--------|-------|
| Programmstart bis Willkommensbildschirm | – | 0,6–0,7 s |
| Projekt öffnen inkl. Ergebnisse | Zittau | ~3 s |
| Geocoding (Nominatim, gedrosselt) | 15 / 12 Adressen | 14,5 s / 11,8 s |
| Wärmebedarf | 15 / 12 / 239 Gebäude | 1,1 s / 0,9 s / 6,8 s |
| OSM-Straßen (Puffer 150 m) | Freiburg | 133 s (Zittau: Abbruch nach 58 s) |
| OSM-Gebäude (Polygon) | Ostritz, 239 | 1,6 s (nach 4 Fehlversuchen) |
| OSM → Gebäude-CSV (Reverse-Geocoding) | 239 Gebäude | ~20 min |
| Netzgenerierung OSMnx | 15 / 12 / 239 Gebäude | 9 s / 193 s / 72 s (Ostritz: 7,7 km Trasse) |
| Netzgenerierung MST / Advanced MST | 12 Gebäude | < 1 s |
| Netzinitialisierung inkl. Durchmesseroptimierung | 15 Gebäude, 146 Rohre / 239 Gebäude, 966 Rohre | 22–30 s / 177 s |
| Zeitreihe detailliert, 1 Prozess | 24 h / 168 h | 15–28 s / 99 s (→ 86–170 min/Jahr) |
| Zeitreihe detailliert, 4 Prozesse | 672 h | 158 s (→ 34 min/Jahr) |
| Zeitreihe vereinfacht | 8760 h, 15 / 239 Gebäude | 0,2–2 s / 5 s |
| Erzeugerberechnung | 1–4 Technologien | 0,4–2,9 s |
| Optimierung | Solar + Biomasse + Gas | 5 s |
| Sensitivität | 125 Rechnungen | 32 s |

## 6. Verbesserungsstrategie

Leitidee: **Erst die Zahlen richtig machen, dann den Einstieg führen, dann absichern.** Jede Stufe
endet mit einem automatisierten Test, der den Befund dauerhaft festhält.

### Stufe 1 – Korrektheit (1–2 Wochen, überwiegend Einzeiler)

| Ziel | Maßnahmen | Befunde |
|------|-----------|---------|
| Richtige Netzverluste | `outer_diameter_mm` bei jedem Typwechsel setzen; Migration gespeicherter Netze; Test „W/m je DN“ gegen ISOPLUS-Katalog; Golden-Master neu einfrieren | K1 |
| CRS überall explizit | Default-CRS-Parameter entfernen; Erzeuger-Geocoding und OSMnx-Export mit Projekt-CRS; CRS-Wechsel projiziert CSV + Netz mit oder ist nach dem ersten Geocoding gesperrt; Warnung bei Koordinaten außerhalb der Zone | K2 |
| Import ins Projekt | Fast-Path kopiert nach `Quartier IST.csv`; einheitlich `utf-8-sig` lesen/schreiben | K3, H7 |
| Keine Zwischenstände speichern | Speichern/Schließen während laufender Threads sperren; Netz ohne Controller speichern | K4 |
| Installierbarkeit | Benutzerdaten nach `%APPDATA%`; Beispielprojekt in Benutzerordner kopieren; stumme `except: pass` entfernen | K6 |
| Karte | OSM-Kacheln als Default; Map-Reload-Callback ersetzen statt anhängen; `fitBounds` über alle Layer | H2, M3 |

### Stufe 2 – Geführter Daten-Einstieg (2–4 Wochen)

Der größte Teil der Reibung entsteht vor der ersten Berechnung. Vorschlag: ein
**Assistent „Neues Projekt“** mit drei Seiten:

1. **Ort** (Adresse oder Kartenklick) → CRS, TRY-Region/Klimazone, Solarstandort, OSM-Bereich
   werden daraus abgeleitet; fehlt ein passendes TRY, Hinweis mit DWD-Link.
2. **Gebäude** – eine von drei Quellen, alle münden in *dieselbe* Projektdatei:
   - Tabelle importieren: Encoding-/Dezimal-Erkennung, Spalten kombinieren, Validierung mit
     Zeilenmarkierung *vor* dem Speichern;
   - OSM: Adressen aus `addr:*`, Nebengebäude filtern, Bedarf aus Fläche × Geschosse ×
     Kennwert vorschlagen, gedrosseltes Rest-Geocoding;
   - manuell in der Tabelle.
   Danach ein **Qualitätsbericht**: nicht gefunden / gleiche Koordinaten / nur Straße gefunden /
   unplausibler Bedarf – jeweils anklickbar auf der Karte.
3. **Netz & Erzeuger-Standort** (Kartenklick statt Koordinatenfeld; Modus OSMnx als Default,
   MST nur mit vorhandener Straßendatei).

Ergänzend: Projektfortschritt als Checkliste mit „veraltet“-Status je Stufe (H10), ein Gebäude-
Editor statt zwei (M13).

### Stufe 3 – Rechnen ohne Warten und ohne Rätsel (2–3 Wochen)

- Zeitreihe: Default „vereinfacht“ für die Erzeugerauslegung, „detailliert“ als bewusste
  Validierung mit Worker = Kernzahl−1, Fortschritt/Restzeit, Abbruch (H1). Die vereinfachte
  Methode gegen die detaillierte kalibrieren (Sommerverluste).
- Externe Dienste: Retry/Backoff, Ausweich-Endpunkte, lokaler Cache, verständliche Meldungen (H3).
- Fehlermeldungen: zentrale Übersetzung typischer Ausnahmen in deutsche Handlungshinweise,
  Traceback nur in „Details“/Logdatei (M1).
- Konnektivität: Snap im Generator, betroffene Gebäude namentlich und auf der Karte (H4).

### Stufe 4 – Fachliche Plausibilität und Transparenz (laufend)

- Plausibilitätsampel im Ergebnis: Verlustanteil, Wärmedichte (MWh/(m·a)), spezifischer
  Druckverlust, Speicher je m² Kollektor, Volllaststunden je Erzeuger (M15, K1).
- Infrastrukturkosten automatisch aus dem Netz vorbelegen, Platzhalter deutlich kennzeichnen (M11).
- PEF-/CO₂-Methodik (Stromgutschrift KWK) dokumentieren und konsistent machen (M15).
- Einheiten und Tooltips in allen Dialogen, durchgehend deutsch (M2).

### Stufe 5 – Qualitätssicherung, damit es so bleibt

- **GUI-End-to-End-Tests** mit dem in diesem Test genutzten Harness (Qt offscreen, Popup-Protokoll,
  Screenshots) als `pytest -m e2e`: je ein Szenario Ost-/West-Deutschland, Excel-Import, OSM-Weg;
  Netzwerkdienste gemockt. Damit wären K1–K3, H6–H8, M3, M5 automatisch aufgefallen.
- Physikalische Invarianten als Tests (Energiebilanz Netz, Verlust W/m je DN, Konnektivität
  frisch generierter Netze).
- Kurzes Benutzerhandbuch (ein Durchlauf „Mein erstes Quartier“ mit Screenshots, CSV-Format,
  Gebäudetypen, Klimadaten) und README an den tatsächlichen Funktionsumfang anpassen (N).

### Empfohlene Reihenfolge

1. K1, K2, K3, K4, K6 + H2 (Korrektheit und Installierbarkeit; jede Zahl, die jetzt berechnet
   wird, ist sonst wertlos).
2. H1, H3, H5, H6, H7, H8 (die häufigsten Abbrüche im Erstkontakt).
3. Assistent „Neues Projekt“ inkl. OSM-Neubau (K5, H9, M13, M14).
4. E2E-Tests + Handbuch parallel zu 2–3, damit Fixes nicht wieder verloren gehen.
5. Plausibilitätsampel, Kosten, Methodik, Feinschliff (M/N).
