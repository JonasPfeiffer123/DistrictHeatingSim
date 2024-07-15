### Erstellt von Jonas Pfeiffer ###
from io import BytesIO

import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

def get_custom_table_style():
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('WORDWRAP', (0, 0), (-1, -1), 'LTR'),
        ('FONTSIZE', (0, 0), (-1, -1), 8)  # Schriftgröße auf 8 setzen
    ])

def add_figure_to_story(figure, story, max_width=6.5 * inch):
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

### Export Ergebnisse mit PDF ###
def create_pdf(MixDesignTab, filename):
    pdf = PyPDF2.PdfWriter()
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    story.append(Paragraph("Ergebnisse Variante 1", styles['Heading1']))

    description_text = "Beschreibung: ..."
    story.append(Paragraph(description_text, styles['Normal']))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Netzstruktur", styles['Heading2']))

    for figure in [MixDesignTab.parent.calcTab.figure5]:
        add_figure_to_story(figure, story)

    story.append(Paragraph("Wirtschaftliche Randbedingungen", styles['Heading2']))

    economic_conditions = MixDesignTab.economicParametersDialog.getValues()
    economic_conditions_data = [("Parameter", "Wert")]
    economic_conditions_data.extend([(key, value) for key, value in economic_conditions.items()])

    economic_conditions_table = Table(economic_conditions_data)
    economic_conditions_table.setStyle(get_custom_table_style())
    story.append(KeepTogether(economic_conditions_table))
    story.append(Spacer(1, 12))

    for figure in [MixDesignTab.techTab.plotFigure]:
        add_figure_to_story(figure, story)

    story.append(Paragraph("Erzeugertechnologien", styles['Heading2']))

    for tech in MixDesignTab.techTab.tech_objects:
        story.append(Paragraph(MixDesignTab.techTab.formatTechForDisplay(tech), styles['Normal']))
        story.append(Spacer(1, 12))

    story.append(Paragraph("Netzinfrastruktur", styles['Heading2']))
    values = MixDesignTab.netInfrastructureDialog.getValues()
    infraObjects = MixDesignTab.netInfrastructureDialog.getCurrentInfraObjects()
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
                annuität = MixDesignTab.costTab.calc_annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand)

        row_data.append("{:.0f}".format(annuität))
        infra_data.append(row_data)

    summen_row = ["Summe Infrastruktur", "{:.0f}".format(MixDesignTab.costTab.summe_investitionskosten), "", "", "", "", "{:.0f}".format(MixDesignTab.costTab.summe_annuität)]
    infra_data.append(summen_row)

    infra_table = Table(infra_data)
    infra_table.setStyle(get_custom_table_style())
    story.append(KeepTogether(infra_table))
    story.append(Spacer(1, 12))

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

    tech_data_table = Table([tech_columns] + tech_rows, colWidths=[1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
    tech_data_table.setStyle(get_custom_table_style())
    story.append(KeepTogether(tech_data_table))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Kostenzusammensetzung", styles['Heading2']))

    for figure in [MixDesignTab.costTab.figure]:
        add_figure_to_story(figure, story)

    story.append(Paragraph(f"Gesamtkosten: {MixDesignTab.costTab.summe_investitionskosten + MixDesignTab.costTab.summe_tech_kosten:.0f} €", styles['Normal']))

    story.append(Paragraph("Berechnungsergebnisse", styles['Heading2']))

    for figure in [MixDesignTab.resultTab.figure1, MixDesignTab.resultTab.pieChartFigure]:
        add_figure_to_story(figure, story)

    results_data = [("Technologie", "Wärmemenge (MWh)", "Kosten (€/MWh)", "Anteil (%)", "spez. CO2-Emissionen (tCO2/MWh_th)", "Primärenergiefaktor")]
    results_data.extend([
        (tech, f"{wärmemenge:.2f}", f"{wgk:.2f}", f"{anteil*100:.2f}", f"{spec_emission:.4f}", f"{primary_energy/wärmemenge:.4f}")
        for tech, wärmemenge, wgk, anteil, spec_emission, primary_energy in zip(MixDesignTab.results['techs'], MixDesignTab.results['Wärmemengen'], MixDesignTab.results['WGK'], 
                                                 MixDesignTab.results['Anteile'], MixDesignTab.results['specific_emissions_L'], MixDesignTab.results['primärenergie_L'])
    ])
    results_table = Table(results_data, colWidths=[1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
    results_table.setStyle(get_custom_table_style())
    story.append(KeepTogether(results_table))
    story.append(Spacer(1, 12))

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

    additional_info_table = Table(additional_info_data, colWidths=[2 * inch, 4 * inch])
    additional_info_table.setStyle(get_custom_table_style())
    story.append(KeepTogether(additional_info_table))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Sensitivitätsuntersuchung", styles['Heading2']))

    for figure in [MixDesignTab.sensitivityTab.figure]:
        add_figure_to_story(figure, story)

    doc.build(story)

    pdf_report = open(filename, 'rb')
    pdf_reader = PyPDF2.PdfReader(pdf_report)
    pdf.add_page(pdf_reader.pages[0])