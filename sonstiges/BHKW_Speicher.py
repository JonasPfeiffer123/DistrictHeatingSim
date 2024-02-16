import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons

# Parameter
bhkw_kapazitaet = 300  # kW
bhkw_zustand = 1  # Anfangszustand
speicher_kapazitaet = 1000  # kWh
speicher_stand = 0  # Anfangsstand des Speichers in kWh
gaspreis = 50  # EUR/MWh

# Pfad zu den CSV-Daten
strom_data = "sonstiges/Strompreise_day_ahead_2023.csv"
lastgang_data = "project_data/Görlitz/Lastgang/Lastgang_85C_70C_60C.csv"

def einlesen_strompreise(dateipfad):
    df = pd.read_csv(dateipfad, header=[0, 1], index_col=0)
    new_columns = [f'{i[0]} {i[1]}' if i[1] else f'{i[0]}' for i in df.columns]
    df.columns = new_columns
    return df["Day Ahead Auktion Preis (EUR/MWh, EUR/tCO2)"].values

def einlesen_lastgang(dateipfad):
    return pd.read_csv(dateipfad, sep=';', parse_dates=['Zeit'], index_col='Zeit')

def berechne_daten(df, bhkw_kapazitaet, bhkw_zustand, speicher_kapazitaet, speicher_stand, gaspreis, strompreis, nutzungsgrad_strom=0.33, nutzungsgrad_waerme=0.57):
    df["Gaspreis_EUR_MWh"] = gaspreis
    df["Strompreis_EUR_MWh"] = strompreis
    df['BHKW_Erzeugung_Waerme_kW'] = 0
    df['Speicherfüllstand_kWh'] = 0
    df['BHKW_Brennstoffbedarf_kW'] = 0
    df['BHKW_Erzeugung_Strom_kW'] = 0
    df['BHKW_Zustand'] = 0
    df['Kosten_Gas_EUR'] = 0
    df['Einnahmen_Strom_EUR'] = 0
    df['Verbleibende_Kosten_EUR'] = 0
    df['Speicherleistung_kW'] = 0
    df['Wärmegestehungskosten_EUR_MWh'] = 0

    for zeitpunkt, row in df.iterrows():
        heizlast = row['Heizlast_Netz_kW']
        speicher_leistung = 0
        aktueller_strompreis = strompreis[df.index.get_loc(zeitpunkt)]  # Zugriff auf den aktuellen Strompreis

        # Entscheidungslogik für BHKW-Betrieb
        if speicher_stand/speicher_kapazitaet <= 0.8 and bhkw_zustand == 1:
            bhkw_erzeugung = bhkw_kapazitaet
            speicher_leistung = max(bhkw_erzeugung - heizlast, 0)
        elif speicher_stand/speicher_kapazitaet > 0.8 and bhkw_zustand == 1:
            bhkw_erzeugung = 0
            bhkw_zustand = 0
        elif speicher_stand/speicher_kapazitaet > 0.2 and bhkw_zustand == 0:
            bhkw_erzeugung = 0
            speicher_leistung = min(-heizlast, 0)  # Heizlast wird aus dem Speicher gedeckt
        elif speicher_stand/speicher_kapazitaet <= 0.2 and bhkw_zustand == 0:
            bhkw_erzeugung = bhkw_kapazitaet
            bhkw_zustand = 1
            speicher_leistung = max(bhkw_erzeugung - heizlast, 0)

        # Berechnung der Energieflüsse
        speicher_stand = min(max(speicher_stand + speicher_leistung, 0), speicher_kapazitaet)

        # Wirtschaftliche Berechnungen
        gasbedarf = bhkw_erzeugung / nutzungsgrad_waerme # kW ... 1h -> kWh
        stromerzeugung = gasbedarf * nutzungsgrad_strom # kW ... 1h -> kWh
        kosten_gas = gasbedarf/1000 * gaspreis # €
        einnahmen_strom = stromerzeugung/1000 * aktueller_strompreis
        verbleibende_kosten = kosten_gas - einnahmen_strom
        wärmegestehungskosten = verbleibende_kosten / (bhkw_erzeugung/1000) if bhkw_erzeugung > 0 else 0

        # Aktualisiere DataFrame
        df.at[zeitpunkt, 'BHKW_Erzeugung_Waerme_kW'] = bhkw_erzeugung
        df.at[zeitpunkt, 'BHKW_Brennstoffbedarf_kW'] = gasbedarf
        df.at[zeitpunkt, 'BHKW_Erzeugung_Strom_kW'] = stromerzeugung
        df.at[zeitpunkt, 'BHKW_Zustand'] = bhkw_zustand
        df.at[zeitpunkt, 'Speicherleistung_kW'] = speicher_leistung
        df.at[zeitpunkt, 'Speicherfüllstand_kWh'] = speicher_stand
        df.at[zeitpunkt, 'Kosten_Gas_EUR'] = kosten_gas
        df.at[zeitpunkt, 'Einnahmen_Strom_EUR'] = einnahmen_strom
        df.at[zeitpunkt, 'Verbleibende_Kosten_EUR'] = verbleibende_kosten
        df.at[zeitpunkt, 'Wärmegestehungskosten_EUR_MWh'] = wärmegestehungskosten

    return df


