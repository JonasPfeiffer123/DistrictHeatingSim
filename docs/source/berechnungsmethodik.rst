Berechnungsmethodik
===================

Diese Seite beschreibt, wie DistrictHeatingSim rechnet: welche Verfahren, Standardwerte und
Annahmen hinter den Ergebnissen stehen und woher die Grenzwerte der Plausibilitätsampel kommen.
Die Bedienung beschreibt das :doc:`benutzerhandbuch`.

.. contents:: Inhalt
   :local:
   :depth: 1


Ablauf
------

Ein Projekt durchläuft fünf Schritte; jeder baut auf dem vorigen auf:

1. **Wärmebedarf** der Gebäude als Stundenlastgang (BDEW oder VDI 4655).
2. **Netz** entlang der Straßen (OpenStreetMap) mit Hausanschlüssen und Erzeugerstandort.
3. **Netzberechnung** mit `pandapipes <https://github.com/e2nIEE/pandapipes>`_: Auslegungsfall
   mit Rohrdimensionierung und Pumpenauslegung, danach eine Jahreszeitreihe.
4. **Erzeugerauslegung**: Einsatz der Erzeuger in Rangfolge über das Jahr, Kosten nach VDI 2067,
   CO₂ und Primärenergie, optional eine Optimierung der Anlagengrößen.
5. **Variantenvergleich** der Kennzahlen über Varianten und Erzeugerkonfigurationen.

Ändern sich die Eingaben eines Schritts, markiert das Programm die abhängigen Ergebnisse als
„veraltet“ (Fortschrittsanzeige, Variantenvergleich).


Wärmebedarf
-----------

Die Lastgänge berechnet `pyslpheat <https://github.com/JonasPfeiffer123/pyslpheat>`_ aus
Jahreswärmebedarf, Gebäudetyp, Warmwasseranteil und Testreferenzjahr (TRY) des Deutschen
Wetterdienstes.

* **Ein Verfahren je Projekt.** Gewerbe- und Wohngebäude nach BDEW (Wohngebäude als ``HEF``
  oder ``HMF``) oder Wohngebäude nach VDI 4655 (``EFH``, ``MFH``). Beides in einem Projekt lehnt
  das Programm ab, weil die Verfahren nicht zusammenpassen.
* **VDI 4655** liefert Viertelstundenwerte; sie werden energiegleich zu Stundenwerten summiert.
* **Klima:** Die Klimazone (eine der 15 TRY-Regionen) und die Personen je Haushalt sind
  Projekteinstellungen. Liegt das gewählte TRY mehr als 50 km vom Projektort entfernt, weist das
  Programm darauf hin.
* **Mindestlast:** Jeder Hausanschluss nimmt mindestens 2 % seiner eigenen Höchstlast ab, damit
  im Netz stets eine kleine Strömung bleibt.


Netzauslegung
-------------

Rohrdimensionierung
~~~~~~~~~~~~~~~~~~~

Die Leitungen werden aus dem ISOPLUS-Katalog von pandapipes gewählt. Die Dämmstärke (Standard,
1-fach oder 2-fach verstärkt) bleibt die des Start-Rohrtyps; geändert wird nur die Nennweite.
Jede Leitung bekommt die kleinste Nennweite, die **beide** Grenzen einhält:

* **Strömungsgeschwindigkeit** ≤ *v*\ :sub:`max` (Standard 1 m/s),
* **Druckverlust durch Reibung** ≤ *R*\ :sub:`max` (Standard 300 Pa/m; ein leeres Feld rechnet
  nur mit der Geschwindigkeit).

Mit der Geschwindigkeit allein hätten kleine Leitungen sehr hohe Verluste: DN 20 verliert bei
1 m/s rund 690 Pa/m (Rauigkeit 0,1 mm), DN 100 rund 90 Pa/m. In großen Leitungen entscheidet
deshalb die Geschwindigkeit, in Hausanschlüssen und kleinen Verteilleitungen der Druckverlust.
Der Druckverlust ist der reine Reibungsanteil; Höhenunterschiede zählen nicht.

Die Wahl des Grenzwerts ist eine Abwägung zwischen Pumpenergie und Wärmeverlust: größere Rohre
senken den Druckverlust, verlieren aber mehr Wärme und kosten mehr. Ein Vergleich an zwei Netzen
(Auslegung mit *v*\ :sub:`max` = 1 m/s, vereinfachte Jahreszeitreihe):

.. list-table::
   :header-rows: 1
   :widths: 22 14 18 16 16 16

   * - Grenze
     - Förderhöhe
     - Rohrmaterial
     - Wärmeverlust Auslegung
     - Pumpenstrom Jahr
     - Netzverluste Jahr
   * - Zittau, ohne Grenze
     - 5,40 bar
     - –
     - 52,7 kW
     - 19,3 MWh
     - 438,9 MWh
   * - Zittau, 300 Pa/m
     - 3,24 bar
     - +3,4 %
     - +2,8 %
     - 11,7 MWh
     - 451,7 MWh
   * - Zittau, 150 Pa/m
     - 2,89 bar
     - +11,5 %
     - +6,1 %
     -
     -
   * - Zittau, 100 Pa/m
     - 2,23 bar
     - +19,1 %
     - +9,5 %
     -
     -
   * - Görlitz, ohne Grenze
     - 2,32 bar
     - –
     - 25,6 kW
     - 9,6 MWh
     - 166,0 MWh
   * - Görlitz, 300 Pa/m
     - 2,19 bar
     - +0,5 %
     - +0,7 %
     - 9,0 MWh
     - 167,5 MWh

