"""
Filename: results_pdf.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-05
Description: Script for generating the results PDF of the calculation results.
"""

import numpy as np

from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors

from PyQt5.QtCore import QBuffer
from PyQt5.QtGui import QPainter, QPixmap

from districtheatingsim.gui.dialogs import PDFSelectionDialog

def get_custom_table_style():
    """
    Returns a custom TableStyle for styling tables in the PDF.
    """
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (0, 0), (-1, -1), 'LTR'),
        ('FONTSIZE', (0, 0), (-1, -1), 8)
    ])

def add_figure_to_story(figure, story, max_width=6.5 * inch):
    """
    Adds a matplotlib figure to the PDF story.
    """
    img_buffer = BytesIO()
    figure.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300)
    img_buffer.seek(0)

    img = Image(img_buffer)
    aspect_ratio = img.drawWidth / img.drawHeight

    if img.drawWidth > max_width:
        img.drawWidth = max_width
        img.drawHeight = img.drawWidth / aspect_ratio

    story.append(img)
    story.append(Spacer(1, 12))

def add_net_structure_section(story, calcTab):
    """
    Adds the network structure section to the PDF story.
    """
    try:
        story.append(Paragraph("Netzstruktur", getSampleStyleSheet()['Heading2']))
        for figure in [calcTab.figure5]:
            add_figure_to_story(figure, story)

    except Exception as e:
        error_message = f"Fehlendes Diagramm der Netzstruktur: {str(e)}"
        story.append(Paragraph(error_message, getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 12))
        print(error_message)

def add_economic_conditions_section(story, mixDesignTab):
    """
    Adds the economic conditions section to the PDF story.
    """
    try:
        story.append(Paragraph("Wirtschaftliche Randbedingungen", getSampleStyleSheet()['Heading2']))

        economic_conditions = mixDesignTab.economicParametersDialog.getValues()
        economic_conditions_data = [("Parameter", "Wert")]
        economic_conditions_data.extend([(key, value) for key, value in economic_conditions.items()])

        economic_conditions_table = Table(economic_conditions_data)
        economic_conditions_table.setStyle(get_custom_table_style())
        story.append(KeepTogether(economic_conditions_table))
        story.append(Spacer(1, 12))

    except Exception as e:
        error_message = f"Fehlende Daten im Wirtschaftsparameterabschnitt: {str(e)}"
        story.append(Paragraph(error_message, getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 12))
        print(error_message)

def add_technologies_section(story, mixDesignTab):
    """
    Adds the energy technologies section to the PDF story.
    """
    try:
        if not hasattr(mixDesignTab, 'techTab') or not mixDesignTab.techTab.tech_objects:
            story.append(Paragraph("Fehlende Daten: Erzeugertechnologien", getSampleStyleSheet()['Normal']))
            story.append(Spacer(1, 12))
            return

        story.append(Paragraph("Erzeugertechnologien", getSampleStyleSheet()['Heading2']))

        for tech in mixDesignTab.techTab.tech_objects:
            story.append(Paragraph(mixDesignTab.techTab.formatTechForDisplay(tech), getSampleStyleSheet()['Normal']))
            story.append(Spacer(1, 12))

    except Exception as e:
        error_message = f"Fehlende Daten im Erzeugertechnologieabschnitt: {str(e)}"
        story.append(Paragraph(error_message, getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 12))
        print(error_message)

def export_scene_to_image(scene):
    """
    Converts the QGraphicsScene to an image (QPixmap) and returns it as a BytesIO object.
    """
    # Erzeuge ein QPixmap mit der gleichen Größe wie die Szene
    scene_rect = scene.sceneRect()
    image = QPixmap(int(scene_rect.width()), int(scene_rect.height()))

    # Erzeuge ein QPainter und male die Szene auf das Bild
    painter = QPainter(image)
    scene.render(painter)
    painter.end()

    # Konvertiere das QPixmap in ein QImage
    qimage = image.toImage()

    # Speichere das Bild in einen QBuffer als PNG
    buffer = QBuffer()
    buffer.open(QBuffer.ReadWrite)
    qimage.save(buffer, "PNG")

    # Konvertiere den QBuffer in BytesIO, damit es mit ReportLab funktioniert
    buffer.seek(0)
    byte_array = buffer.data()
    
    img_buffer = BytesIO(byte_array)
    img_buffer.seek(0)

    return img_buffer