def plot_daten(df, daten_zum_plotten):
    fig, ax = plt.subplots(figsize=(12, 7))
    plt.subplots_adjust(left=0.2)
    lines = []

    # Zeichne jede Datenreihe und speichere die Linienobjekte
    for label, spalte in daten_zum_plotten.items():
        line, = ax.plot(df.index, df[spalte], label=label)
        lines.append(line)

    # Legende und Achsenbeschriftungen
    plt.title('Energieflüsse und Speicherstatus')
    plt.xlabel('Zeit')
    plt.ylabel('Werte')
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    plt.grid(True)
    plt.xticks(rotation=45)

    # Checkbutton Widget hinzufügen
    rax = plt.axes([0.005, 0.4, 0.15, 0.15], facecolor='lightgoldenrodyellow')
    labels = [line.get_label() for line in lines]
    visibility = [line.get_visible() for line in lines]
    check = CheckButtons(rax, labels, visibility)

    # Funktion zum Aktualisieren der Sichtbarkeit
    def func(label):
        index = labels.index(label)
        lines[index].set_visible(not lines[index].get_visible())
        plt.draw()

    # Checkbuttons mit der Update-Funktion verbinden
    check.on_clicked(func)

    plt.show()

def haupt():
    strompreis = einlesen_strompreise(strom_data)
    df_lastgang = einlesen_lastgang(lastgang_data)
    df_berechnet = berechne_daten(df_lastgang, bhkw_kapazitaet, bhkw_zustand, speicher_kapazitaet, speicher_stand, gaspreis, strompreis)
    
    daten_zum_plotten = {
        'Heizlast (Netz) in kW': 'Heizlast_Netz_kW',
        'BHKW Erzeugung in kW': 'BHKW_Erzeugung_Waerme_kW',
        'Stromerzeugung BHKW in kW': 'BHKW_Erzeugung_Strom_kW',
        'Brennstoffbedarf BHKW in kW': 'BHKW_Brennstoffbedarf_kW',
        'Speicherfüllstand in kWh': 'Speicherfüllstand_kWh',
        'Speicherleistung in kW': 'Speicherleistung_kW',
        'Gaspreis in €/MWh': "Gaspreis_EUR_MWh",
        'Strompreis in €/MWh': "Strompreis_EUR_MWh",
        'Kosten Gas in €': 'Kosten_Gas_EUR',
        'Einnahmen Strom in €': 'Einnahmen_Strom_EUR',
        'Verbleibende Kosten in €': 'Verbleibende_Kosten_EUR',
        'Wärmegestehungskosten in €/MWh': 'Wärmegestehungskosten_EUR_MWh'
    }
    
    plot_daten(df_berechnet, daten_zum_plotten)

if __name__ == '__main__':
    haupt()