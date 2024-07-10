### Erstellt von Jonas Pfeiffer ###
from io import BytesIO

import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

def get_standard_table_style():
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (0, 0), (-1, -1), 'LTR')
    ])

### Export Ergebnisse mit PDF ###
def create_pdf(MixDesignTab, filename):
    # Erstellen eines leeren PDF-Dokuments
    pdf = PyPDF2.PdfWriter()

    # Erstellen eines PDF-Berichts mit ReportLab
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Name des Projektes
    # name = None
    # Beschreibung des Projektes
    # description = None

    # Überschrift "Ergebnisse Variante 1"
    story.append(Paragraph("Ergebnisse Variante 1", styles['Heading1']))

    # Beschreibung
    description_text = "Beschreibung: ..."
    story.append(Paragraph(description_text, styles['Normal']))
    story.append(Spacer(1, 12))

    ### Darstellung der Netzstruktur ###
    story.append(Paragraph("Netzstruktur", styles['Heading2']))

    for figure in [MixDesignTab.parent.calcTab.figure5]:
        # Save figure to a buffer
        img_buffer = BytesIO()
        figure.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300)
        img_buffer.seek(0)
        
        # Create an image object from the buffer
        img = Image(img_buffer)
        
        # Calculate the aspect ratio
        aspect_ratio = img.drawWidth / img.drawHeight
        
        # Set the dimensions, preserving the aspect ratio
        img.drawHeight = 4 * inch  # Set height
        img.drawWidth = aspect_ratio * img.drawHeight  # Set width based on aspect ratio
        img.keepAspectRatio = True  # Maintain aspect ratio
        
        # Add the image to the story
        story.append(img)
        story.append(Spacer(1, 12))

    ### Darstellung der wirtschaftlichen Randbedingungen ###
    story.append(Paragraph("Wirtschaftliche Randbedingungen", styles['Heading2']))

    # Werte der wirtschaftlichen Bedingungen aus der Funktion getValues holen
    economic_conditions = MixDesignTab.economicParametersDialog.getValues()

    # Kopfzeile hinzufügen
    economic_conditions_data = [("Parameter", "Wert")]
    # Schleife durch die Werte der wirtschaftlichen Bedingungen und in Tabelle umwandeln
    economic_conditions_data.extend([(key, value) for key, value in economic_conditions.items()])

    # Tabelle erstellen und stilisieren
    economic_conditions_table = Table(economic_conditions_data)
    economic_conditions_table.setStyle(get_standard_table_style())
    story.append(KeepTogether(economic_conditions_table))
    story.append(Spacer(1, 12))

    ### Diagramm Wärmebedarf ###
    for figure in [MixDesignTab.techTab.plotFigure]:
        img_buffer = BytesIO()
        figure.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300)
        img_buffer.seek(0)

        img = Image(img_buffer)

        # Calculate the aspect ratio
        aspect_ratio = img.drawWidth / img.drawHeight
        
        # Set the dimensions, preserving the aspect ratio
        img.drawHeight = 4 * inch  # Set height
        img.drawWidth = aspect_ratio * img.drawHeight  # Set width based on aspect ratio
        img.keepAspectRatio = True  # Maintain aspect ratio

        story.append(img)
        story.append(Spacer(1, 12))

    ### Darstellung der Erzeugertechnologien ###
    story.append(Paragraph("Erzeugertechnologien", styles['Heading2']))

    for tech in MixDesignTab.techTab.tech_objects:
        story.append(Paragraph(MixDesignTab.techTab.formatTechForDisplay(tech), styles['Normal']))
        story.append(Spacer(1, 12))

    # Darstellung der Netzinfrastruktur
    story.append(Paragraph("Netzinfrastruktur", styles['Heading2']))
    # Tabelle erstellen
    values = MixDesignTab.netInfrastructureDialog.getValues()
    infraObjects = MixDesignTab.netInfrastructureDialog.getCurrentInfraObjects()
    columns = ['Beschreibung', 'Kosten', 'T_N', 'f_Inst', 'f_W_Insp', 'Bedienaufwand', 'Gesamtannuität']

    infra_data = []
    infra_data.append(columns)

    for i, obj in enumerate(infraObjects):
        row_data = [obj.capitalize()]
        annuität = 0  # Initialisiere Annuität auf 0
        for j, col in enumerate(columns[1:], 1):
            key = f"{obj}_{col.lower()}"
            value = values.get(key, "")
            if value != "":
                row_data.append(str(value))

            if col == 'Kosten':
                # Annuität berechnen und hinzufügen
                A0 = float(values.get(f"{obj}_kosten", 0))
                TN = int(values.get(f"{obj}_t_n", 0))
                f_Inst = float(values.get(f"{obj}_f_inst", 0))
                f_W_Insp = float(values.get(f"{obj}_f_w_insp", 0))
                Bedienaufwand = float(values.get(f"{obj}_bedienaufwand", 0))
                annuität = MixDesignTab.costTab.calc_annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand)

        row_data.append("{:.0f}".format(annuität))

        infra_data.append(row_data)

    # Summenzeile hinzufügen
    summen_row = ["Summe Infrastruktur", "{:.0f}".format(MixDesignTab.costTab.summe_investitionskosten), "", "", "", "", "{:.0f}".format(MixDesignTab.costTab.summe_annuität)]
    infra_data.append(summen_row)

    # Tabelle formatieren
    infra_table = Table(infra_data)
    infra_table.setStyle(get_standard_table_style())

    # Tabelle zur Story hinzufügen
    story.append(KeepTogether(infra_table))
    story.append(Spacer(1, 12))

    # Ergebnisse aus dem costTab hinzufügen
    story.append(Paragraph("Kosten Erzeuger", styles['Heading2']))
    tech_data = MixDesignTab.costTab.techDataTable
    tech_columns = [tech_data.horizontalHeaderItem(i).text() for i in range(tech_data.columnCount())]
    tech_rows = []

    for row in range(tech_data.rowCount()):
        tech_row = []
        for col in range(tech_data.columnCount()):
            item = tech_data.item(row, col)
            tech_row.append(Paragraph(item.text() if item else "", styles['Normal']))
        tech_rows.append(tech_row)

    tech_data_table = Table([tech_columns] + tech_rows)
    tech_data_table.setStyle(get_standard_table_style())
    story.append(KeepTogether(tech_data_table))
    story.append(Spacer(1, 12))

    # Kostenaufteilung Diagramm hinzufügen
    story.append(Paragraph("Kostenzusammensetzung", styles['Heading2']))

    for figure in [MixDesignTab.costTab.figure]:
        img_buffer = BytesIO()
        figure.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300)
        img_buffer.seek(0)

        img = Image(img_buffer)

        # Calculate the aspect ratio
        aspect_ratio = img.drawWidth / img.drawHeight
        
        # Set the dimensions, preserving the aspect ratio
        img.drawHeight = 4 * inch  # Set height
        img.drawWidth = aspect_ratio * img.drawHeight  # Set width based on aspect ratio
        img.keepAspectRatio = True  # Maintain aspect ratio

        story.append(img)
        story.append(Spacer(1, 12))

    # Summenlabel hinzufügen
    story.append(Paragraph(f"Gesamtkosten: {MixDesignTab.costTab.summe_investitionskosten + MixDesignTab.costTab.summe_tech_kosten:.0f} €", styles['Normal']))

    # Berechnungsergebnisse im PDF ausgeben
    story.append(Paragraph("Berechnungsergebnisse", styles['Heading2']))

    # Diagramme als Bilder hinzufügen
    for figure in [MixDesignTab.resultTab.figure1, MixDesignTab.resultTab.pieChartFigure]:
        img_buffer = BytesIO()
        figure.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300)
        img_buffer.seek(0)

        img = Image(img_buffer)

        # Calculate the aspect ratio
        aspect_ratio = img.drawWidth / img.drawHeight
        
        # Set the dimensions, preserving the aspect ratio
        img.drawHeight = 4 * inch  # Set height
        img.drawWidth = aspect_ratio * img.drawHeight  # Set width based on aspect ratio
        img.keepAspectRatio = True  # Maintain aspect ratio

        story.append(img)
        story.append(Spacer(1, 12))

    # Ergebnisse in Tabelle umwandeln
    results_data = [("Technologie", "Wärmemenge (MWh)", "Kosten (€/MWh)", "Anteil (%)", "spez. CO2-Emissionen (t_CO2/MWh_th)", "Primärenergiefaktor")]
    results_data.extend([
        (tech, f"{wärmemenge:.2f}", f"{wgk:.2f}", f"{anteil*100:.2f}", f"{spec_emission}", f"{primary_energy/wärmemenge}")
        for tech, wärmemenge, wgk, anteil, spec_emission, primary_energy in zip(MixDesignTab.results['techs'], MixDesignTab.results['Wärmemengen'], MixDesignTab.results['WGK'], 
                                                 MixDesignTab.results['Anteile'], MixDesignTab.results['specific_emissions_L'], MixDesignTab.results['primärenergie_L'])
    ])
    results_table = Table(results_data)
    results_table.setStyle(get_standard_table_style())
    story.append(KeepTogether(results_table))
    story.append(Spacer(1, 12))

    # Daten für die zusätzlichen Informationen sammeln
    additional_info_data = [
        ("Parameter", "Wert"),
        ("Jahreswärmebedarf (MWh)", f"{MixDesignTab.results['Jahreswärmebedarf']:.0f}"),
        ("Stromerzeugung (MWh)", f"{MixDesignTab.results['Strommenge']:.0f}"),
        ("Strombedarf (MWh)", f"{MixDesignTab.results['Strombedarf']:.0f}"),
        ("Wärmegestehungskosten Erzeugeranlagen (€/MWh)", f"{MixDesignTab.results['WGK_Gesamt']:.2f}"),
        ("Wärmegestehungskosten Netzinfrastruktur (€/MWh)", f"{MixDesignTab.resultTab.WGK_Infra:.2f}"),
        ("Wärmegestehungskosten dezentrale Wärmepumpen (€/MWh)", f"{MixDesignTab.resultTab.wgk_heat_pump_electricity:.2f}"),
        ("Wärmegestehungskosten Gesamt (€/MWh)", f"{MixDesignTab.resultTab.WGK_Gesamt:.2f}"),
        ("spez. CO2-Emissionen Wärme (tCO2/MWh_th)", f"{MixDesignTab.results['specific_emissions_Gesamt']:.4f}"),
        ("CO2-Emissionen Wärme (tCO2)", f"{MixDesignTab.results['specific_emissions_Gesamt']*MixDesignTab.results['Jahreswärmebedarf']:.2f}"),
        ("Primärenergiefaktor", f"{MixDesignTab.results['primärenergiefaktor_Gesamt']:.4f}")
    ]

    # Tabelle für die zusätzlichen Informationen erstellen
    additional_info_table = Table(additional_info_data)
    additional_info_table.setStyle(get_standard_table_style())

    # Zusätzliche Informationen zur Story hinzufügen
    story.append(KeepTogether(additional_info_table))
    story.append(Spacer(1, 12))

    # Diagramm aus dem SensitivityTab hinzufügen
    story.append(Paragraph("Sensitivitätsuntersuchung", styles['Heading2']))

    for figure in [MixDesignTab.sensitivityTab.figure]:
        img_buffer = BytesIO()
        figure.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300)
        img_buffer.seek(0)

        img = Image(img_buffer)

        # Calculate the aspect ratio
        aspect_ratio = img.drawWidth / img.drawHeight
        
        # Set the dimensions, preserving the aspect ratio
        img.drawHeight = 4 * inch  # Set height
        img.drawWidth = aspect_ratio * img.drawHeight  # Set width based on aspect ratio
        img.keepAspectRatio = True  # Maintain aspect ratio

        story.append(img)
        story.append(Spacer(1, 12))

    # PDF-Dokument erstellen
    doc.build(story)

    # Fügen Sie das erstellte PDF zum leeren PDF-Dokument hinzu
    pdf_report = open(filename, 'rb')
    pdf_reader = PyPDF2.PdfReader(pdf_report)
    pdf.add_page(pdf_reader.pages[0])