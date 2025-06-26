#!/bin/bash

# Stoppe bei Fehler
set -e

# Verzeichnisse
BUILD_DIR="build/html"
TARGET_DIR="docs"

# Baue die Doku
echo "Generiere Sphinx-Dokumentation..."
make html

# Lösche alte HTML-Dateien im /docs (außer .git-Dateien)
echo "Bereinige alten Inhalt in /$TARGET_DIR..."
find $TARGET_DIR -type f -not -name '.git*' -delete

# Kopiere neue HTML-Dateien
echo "Kopiere neue HTML-Dateien nach /$TARGET_DIR..."
cp -r $BUILD_DIR/* $TARGET_DIR/

# Git Commit & Push
echo "Committe Änderungen..."
git add $TARGET_DIR
git commit -m "Update Sphinx HTML-Doku"
git push

echo "Dokumentation aktualisiert und gepusht!"
