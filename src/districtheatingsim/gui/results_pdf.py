"""
Results PDF Generation Module
=============================

This module provides PDF generation functionality for district heating calculation results
using ReportLab for professional report output.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-05
"""

import numpy as np
import pandas as pd

from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Rect, Group
from reportlab.platypus import Image as PlatypusImage

from PyQt5.QtCore import QBuffer
from PyQt5.QtGui import QPainter, QPixmap

from districtheatingsim.gui.dialogs import PDFSelectionDialog

def get_custom_table_style():
    """
    Get custom table styling for PDF reports.
    
    Returns
    -------
    TableStyle
        ReportLab table style with grey header and beige body.
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

def add_figure_to_story(figure, story, max_width=6.5 * inch, figures_per_row=2):
    """
    Add matplotlib figure to PDF with border.
    
    Parameters
    ----------
    figure : matplotlib.figure.Figure
        Figure to add.
    story : list
        PDF story elements list.
    max_width : float, optional
        Maximum figure width in inches.
    figures_per_row : int, optional
        Number of figures per row (unused currently).
    """
    img_buffer = BytesIO()
    figure.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300)
    img_buffer.seek(0)

    img = PlatypusImage(img_buffer)
    aspect_ratio = img.drawWidth / img.drawHeight

    if img.drawWidth > max_width:
        img.drawWidth = max_width
        img.drawHeight = img.drawWidth / aspect_ratio

    cell = [[img]]
    table = Table(cell, colWidths=[img.drawWidth + 4], rowHeights=[img.drawHeight + 4])
    table.setStyle(
        TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ])
    )

    story.append(table)
    story.append(Spacer(1, 12))

def add_net_structure_section(story, calcTab):
    """
    Add network structure section to PDF.
    
    Parameters
    ----------
    story : list
        PDF story elements list.
    calcTab : object
        Calculation tab containing network figures.
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
    Add economic conditions table to PDF.
    
    Parameters
    ----------
    story : list
        PDF story elements list.
    mixDesignTab : object
        Mix design tab containing economic parameters.
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
    Add energy technologies section to PDF.
    
    Parameters
    ----------
    story : list
        PDF story elements list.
    mixDesignTab : object
        Mix design tab containing technology data.
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
    Convert QGraphicsScene to BytesIO image.
    
    Parameters
    ----------
    scene : QGraphicsScene
        Qt graphics scene to export.
        
    Returns
    -------
    BytesIO
        Image data as BytesIO stream.
    """
    scene_rect = scene.sceneRect()
    image = QPixmap(int(scene_rect.width()), int(scene_rect.height()))

    painter = QPainter(image)
    scene.render(painter)
    painter.end()

    qimage = image.toImage()

    buffer = QBuffer()
    buffer.open(QBuffer.ReadWrite)
    qimage.save(buffer, "PNG")

    buffer.seek(0)
    byte_array = buffer.data()
    
    img_buffer = BytesIO(byte_array)
    img_buffer.seek(0)

    return img_buffer

def add_schematic_scene_section(story, scene, max_width=6.5 * inch):
    """
    Add schematic scene image to PDF.
    
    Parameters
    ----------
    story : list
        PDF story elements list.
    scene : QGraphicsScene
        Qt graphics scene to add.
    max_width : float, optional
        Maximum image width in inches.
    """
    try:
        img_buffer = export_scene_to_image(scene)

        img = PlatypusImage(img_buffer)
        aspect_ratio = img.drawWidth / img.drawHeight

        if img.drawWidth > max_width:
            img.drawWidth = max_width
            img.drawHeight = img.drawWidth / aspect_ratio

        cell = [[img]]
        table = Table(cell, colWidths=[img.drawWidth + 4], rowHeights=[img.drawHeight + 4])
        table.setStyle(
            TableStyle([
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ])
        )

        story.append(Paragraph("Schematische Darstellung", getSampleStyleSheet()['Heading2']))
        story.append(table)
        story.append(Spacer(1, 12))

    except Exception as e:
        error_message = f"Fehler beim Export der Szene: {str(e)}"
        story.append(Paragraph(error_message, getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 12))
        print(error_message)

def add_costs_net_infrastructure_section(story, mixDesignTab):
    """
    Add network infrastructure costs table to PDF.
    
    Parameters
    ----------
    story : list
        PDF story elements list.
    mixDesignTab : object
        Mix design tab containing cost data.
    """
    try:
        if not hasattr(mixDesignTab, 'costTab') or mixDesignTab.costTab.data.empty:
            story.append(Paragraph("Fehlende Daten: Netzinfrastruktur", getSampleStyleSheet()['Normal']))
            story.append(Spacer(1, 12))
            return

        story.append(Paragraph("Netzinfrastruktur", getSampleStyleSheet()['Heading2']))

        data = mixDesignTab.costTab.data
        columns = ['Beschreibung'] + data.columns.tolist()
        infra_data = [columns]

        for index, row in data.iterrows():
            formatted_row = [index]
            for col_name in data.columns:
                value = row[col_name]
                if col_name == 'Kosten' or col_name == 'Annuität':
                    formatted_row.append(f"{value:,.0f} €" if pd.notna(value) else "")
                elif col_name == 'T_N':
                    formatted_row.append(f"{value} a" if pd.notna(value) and value != '' else "")
                elif col_name in ['F_inst', 'F_w_insp']:
                    formatted_row.append(f"{value} %" if pd.notna(value) and value != '' else "")
                elif col_name == 'Bedienaufwand':
                    formatted_row.append(f"{value} h" if pd.notna(value) and value != '' else "")
                else:
                    formatted_row.append(str(value) if pd.notna(value) else "")
            infra_data.append(formatted_row)

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
    Add heat generator costs table to PDF.
    
    Parameters
    ----------
    story : list
        PDF story elements list.
    mixDesignTab : object
        Mix design tab containing generator cost data.
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
    Add total costs charts to PDF.
    
    Parameters
    ----------
    story : list
        PDF story elements list.
    mixDesignTab : object
        Mix design tab containing cost charts.
    """
    try:
        story.append(Paragraph("Gesamtkosten", getSampleStyleSheet()['Heading2']))

        add_figure_to_story(mixDesignTab.costTab.bar_chart_figure, story)
        add_figure_to_story(mixDesignTab.costTab.pie_chart_figure, story)

    except Exception as e:
        error_message = f"Fehlende Daten im Gesamtkostenabschnitt: {str(e)}"
        story.append(Paragraph(error_message, getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 12))
        print(error_message)