def add_schematic_scene_section(story, scene):
    """
    Adds the schematic scene as an image to the PDF story.
    """
    try:
        # Konvertiere die Szene in ein Bild und erhalte einen BytesIO-Stream
        img_buffer = export_scene_to_image(scene)
        
        # Füge das Bild zur PDF-Story hinzu
        img = Image(img_buffer)
        aspect_ratio = img.drawWidth / img.drawHeight

        max_width = 6.5 * inch
        if img.drawWidth > max_width:
            img.drawWidth = max_width
            img.drawHeight = img.drawWidth / aspect_ratio

        story.append(Paragraph("Schematische Darstellung", getSampleStyleSheet()['Heading2']))
        story.append(img)
        story.append(Spacer(1, 12))

    except Exception as e:
        error_message = f"Fehler beim Export der Szene: {str(e)}"
        story.append(Paragraph(error_message, getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 12))
        print(error_message)


def add_costs_net_infrastructure_section(story, mixDesignTab):
    """
    Adds the network infrastructure section to the PDF story.
    """
    try:
        # Überprüfen, ob die notwendigen Daten vorhanden sind
        if not hasattr(mixDesignTab, 'costTab') or not hasattr(mixDesignTab.costTab, 'summe_investitionskosten'):
            story.append(Paragraph("Fehlende Daten: Summe Infrastruktur", getSampleStyleSheet()['Normal']))
            story.append(Spacer(1, 12))
            return

        story.append(Paragraph("Netzinfrastruktur", getSampleStyleSheet()['Heading2']))

        values = mixDesignTab.netInfrastructureDialog.getValues()
        infraObjects = mixDesignTab.netInfrastructureDialog.getCurrentInfraObjects()
        columns = ['Beschreibung', 'Kosten', 'T_N', 'f_Inst', 'f_W_Insp', 'Bedienaufwand', 'Gesamtannuität']

        infra_data = [columns]

        for obj in infraObjects:
            row_data = [obj.capitalize()]
            annuität = 0
            for col in columns[1:]:
                key = f"{obj}_{col.lower()}"
                value = values.get(key, "")
                if value != "":
                    row_data.append(str(value))

                if col == 'Kosten':
                    A0 = float(values.get(f"{obj}_kosten", 0))
                    TN = int(values.get(f"{obj}_t_n", 0))
                    f_Inst = float(values.get(f"{obj}_f_inst", 0))
                    f_W_Insp = float(values.get(f"{obj}_f_w_insp", 0))
                    Bedienaufwand = float(values.get(f"{obj}_bedienaufwand", 0))
                    annuität = mixDesignTab.costTab.calc_annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand)

            row_data.append("{:.0f}".format(annuität))
            infra_data.append(row_data)

        summen_row = ["Summe Infrastruktur", "{:.0f}".format(mixDesignTab.costTab.summe_investitionskosten), "", "", "", "", "{:.0f}".format(mixDesignTab.costTab.summe_annuität)]
        infra_data.append(summen_row)

        infra_table = Table(infra_data)
        infra_table.setStyle(get_custom_table_style())
        story.append(KeepTogether(infra_table))
        story.append(Spacer(1, 12))

    except Exception as e:
        error_message = f"Fehlende Daten im Netzinfrastrukturabschnitt: {str(e)}"
        story.append(Paragraph(error_message, getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 12))
        print(error_message)


