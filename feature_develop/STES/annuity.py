"""
Filename: annuity.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-10
Description: Contains the annuity calculation function for technical installations according to VDI 2067.

"""

# Wirtschaftlichkeitsberechnung für technische Anlagen nach VDI 2067
def annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand=0, q=1.05, r=1.03, T=20, Energiebedarf=0, Energiekosten=0, E1=0, stundensatz=45):
    """
    Calculate the annuity for a given set of parameters over a specified period.

    Args:
        A0 (float): Initial investment cost.
        TN (int): Useful life of the investment.
        f_Inst (float): Installation factor.
        f_W_Insp (float): Maintenance and inspection factor.
        Bedienaufwand (float, optional): Operating effort in hours. Defaults to 0.
        q (float, optional): Interest rate factor. Defaults to 1.05.
        r (float, optional): Inflation rate factor. Defaults to 1.03.
        T (int, optional): Consideration period in years. Defaults to 20.
        Energiebedarf (float, optional): Energy demand in kWh. Defaults to 0.
        Energiekosten (float, optional): Energy costs in €/kWh. Defaults to 0.
        E1 (float, optional): Annual revenue. Defaults to 0.
        stundensatz (float, optional): Hourly rate for labor in €/h. Defaults to 45.

    Returns:
        float: Calculated annuity value.
    """

    n = max(T // TN, 0)

    a = (q - 1) / (1 - (q ** (-T)))  # Annuitätsfaktor
    b = (1 - (r / q) ** T) / (q - r)  # preisdynamischer Barwertfaktor
    b_v = b_B = b_IN = b_s = b_E = b

    # kapitalgebundene Kosten
    AN = A0 + sum(A0 * (r ** (i * TN)) / (q ** (i * TN)) for i in range(1, n + 1)) # Barwert der Investitionskosten

    R_W = A0 * (r**(n*TN)) * (((n+1)*TN-T)/TN) * 1/(q**T) # Restwert
    A_N_K = (AN - R_W) * a # Annuität der kapitalgebundenen Kosten

    # bedarfsgebundene Kosten
    A_V1 = Energiebedarf * Energiekosten # Energiekosten erste Periode
    A_N_V = A_V1 * a * b_v # Annuität der bedarfsgebundenen Kosten

    # betriebsgebundene Kosten
    A_B1 = Bedienaufwand * stundensatz # Betriebskosten erste Periode
    A_IN = A0 * (f_Inst + f_W_Insp)/100 # Instandhaltungskosten
    A_N_B = A_B1 * a * b_B + A_IN * a * b_IN # Annuität der betriebsgebundenen Kosten

    # sonstige Kosten
    A_S1 = 0 # sonstige Kosten erste Periode
    A_N_S = A_S1 * a * b_s # Annuität der sonstigen Kosten

    A_N = - (A_N_K + A_N_V + A_N_B + A_N_S)  # Annuität

    # Erlöse
    A_NE = E1 * a * b_E # Annuität der Erlöse

    A_N += A_NE # Annuität mit Erlösen

    return -A_N