300 Pa/m nimmt den größten Teil der Förderhöhe für wenig zusätzlichen Wärmeverlust; energetisch
gleichen sich eingesparter Pumpenstrom und zusätzlicher Wärmeverlust etwa aus. Der Gewinn ist
vor allem ein kleinerer Differenzdruck an den Hausstationen nahe der Heizzentrale. Etwa 100 Pa/m
gilt in der Praxis als vorsichtiger Wert für Hausanschlussleitungen [Energiforsk2021]_.

Pumpenauslegung
~~~~~~~~~~~~~~~

Die Hauptpumpe regelt auf den Schlechtpunkt: Sie erhöht die Förderhöhe, bis am ungünstigsten
Hausanschluss mindestens **1 bar** Differenzdruck anliegt. Der ungünstigste Anschluss wird in jeder
Iteration neu bestimmt, weil er sich mit der Rohrdimensionierung verschieben kann. Nach der
Initialisierung nennt das Programm die Förderhöhe (und den vorgegebenen Startwert), den
Differenzdruck am Schlechtpunkt, die höchste Geschwindigkeit und den höchsten Druckverlust.

Jahreszeitreihe
~~~~~~~~~~~~~~~

* **Vereinfacht (Standard):** Der Auslegungszustand wird mit dem stündlichen Gebäudebedarf
  skaliert. Die Netzverluste bleiben auf dem Wert des Auslegungsfalls, die Drücke ebenfalls; der
  Pumpenstrom ist deshalb eher eine obere Abschätzung. Ein Jahr dauert Sekunden.
* **Detailliert:** Für jede Stunde eine vollständige thermohydraulische Berechnung mit Reglern
  (Pumpe, Mindestvorlauftemperatur). Genauer, aber Minuten bis Stunden; optional auf mehrere
  Prozesse verteilt.


Erzeuger und Wirtschaftlichkeit
-------------------------------

Einsatz
~~~~~~~

Die Erzeuger decken den Lastgang in der Reihenfolge der Erzeugerliste: Jeder Erzeuger übernimmt
so viel der verbleibenden Last, wie seine Leistung, Mindestteillast und Betriebsweise zulassen.
Ein Netzspeicher (1D-Schichtenspeicher, siehe :doc:`thermal_storage`) puffert zwischen Erzeugung
und Last. Was am Ende übrig bleibt, erscheint als „Ungedeckter Bedarf“.

Kosten
~~~~~~

Die Wärmegestehungskosten (WGK) folgen der Annuitätenmethode nach VDI 2067 (kapital-, bedarfs-,
betriebsgebundene und sonstige Kosten; Standard: 20 Jahre Betrachtungszeitraum, 5 % Zins, 3 %
Preissteigerung). Eine Anlage, die keine Wärme liefert, behält ihre Investitionskosten.

* **Infrastruktur:** Solange keine eigenen Werte eingetragen sind, schätzt das Programm das Netz
  aus der Trassenlänge (1000 €/m inklusive Tiefbau) und die Hausanschlussstationen aus der
  Höchstlast (250 €/kW). Planung und weitere Posten sind Pauschalwerte und als solche markiert.
* **Speicherkosten:** Ein neuer Netzspeicher übernimmt als Startwert die typischen Kosten für sein
  Volumen,

  .. math::

     c(V) = 750\ \tfrac{\text{€}}{\text{m}^3} \cdot \left(\frac{V}{20\ \text{m}^3}\right)^{-0{,}37}

  angepasst an Pufferspeicher (750 €/m³ bei 20 m³), Behälterspeicher von 1.500–2.500 m³ (etwa
  150–100 €/m³ [store4grid]_) und dänische Erdbeckenspeicher (Dronninglund 60.000 m³: 38 €/m³,
  Vojens 210.000 m³: 24 €/m³ [SolarThermalWorld]_). Für 1.000 m³ ergibt das 176 €/m³.
* **BEW-Förderung:** Ist die Förderung gewählt, sinken die Investitionen um 40 %.

CO₂ und Primärenergie
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Energieträger
     - CO₂ [t/MWh]
     - Primärenergiefaktor
   * - Erdgas
     - 0,201
     - 1,1
   * - Holz (Pellets, Holzgas)
     - 0,036
     - 0,2
   * - Strom für Wärmepumpen
     - 0,4
     - 1,8
   * - Strom für Power-to-Heat
     - 0,4
     - 2,4
   * - Solarthermie
     - 0
     - 0

