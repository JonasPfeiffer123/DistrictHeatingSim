# Berechnung der Wärmegestehungskosten nach der Annuitätsmethode gemäß VDI 2067

def annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand=0, q=1.05, r=1.03, T=20, Energiebedarf=0, Energiekosten=0, E1=0):
    if T > TN:
        n = T // TN
    else:
        n = 0

    a = (q - 1) / (1 - (q ** (-T)))  # Annuitätsfaktor
    b = (1 - (r / q) ** T) / (q - r)  # preisdynamischer Barwertfaktor
    b_v = b_B = b_IN = b_s = b_E = b

    # kapitalgebundene Kosten
    AN = A0
    AN_L = [A0]
    for i in range(1, n+1):
        Ai = A0*((r**(n*TN))/(q**(n*TN)))
        AN += Ai
        AN_L.append(Ai)

    R_W = A0 * (r**(n*TN)) * (((n+1)*TN-T)/TN) * 1/(q**T)
    A_N_K = (AN - R_W) * a

    # bedarfsgebundene Kosten
    A_V1 = Energiebedarf * Energiekosten
    A_N_V = A_V1 * a * b_v

    # betriebsgebundene Kosten#
    stundensatz = 100  # €
    A_B1 = Bedienaufwand * stundensatz
    A_IN = A0 * (f_Inst + f_W_Insp)/100
    A_N_B = A_B1 * a * b_B + A_IN * a * b_IN

    # sonstige Kosten
    A_S1 = 0
    A_N_S = A_S1 * a * b_s

    A_N = - (A_N_K + A_N_V + A_N_B + A_N_S)  # Annuität

    # Erlöse
    A_NE = E1*a*b_E

    A_N += A_NE

    return -A_N

# print(annuität(30000, 20, 1, 2, 0, 1.05, 1.03, 20, 20000, 0.1))

def WGK_WP(Wärmeleistung, Wärmemenge, Strombedarf, Wärmequelle, spez_Investitionskosten_WQ, Strompreis, q, r, T, BEW="Nein"):
    if Wärmemenge == 0:
        return 0
    # Kosten Wärmepumpe: Viessmann Vitocal 350 HT-Pro: 140.000 €, 350 kW Nennleistung; 120 kW bei 10/85
    # Annahme Kosten Wärmepumpe: 1000 €/kW; Vereinfachung
    spezifische_Investitionskosten_WP = 1000  # €/kW
    Nutzungsdauer_WP = 20
    f_Inst_WP, f_W_Insp_WP, Bedienaufwand_WP = 1, 1.5, 0
    f_Inst_WQ, f_W_Insp_WQ, Bedienaufwand_WQ = 0.5, 0.5, 0

    Investitionskosten_WP = spezifische_Investitionskosten_WP * round(Wärmeleistung, 0)

    E1_WP = annuität(Investitionskosten_WP, Nutzungsdauer_WP, f_Inst_WP, f_W_Insp_WP, Bedienaufwand_WP, q, r, T,
                           Strombedarf, Strompreis)
    WGK_WP_a = E1_WP/Wärmemenge

    spezifische_Investitionskosten_WQ_dict = {"Abwärme": 500, "Abwasserwärme": 1000,
                                              "Geothermie": spez_Investitionskosten_WQ}
    Nutzungsdauer_WQ_dict = {"Abwärme": 20, "Abwasserwärme": 20, "Geothermie": 30}

    Investitionskosten_WQ = spezifische_Investitionskosten_WQ_dict[Wärmequelle] * Wärmeleistung

    E1_WQ = annuität(Investitionskosten_WQ, Nutzungsdauer_WQ_dict[Wärmequelle], f_Inst_WQ, f_W_Insp_WQ,
                           Bedienaufwand_WQ, q, r, T)
    WGK_WQ_a = E1_WQ / Wärmemenge

    WGK_Gesamt_a = WGK_WP_a + WGK_WQ_a

    return WGK_Gesamt_a

def WGK_Gaskessel(P_max, Wärmemenge, Brennstoffbedarf, Brennstoffkosten, q, r, T, BEW="Nein"):
    if Wärmemenge == 0:
        return 0
    # Kosten 1000 kW Gaskessel ~ 30000 €
    spez_Investitionskosten = 30  # €/kW
    Investitionskosten = spez_Investitionskosten * P_max
    Nutzungsdauer = 20
    f_Inst, f_W_Insp, Bedienaufwand = 1, 2, 0

    A_N = annuität(Investitionskosten, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T,
                        Brennstoffbedarf, Brennstoffkosten)
    WGK_a = A_N / Wärmemenge

    return WGK_a

