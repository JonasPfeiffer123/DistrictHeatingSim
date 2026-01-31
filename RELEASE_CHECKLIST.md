# Pre-Release Checklist für Version 1.0.0

## ✅ Code & Dokumentation
- [x] Alle Versionsnummern auf 1.0.0 aktualisiert
  - [x] setup.py
  - [x] docs/source/conf.py
  - [x] docs/source/index.rst
  - [x] src/districtheatingsim/__init__.py
- [x] CHANGELOG.md erstellt mit allen Änderungen
- [x] Dokumentation zu Sphinx reST migriert
- [x] Beispiele getestet (26/29 funktionsfähig)

## 📋 Vor dem Merge in main

### Tests & Validierung
- [ ] Alle Unit-Tests laufen durch (falls vorhanden)
  ```bash
  python -m pytest tests/
  ```
- [ ] Beispiele nochmal stichprobenartig testen:
  ```bash
  python examples/01_example_geocoding.py
  python examples/05_example_net_generation.py
  python examples/09_example_heat_generators.py
  python examples/16_interactive_matplotlib.py
  ```
- [ ] GUI startet ohne Fehler:
  ```bash
  python src/districtheatingsim/DistrictHeatingSim.py
  ```

### Dokumentation
- [ ] Sphinx Dokumentation bauen und prüfen:
  ```bash
  cd docs
  make clean
  make html
  # Prüfe docs/build/html/index.html im Browser
  ```
- [ ] README.md aktuell und korrekt?
- [ ] requirements.txt vollständig?
- [ ] documentation_requirements.txt aktuell?

### Code Quality
- [ ] Keine Debug-Print-Statements im Code
- [ ] Keine TODO-Kommentare, die vor Release erledigt sein müssen
- [ ] Keine hardcodierten Pfade für User-spezifische Daten
- [ ] Keine großen auskommentierte Code-Blöke

### Git & Repository
- [ ] Alle Änderungen committed
- [ ] .gitignore korrekt (keine __pycache__, .pyc, build/, dist/ im Repo)
- [ ] Keine sensiblen Daten im Repository
- [ ] Branch ist sauber (kein Merge-Konflikt)

## 🚀 Release Prozess

### 1. Branch Merge
```bash
# Stelle sicher, dass du auf develop bist
git checkout develop
git status
git pull origin develop

# Merge in main
git checkout main
git pull origin main
git merge develop

# Push nach GitHub
git push origin main
```

### 2. Tag erstellen
```bash
# Annotiertes Tag mit Changelog
git tag -a v1.0.0 -m "Release v1.0.0

Major release with complete Sphinx documentation and bug fixes.

Highlights:
- Complete Sphinx reST documentation
- 26/29 examples working
- Fixed 7 major bug categories
- Performance: 0.06s per building
- See CHANGELOG.md for full details"

# Tag pushen
git push origin v1.0.0
```

### 3. GitHub Release erstellen
- [ ] Gehe zu https://github.com/JonasPfeiffer123/DistrictHeatingSim/releases
- [ ] Klicke auf "Draft a new release"
- [ ] Wähle Tag: v1.0.0
- [ ] Release title: "DistrictHeatingSim v1.0.0 - First Major Release"
- [ ] Beschreibung aus CHANGELOG.md kopieren
- [ ] Optional: Assets hinzufügen
  - [ ] Executable (falls mit PyInstaller gebaut)
  - [ ] Dokumentation PDF (falls generiert)
- [ ] "Publish release" klicken

### 4. PyPI Upload (optional)
Falls du das Paket auf PyPI veröffentlichen möchtest:
```bash
# Build vorbereiten
python -m pip install --upgrade build twine

# Package bauen
python -m build

# Auf TestPyPI hochladen (zum Testen)
python -m twine upload --repository testpypi dist/*

# Auf PyPI hochladen
python -m twine upload dist/*
```

### 5. Post-Release
- [ ] develop Branch aktualisieren:
  ```bash
  git checkout develop
  git merge main
  git push origin develop
  ```
- [ ] Version in develop auf 1.1.0-dev setzen für nächste Entwicklung
- [ ] Release-Announcement (falls gewünscht)
  - GitHub Discussions
  - Twitter/LinkedIn
  - Projektwebseite

## ⚠️ Bekannte Einschränkungen (für Release Notes)

### Nicht funktionsfähige Beispiele
- `12_example_renovation_analysis.py` - Modul existiert nicht mehr
- Einige Utility-Skripte benötigen spezifische Testdaten

### Warnings
- Qt DeprecationWarning bei GUI-Beispielen (sipPyTypeDict)
- Pandas FutureWarnings bei BHKW_Speicher.py (dtype conversions)
- Matplotlib warnings bei einigen Plots

### TODO für zukünftige Versionen
- STES.calculate_operational_costs() Implementierung
- Pandapipes Konvergenz-Verbesserungen für komplexe Netze
- renovation_analysis Modul wiederherstellen oder Beispiel entfernen

## 📊 Testing Metriken
- **Beispiel-Erfolgsrate**: 89.7% (26/29)
- **Getestete Python-Version**: 3.11.9
- **Dokumentierte Module**: 90+
- **Performance**: 0.06s pro Gebäude (Netzgenerierung)
- **Benchmark Range**: 25-300 Gebäude getestet

## 🔍 Abschließende Prüfungen

### Lizenz & Legal
- [ ] LICENSE Datei vorhanden und aktuell
- [ ] Copyright-Angaben korrekt (2025)
- [ ] Keine Copyright-Verletzungen in Abhängigkeiten

### Dependencies
- [ ] Alle Requirements in requirements.txt
- [ ] Keine pinned versions ohne Grund
- [ ] Kompatibilität mit aktuellen Versionen geprüft

### Plattformen
- [ ] Windows getestet (primäre Plattform)
- [ ] Linux getestet (optional)
- [ ] macOS getestet (optional)