def add_results_section(story, mixDesignTab):
    """
    Add calculation results with charts and table to PDF.
    
    Parameters
    ----------
    story : list
        PDF story elements list.
    mixDesignTab : object
        Mix design tab containing results data.
    """
    try:
        story.append(Paragraph("Berechnungsergebnisse", getSampleStyleSheet()['Heading2']))

        for figure in [mixDesignTab.resultTab.stackPlotFigure, mixDesignTab.resultTab.pieChartFigure]:
            add_figure_to_story(figure, story)

        print("Results Data:", mixDesignTab.resultTab.energy_system.results)

        results_data = [("Technologie", "Wärmemenge (MWh)", "Kosten (€/MWh)", "Anteil (%)", "spez. CO2-Emissionen (tCO2/MWh_th)", "Primärenergiefaktor")]
        results_data.extend([
            (tech, f"{wärmemenge:.2f}", f"{wgk:.2f}", f"{anteil*100:.2f}", f"{spec_emission:.4f}", f"{primary_energy/wärmemenge:.4f}")
            for tech, wärmemenge, wgk, anteil, spec_emission, primary_energy in zip(mixDesignTab.resultTab.energy_system.results['techs'], 
                                                                                    mixDesignTab.resultTab.energy_system.results['Wärmemengen'], 
                                                                                    mixDesignTab.resultTab.energy_system.results['WGK'],
                                                                                    mixDesignTab.resultTab.energy_system.results['Anteile'],
                                                                                    mixDesignTab.resultTab.energy_system.results['specific_emissions_L'],
                                                                                    mixDesignTab.resultTab.energy_system.results['primärenergie_L'])
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
    Add combined results summary table to PDF.
    
    Parameters
    ----------
    story : list
        PDF story elements list.
    mixDesignTab : object
        Mix design tab containing combined results data.
    """
    try:
        story.append(Paragraph("Kombinierte Ergebnisse", getSampleStyleSheet()['Heading2']))
        
        results = mixDesignTab.resultTab.energy_system.results
        waerme_ges_kW = np.sum(results["waerme_ges_kW"])
        strom_wp_kW = np.sum(results["strom_wp_kW"])
        if 'Summe Infrastruktur' in mixDesignTab.costTab.data.index:
            WGK_Infra = mixDesignTab.costTab.data.at['Summe Infrastruktur', 'Annuität'] / results['Jahreswärmebedarf']
        else:
            WGK_Infra = 0
        wgk_heat_pump_electricity = ((strom_wp_kW / 1000) * mixDesignTab.economic_parameters["electricity_price"]) / ((strom_wp_kW + waerme_ges_kW) / 1000)
        WGK_Gesamt = results['WGK_Gesamt'] + WGK_Infra + wgk_heat_pump_electricity
        
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
        
        combined_results_table = Table(combined_results_data, colWidths=[2 * inch, 1.5 * inch, 1.2 * inch])
        combined_results_table.setStyle(get_custom_table_style())
        
        story.append(KeepTogether(combined_results_table))
        story.append(Spacer(1, 12))
    
    except Exception as e:
        error_message = f"Fehlende Daten im Abschnitt Kombinierte Ergebnisse: {str(e)}"
        story.append(Paragraph(error_message, getSampleStyleSheet()['Normal']))
        story.append(Spacer(1, 12))
        print(error_message)

def create_pdf(HeatSystemDesignGUI, filename):
    """
    Create PDF report with selected sections.
    
    Main function to generate a comprehensive PDF report from calculation results.
    Shows selection dialog for report sections and generates PDF with chosen content.
    
    Parameters
    ----------
    HeatSystemDesignGUI : object
        Main GUI object containing all analysis tabs and data.
    filename : str
        Output filename for the PDF report.
    """
    mixDesignTab = HeatSystemDesignGUI.mixDesignTab
    calcTab = HeatSystemDesignGUI.calcTab
    schematic_scene = mixDesignTab.techTab.schematic_scene

    dialog = PDFSelectionDialog()
    if not dialog.exec_():
        return

    selected_sections = dialog.get_selected_sections()

    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    story.append(Paragraph("Ergebnisse Variante 1", styles['Heading1']))
    description_text = "Beschreibung: ..."
    story.append(Paragraph(description_text, styles['Normal']))
    story.append(Spacer(1, 12))

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

    doc.build(story)