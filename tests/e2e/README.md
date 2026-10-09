# GUI-End-to-End-Szenarien (Anwendertest)

Referenzläufe aus dem Anwendertest vom 2026-10-08 ([ANWENDERTEST_2026-10-08.md](../../ANWENDERTEST_2026-10-08.md)).
Sie bedienen die **echte** Hauptanwendung headless (Qt `offscreen`) über dieselben Slots wie
Klicks und Menüs, protokollieren jede Meldung und jeden Dialog, den ein Anwender sähe, und
legen Screenshots ab. Mit ihnen lassen sich die Befunde vor und nach einem Fix nachstellen.

Die Szenarien sind **keine pytest-Tests** (kein `test_`-Präfix, werden nicht eingesammelt):
Sie nutzen die echten Dienste Nominatim, Overpass und OSMnx und laufen Minuten bis Stunden.

## Ausführen

```sh
python tests/e2e/scenario_p1_zittau.py              # alle Schritte
python tests/e2e/scenario_p1_zittau.py energy       # nur einzelne Schritte (Projekt muss existieren)
python tests/e2e/analysis_net_losses.py             # braucht das initialisierte Netz aus P1
```

Ausgaben landen in `tests/e2e/_work/` (git-ignoriert) oder in `$DHS_E2E_WORKDIR`:
`projects/` (die Szenario-Projekte), `shots/` (Screenshots), `events.log` (alle
Meldungen/Dialoge mit Phase), `applogs/` (Logdatei der Anwendung), eine eigene
`recent_projects.json`. Die echte „Zuletzt geöffnet“-Liste und das mitgelieferte
Beispielprojekt werden nie verändert.

## Inhalt

| Datei | Inhalt | Befunde |
|-------|--------|---------|
| `harness.py` | Start der App, Antwort-Warteschlangen für Datei-/Eingabe-/Meldungsdialoge, Dialog-Handler, Screenshots, Karten-Helfer, Schritt-Runner | – |
| `scenario_p0_example.py` | Görlitz-Beispiel (Kopie) öffnen, alle Tabs ansehen | K6, H2, M3, M7 |
| `scenario_p1_zittau.py` | Kern-Workflow mit Adress-CSV: Import, Geocoding, Wärmebedarf, Straßen, OSMnx-Netz, Hydraulik, 4 Erzeugerkonfigurationen, Variante 2, Vergleich, Optimierung, Sensitivität, Export | K1, K3, H3, H4, H10, M3, M9–M11, M15 |
| `scenario_p2_ostritz.py` | OSM-Gebäudeabfrage per Polygon, „CSV aus OSM-GeoJSON“, Netz und Hydraulik für ~240 Gebäude | K5, H3, H4 |
| `scenario_p3_freiburg.py` | Excel-Export (cp1252, Dezimalkomma, eigene Spalten) in UTM 32: Import, CRS, Geocoding, Erzeuger per Adresse, MST/Advanced MST/OSMnx | K2, H4–H6, H9 |
| `scenario_robustness.py` | Bedienfehler: Abbrechen, Doppelklick im Projektbaum, doppelter Name, Rechnen ohne Daten, Schließen, schreibgeschützte Konfiguration | K6, H8, M5, M6, M8, M17 |
| `analysis_net_losses.py` | Rohrverluste mit gespeichertem vs. katalogrichtigem Außendurchmesser | K1 |
| `analysis_timeseries.py` | Laufzeit und Verlustbilanz der Jahreszeitreihe (detailliert/parallel/vereinfacht) | H1, K1 |
| `analysis_solar_time.py` | Vorzeichen der Längengrade bei der Solarthermie | M4 |
| `inputs/` | Eingabedaten der Szenarien (die Excel-Datei bleibt byte-genau cp1252) | – |

Stellen, an denen ein Szenario einen bekannten Fehler umgeht, sind mit `WORKAROUND <Befund>`
markiert; Prüfpunkte mit `CHECK <Befund>` im `events.log`. Nach einem Fix sollte der Workaround
nicht mehr greifen und der Prüfpunkt das korrigierte Verhalten zeigen.

## Grenzen

- Plotly-Ansichten (Netzplot, Sankey) rendern im Offscreen-Modus leer; das ist kein Fehler der
  Anwendung.
- Freies Zeichnen/Editieren auf der Karte wird nur über die JavaScript-Schnittstelle nachgestellt
  (`draw_polygon_on_map`).
- Unter Windows werden die Systemschriften über `QT_QPA_FONTDIR` eingebunden; in einigen
  elternlosen Dialogen erscheinen trotzdem Ersatzzeichen.
