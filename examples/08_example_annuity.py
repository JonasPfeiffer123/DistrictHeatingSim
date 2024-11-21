"""
Filename: 08_example_annuity.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-11-19
Description: Example for the calculation of the annuity of a heat generator

"""

from districtheatingsim.heat_generators import annuity

# Test Annuitätsberechnung
def test_annuität():
    # Investition in €
    A0 = 10000

    # Technische Nutzungsdauer in Jahren
    TN = 20

    # Kostenfaktor Installationskosten als Anteil der Investitionskosten
    f_Inst = 0.03

    # Kostenfaktor Wartungs- und Instandhaltungskosten als Anteil der Investitionskosten
    f_W_Insp = 0.02

    # Bedienaufwand in Stunden (Stundensatz aktuell fix in der Funktion mit 45 €/h hinterlegt)
    # muss unbedingt noch weg von der fixen Definition
    Bedienaufwand = 10

    # Kapitalzinsfaktor 
    q = 1.05 # 5 %

    # Preissteigerungsfaktor
    r = 1.03 # 3 %

    # Betrachtungszeitraum in Jahren
    T = 20

    # Energiebedarf / Brennstoffbedarf in z.B. kWh
    Energiebedarf = 15000

    # Energiekosten in z.B. €/kWh --> Einheit Energie muss mit der des Energiebedarfs übereinstimmen
    Energiekosten = 0.15

    # Erlöse, könnte z.B. Stromverkauf aus BHKW sein oder auch Wärmeverkauf, kann auf 0 gesetzt werden, dann nur Aussage über Höhe der Kosten
    E1 = 0

    A_N = annuity.annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand, q, r, T, Energiebedarf, Energiekosten, E1)

    print(f"Annuität: {A_N:.2f} €")

if __name__ == "__main__":
    test_annuität()