def WGK_Biomassekessel(Leistung_BMK, Wärmemenge, Brennstoffbedarf, Brennstoffkosten, q, r, T, BEW="Nein"):
    if Wärmemenge == 0:
        return 0
    # Kosten 200 kW Holzpelletkessel ~ 40000 €
    Nutzungsdauer = 15
    spez_Investitionskosten = 200  # €/kW
    spez_Investitionskosten_Holzlager = 400  # €/t
    Größe_Holzlager = 40  # t
    Investitionskosten = spez_Investitionskosten * Leistung_BMK + spez_Investitionskosten_Holzlager * Größe_Holzlager
    f_Inst, f_W_Insp, Bedienaufwand = 3, 3, 0

    A_N = annuität(Investitionskosten, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T, Brennstoffbedarf,
                        Brennstoffkosten)
    WGK_a = A_N / Wärmemenge

    return WGK_a

def WGK_BHKW(Wärmeleistung, Wärmemenge, Strommenge, Art, Brennstoffbedarf, Brennstoffkosten, Strompreis, q, r, T, BEW="Nein"):
    if Wärmemenge == 0:
        return 0
    # Holzvergaser-BHKW: 130 kW: 240.000 -> 1850 €/kW
    # (Erd-)Gas-BHKW: 100 kW: 150.000 € -> 1500 €/kW
    if Art == "BHKW":
        spez_Investitionskosten = 1500  # €/kW
    elif Art == "Holzgas-BHKW":
        spez_Investitionskosten = 1850  # €/kW

    Investitionskosten = spez_Investitionskosten * Wärmeleistung
    Nutzungsdauer = 15
    f_Inst, f_W_Insp, Bedienaufwand = 6, 2, 0

    Stromeinnahmen = Strommenge * Strompreis

    A_N = annuität(Investitionskosten, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T,
                        Brennstoffbedarf, Brennstoffkosten, Stromeinnahmen)
    WGK_a = A_N / Wärmemenge

    return WGK_a

def WGK_STA(Bruttofläche_STA, VS, typ, Wärmemenge, q=1.05, r=1.03, T=20, BEW="Nein"):
    if Wärmemenge == 0:
        return 0

    kosten_pro_typ = {
        # Viessmann Flachkollektor Vitosol 200-FM, 2,56 m²: 697,9 € (brutto); 586,5 € (netto) -> 229 €/m²
        # + 200 €/m² Installation/Zubehör
        "Flachkollektor": 430,
        # Ritter Vakuumröhrenkollektor CPC XL1921 (4,99m²): 2299 € (brutto); 1932 € (Netto) -> 387 €/m²
        # + 200 €/m² Installation/Zubehör
        "Vakuumröhrenkollektor": 590
    }

    Kosten_STA_spez = kosten_pro_typ[typ]  # €/m^2
    Kosten_Speicher_spez = 0  # 750  # €/m^3
    Nutzungsdauer = 20
    f_Inst, f_W_Insp, Bedienaufwand = 0.5, 1, 0

    Investitionskosten_Speicher = VS * Kosten_Speicher_spez
    Investitionskosten_STA = Bruttofläche_STA * Kosten_STA_spez
    Investitionskosten_Gesamt = Investitionskosten_Speicher + Investitionskosten_STA

    A_N = annuität(Investitionskosten_Gesamt, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T)
    WGK = A_N / Wärmemenge

    Anteil_Förderung_BEW = 0.4
    Eigenanteil = 1 - Anteil_Förderung_BEW
    Investitionskosten_Gesamt_BEW = Investitionskosten_Gesamt * Eigenanteil
    Annuität_BEW = annuität(Investitionskosten_Gesamt_BEW, Nutzungsdauer, f_Inst, f_W_Insp, Bedienaufwand, q, r, T)
    WGK_BEW = Annuität_BEW / Wärmemenge

    WGK_BEW_BKF = WGK_BEW - 10  # €/MWh 10 Jahre

    if BEW == "Nein":
        return WGK
    elif BEW == "Ja":
        return WGK_BEW_BKF