**Stromgutschrift beim BHKW.** Der erzeugte Strom ersetzt Netzstrom und wird für CO₂ und
Primärenergie gleich behandelt:

* CO₂ = Brennstoff × CO₂-Faktor − Strom × 0,4 t/MWh,
* Primärenergie = Brennstoff × Primärenergiefaktor − Strom × 1,8.

Beide Werte können negativ werden, etwa bei einem Holzgas-BHKW. Die Faktoren stehen in
``districtheatingsim/constants.py``. Das normative Stromgutschriftverfahren (AGFW FW 309-1,
GEG Anlage 4) rechnet mit dem Verdrängungsstrommix, also mit dem Primärenergiefaktor 2,8 und
860 g CO₂/kWh, und begrenzt den Primärenergiefaktor des Netzes nach unten auf 0 [GEG]_. Dafür sind
beide Konstanten gemeinsam umzustellen.

Optimierung
~~~~~~~~~~~

Die Optimierung sucht Anlagengrößen (Leistung, Kollektorfläche, Speichervolumen) innerhalb der
eingestellten Grenzen. Das Verfahren ist SLSQP mit fünf Starts von zufälligen Startwerten.

* **Zielfunktion:** gewichtete Summe aus WGK, spezifischen CO₂-Emissionen und
  Primärenergiefaktor. Jede Kennzahl wird auf ihren Wert für die eingestellte Konfiguration
  bezogen; die Gewichte sind daher relative Wichtigkeiten. Bei gleichen Gewichten zählen 10 %
  weniger CO₂ so viel wie 10 % niedrigere Kosten. Mit dem Standard (nur Kosten) minimiert die
  Optimierung die WGK.
* **Deckung:** Ungedeckter Bedarf wird stark bestraft. Ohne diese Strafe könnte die Optimierung
  die Zielgrößen senken, indem sie Anlagen verkleinert und den Bedarf ungedeckt lässt.
* **Solarspeicher:** Mindestens 50 l Speicher je m² Kollektorfläche. Ohne diese Nebenbedingung
  endete der Speicher an seiner unteren Grenze, etwa bei 773 m² Kollektor mit 16 m³.


Plausibilitätsampel
-------------------

Netz- und Erzeugerergebnisse zeigen eine Ampel neben den Zahlen; die Hinweise mit Grenzwert und
Quelle erscheinen beim Zeigen auf eine Zeile.

.. list-table::
   :header-rows: 1
   :widths: 26 18 18 18 20

   * - Kennzahl
     - plausibel
     - prüfen
     - unplausibel
     - Quelle
   * - Wärmeverluste des Netzes (Anteil an der Erzeugung, Jahreszeitreihe)
     - ≤ 10 %
     - ≤ 20 %
     - > 20 %
     - QM Holzheizwerke [BFE]_
   * - Wärmebelegungsdichte (Jahresbedarf je Meter Trasse)
     - ≥ 1,8 MWh/(m·a)
     - ≥ 0,5 MWh/(m·a)
     - < 0,5 MWh/(m·a)
     - QM Holzheizwerke [BFE]_; frühere KfW-Förderung
   * - Spezifischer Druckverlust (höchster Wert einer Leitung)
     - ≤ Grenze der Auslegung
     - darüber
     -
     - Auslegungsgrenze
   * - Speicher je m² Kollektor (Solarthermie)
     - ≥ 50 l/m²
     - ≥ 25 l/m²
     - < 25 l/m²
     - üblicher Tagesspeicher 50–100 l/m²
   * - Volllaststunden je Erzeuger
     - nur Information
     -
     -
     - kein belastbarer Grenzwert

Die Volllaststunden sind die Jahreswärmemenge geteilt durch die höchste Stundenleistung im Jahr.
Grundlasterzeuger (BHKW, Biomasse, Wärmepumpe) mit nur wenigen tausend Stunden sind meist zu
groß ausgelegt.


Quellen
-------

.. [Energiforsk2021] Energiforsk: *Dimensionering av servisledningar i distributionssystem*,
   Rapport 2021:813.
   https://energiforsk.se/media/30563/dimensionering-av-servisledningar-i-distributionssystem-energiforskrapport-2021-813.pdf
.. [BFE] Bundesamt für Energie (BFE): Auswertung von Wärmenetzen nach den Anforderungen von
   QM Holzheizwerke. https://pubdb.bfe.admin.ch/de/publication/download/7306
.. [GEG] Gebäudeenergiegesetz, Anlage 4 (Primärenergiefaktoren, Verdrängungsstrommix für KWK).
   https://lexmea.de/de/gesetz/geg/anlage-4
.. [store4grid] store4grid: Konzept Langzeit-Wärmespeicher (2015).
   https://dev.energieforschung.at/wp-content/uploads/sites/11/2020/12/store4grid-Konzept-Langzeit-Waermespeicher-20150813.pdf
.. [SolarThermalWorld] IEA SHC / Solar Thermal World: Kosten dänischer Erdbeckenspeicher.
   https://52.iea-shc.org/article?NewsID=265