def add_costs_heat_generators_section(story, mixDesignTab):
    """
    Adds the costs section to the PDF story.
    """
    try:
        story.append(Paragraph("Kosten Erzeuger", getSampleStyleSheet()['Heading2']))
        tech_data = mixDesignTab.costTab.techDataTable
        tech_columns = [tech_data.horizontalHeaderItem(i).text() for i in range(tech_data.columnCount())]
        tech_rows = []

        for row in range(tech_data.rowCount()):
            tech_row = []
            for col in range(tech_data.columnCount()):
                item = tech_data.item(row, col)
                tech_row.append(Paragraph(item.text() if item else "", getSampleStyleSheet()['Normal']))
            tech_rows.append(tech_row)

        tech_data_table = Table([tech_columns] + tech_rows, colWidths=[1.2 * inch] * len(tech_columns))
        tech_data_table.setStyle(get_custom_table_style())
        story.append(KeepTogether(tech_data_table))
        story.append(Spacer(1, 12))

    except Exception as e:
        error_message = f"Fehlende Daten im Kostenabschnitt: {str(e)}"
        story.append(Paragraph(error_message, getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 12))
        print(error_message)

def add_costs_total_section(story, mixDesignTab):
    """
    Adds the total costs section to the PDF story.
    Shows the plots from MixDesignTab.costTab if available.
    """
    try:
        story.append(Paragraph("Gesamtkosten", getSampleStyleSheet()['Heading2']))

        # Add Bar Chart as a separate plot
        add_figure_to_story(mixDesignTab.costTab.bar_chart_figure, story)

        # Add Pie Chart as a separate plot
        add_figure_to_story(mixDesignTab.costTab.pie_chart_figure, story)

    except Exception as e:
        error_message = f"Fehlende Daten im Gesamtkostenabschnitt: {str(e)}"
        story.append(Paragraph(error_message, getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 12))
        print(error_message)

def add_results_section(story, mixDesignTab):
    """
    Adds the results section to the PDF story.
    """
    try:
        story.append(Paragraph("Berechnungsergebnisse", getSampleStyleSheet()['Heading2']))

        for figure in [mixDesignTab.resultTab.figure1, mixDesignTab.resultTab.pieChartFigure]:
            add_figure_to_story(figure, story)

        results_data = [("Technologie", "Wärmemenge (MWh)", "Kosten (€/MWh)", "Anteil (%)", "spez. CO2-Emissionen (tCO2/MWh_th)", "Primärenergiefaktor")]
        results_data.extend([
            (tech, f"{wärmemenge:.2f}", f"{wgk:.2f}", f"{anteil*100:.2f}", f"{spec_emission:.4f}", f"{primary_energy/wärmemenge:.4f}")
            for tech, wärmemenge, wgk, anteil, spec_emission, primary_energy in zip(mixDesignTab.results['techs'], mixDesignTab.results['Wärmemengen'], mixDesignTab.results['WGK'], 
                                                    mixDesignTab.results['Anteile'], mixDesignTab.results['specific_emissions_L'], mixDesignTab.results['primärenergie_L'])
        ])

        results_table = Table(results_data, colWidths=[1.2 * inch] * len(results_data[0]))
        results_table.setStyle(get_custom_table_style())
        story.append(KeepTogether(results_table))
        story.append(Spacer(1, 12))

    except Exception as e:
        error_message = f"Fehlende Daten im Ergebnisabschnitt: {str(e)}"
        story.append(Paragraph(error_message, getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 12))
        print(error_message)

def add_combined_results_section(story, mixDesignTab):
    """
    Adds the combined results section to the PDF story.
    
    Args:
        story (list): The list of PDF elements to be added.
        mixDesignTab: The object containing the resultTab with data for combined results.
    """
    try:
        # Hinzufügen des Abschnittstitels
        story.append(Paragraph("Kombinierte Ergebnisse", getSampleStyleSheet()['Heading2']))
        
        # Holen der Resultate aus dem resultTab
        results = mixDesignTab.resultTab.results
        waerme_ges_kW = np.sum(results["waerme_ges_kW"])
        strom_wp_kW = np.sum(results["strom_wp_kW"])
        WGK_Infra = mixDesignTab.costTab.summe_annuität / results['Jahreswärmebedarf']
        wgk_heat_pump_electricity = ((strom_wp_kW / 1000) * mixDesignTab.strompreis) / ((strom_wp_kW + waerme_ges_kW) / 1000)
        WGK_Gesamt = results['WGK_Gesamt'] + WGK_Infra + wgk_heat_pump_electricity
        
        # Definieren der Daten für die Tabelle
        combined_results_data = [("Parameter", "Wert", "Einheit")]
        combined_results_data.extend([
            ("Jahreswärmebedarf", round(results['Jahreswärmebedarf'], 1), "MWh"),
            ("Stromerzeugung", round(results['Strommenge'], 2), "MWh"),
            ("Strombedarf", round(results['Strombedarf'], 2), "MWh"),
            ("Wärmegestehungskosten Erzeugeranlagen", round(results['WGK_Gesamt'], 2), "€/MWh"),
            ("Wärmegestehungskosten Netzinfrastruktur", round(WGK_Infra, 2), "€/MWh"),
            ("Wärmegestehungskosten dezentrale Wärmepumpen", round(wgk_heat_pump_electricity, 2), "€/MWh"),
            ("Wärmegestehungskosten Gesamt", round(WGK_Gesamt, 2), "€/MWh"),
            ("spez. CO2-Emissionen Wärme", round(results["specific_emissions_Gesamt"], 4), "t_CO2/MWh_th"),
            ("CO2-Emissionen Wärme", round(results["specific_emissions_Gesamt"] * results['Jahreswärmebedarf'], 2), "t_CO2"),
            ("Primärenergiefaktor", round(results["primärenergiefaktor_Gesamt"], 4), "-")
        ])
        
        # Erstellen der Tabelle für die kombinierten Ergebnisse
        combined_results_table = Table(combined_results_data, colWidths=[2 * inch, 1.5 * inch, 1.2 * inch])
        combined_results_table.setStyle(get_custom_table_style())
        
        # Hinzufügen der Tabelle zur PDF-Geschichte
        story.append(KeepTogether(combined_results_table))
        story.append(Spacer(1, 12))
    
    except Exception as e:
        error_message = f"Fehlende Daten im Abschnitt Kombinierte Ergebnisse: {str(e)}"
        story.append(Paragraph(error_message, getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 12))
        print(error_message)

def create_pdf(HeatSystemDesignGUI, filename):
    """
    Creates a PDF with the results of the calculation, basierend auf der Auswahl der Abschnitte.
    """
    mixDesignTab = HeatSystemDesignGUI.mixDesignTab
    calcTab = HeatSystemDesignGUI.calcTab
    schematic_scene = mixDesignTab.techTab.schematic_scene  # Nimm an, dass dies die Szene ist


    # Zeige den Abschnitts-Auswahldialog
    dialog = PDFSelectionDialog()
    if not dialog.exec_():  # Wenn der Benutzer den Dialog abbricht
        return

    selected_sections = dialog.get_selected_sections()

    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Title
    story.append(Paragraph("Ergebnisse Variante 1", styles['Heading1']))
    description_text = "Beschreibung: ..."
    story.append(Paragraph(description_text, styles['Normal']))
    story.append(Spacer(1, 12))

    # Add sections basierend auf der Auswahl
    if selected_sections['net_structure']:
        add_net_structure_section(story, calcTab)
    if selected_sections['economic_conditions']:
        add_economic_conditions_section(story, mixDesignTab)
    if selected_sections['technologies']:
        add_technologies_section(story, mixDesignTab)
    if selected_sections.get('technologies_scene', True):
        add_schematic_scene_section(story, schematic_scene)
    if selected_sections['costs_net_infrastructure']:
        add_costs_net_infrastructure_section(story, mixDesignTab)
    if selected_sections['costs_heat_generators']:
        add_costs_heat_generators_section(story, mixDesignTab)
    if selected_sections['costs_total']:
        add_costs_total_section(story, mixDesignTab)
    if selected_sections['results']:
        add_results_section(story, mixDesignTab)
    if selected_sections['combined_results']:
        add_combined_results_section(story, mixDesignTab)

    # Build the PDF
    doc.build(story)
