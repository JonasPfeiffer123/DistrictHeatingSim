### Erstellt von Jonas Pfeiffer ###
from io import BytesIO

import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors

### Export Ergebnisse mit PDF ###
def create_pdf(self, filename):
    # Erstellen eines leeren PDF-Dokuments
    pdf = PyPDF2.PdfWriter()

    # Erstellen eines PDF-Berichts mit ReportLab
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Überschrift "Ergebnisse Variante 1"
    story.append(Paragraph("Ergebnisse Variante 1", styles['Heading1']))

    # Beschreibung
    description_text = "Beschreibung: ..."
    story.append(Paragraph(description_text, styles['Normal']))
    story.append(Spacer(1, 12))

    # Platzhalter für das Bild
    """image_path = "path/to/your/image.png"  # Pfad zum Bild
    img = Image(image_path)
    img.drawHeight = 2 * inch  # Passen Sie die Größe nach Bedarf an
    img.drawWidth = 4 * inch  # Passen Sie die Größe nach Bedarf an
    story.append(img)
    story.append(Spacer(1, 12))"""

    # Darstellung der wirtschaftlichen Randbedingungen
    story.append(Paragraph("Wirtschaftliche Randbedingungen", styles['Heading2']))
    # Werte der wirtschaftlichen Bedingungen aus der Funktion getValues holen
    economic_conditions = self.economicParametersDialog.getValues()

    # Schleife durch die Werte der wirtschaftlichen Bedingungen und in Tabelle umwandeln
    economic_conditions_data = [(key, value) for key, value in economic_conditions.items()]
    economic_conditions_table = Table(economic_conditions_data, colWidths=[150, 50])
    economic_conditions_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.beige),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(economic_conditions_table)

    # Darstellung der Technologien
    story.append(Paragraph("Technologien", styles['Heading2']))
    for tech in self.tech_objects:
        story.append(Paragraph(self.formatTechForDisplay(tech), styles['Normal']))
        story.append(Spacer(1, 12))
    

    # Darstellung der Netzinfrastruktur
    story.append(Paragraph("Netzinfrastruktur", styles['Heading2']))
    # Tabelle erstellen
    # Hole die aktuellen Infrastruktur-Objekte aus dem Dialog
    values = self.netInfrastructureDialog.getValues()
    infraObjects = self.getCurrentInfraObjects()
    columns = ['Beschreibung', 'Kosten', 'Technische Nutzungsdauer', 'f_Inst', 'f_W_Insp', 'Bedienaufwand', 'Gesamtannuität']
    
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
                TN = int(values.get(f"{obj}_technische nutzungsdauer", 0))
                f_Inst = float(values.get(f"{obj}_f_inst", 0))
                f_W_Insp = float(values.get(f"{obj}_f_w_insp", 0))
                Bedienaufwand = float(values.get(f"{obj}_bedienaufwand", 0))
                annuität = self.calc_annuität(A0, TN, f_Inst, f_W_Insp, Bedienaufwand)
    
        row_data.append("{:.0f}".format(annuität))

        infra_data.append(row_data)

    # Summenzeile hinzufügen
    summen_row = ["Summe Infrastruktur", "{:.0f}".format(self.summe_investitionskosten), "", "", "", "", "{:.0f}".format(self.summe_annuität)]
    infra_data.append(summen_row)

    # Tabelle formatieren
    infra_table = Table(infra_data)
    infra_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    # Tabelle zur Story hinzufügen
    story.append(infra_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Berechnungsergebnisse", styles['Heading2']))
    # Ergebnisse in Tabelle umwandeln
    results_data = [("Technologie", "Wärmemenge (MWh)", "Kosten (€/MWh)", "Anteil (%)")]
    results_data.extend([
        (tech, f"{wärmemenge:.2f}", f"{wgk:.2f}", f"{anteil*100:.2f}%")
        for tech, wärmemenge, wgk, anteil in zip(self.results['techs'], self.results['Wärmemengen'], self.results['WGK'], self.results['Anteile'])
    ])
    results_table = Table(results_data)
    results_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(results_table)
    story.append(Spacer(1, 12))

    # Daten für die zusätzlichen Informationen sammeln
    additional_info_data = [
        ("Jahreswärmebedarf (MWh)", f"{self.results['Jahreswärmebedarf']:.0f}"),
        ("Stromerzeugung (MWh)", f"{self.results['Strommenge']:.0f}"),
        ("Strombedarf (MWh)", f"{self.results['Strombedarf']:.0f}"),
        ("Wärmegestehungskosten Erzeugeranlagen (€/MWh)", f"{self.results['WGK_Gesamt']:.2f}"),
        ("Wärmegestehungskosten Netzinfrastruktur (€/MWh)", f"{self.WGK_Infra:.2f}"),
        ("Wärmegestehungskosten Gesamt (€/MWh)", f"{self.WGK_Gesamt:.2f}")
    ]

    # Tabelle für die zusätzlichen Informationen erstellen
    additional_info_table = Table(additional_info_data, colWidths=[250, 100])
    additional_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    # Zusätzliche Informationen zur Story hinzufügen
    story.append(additional_info_table)
    story.append(Spacer(1, 12))

    # Diagramme als Bilder hinzufügen
    for figure in [self.figure1, self.figure2]:
        img_buffer = BytesIO()
        figure.savefig(img_buffer, format='png', bbox_inches='tight', dpi=300)
        img_buffer.seek(0)
        img = Image(img_buffer)
        img.drawHeight = 4 * inch  # Höhe einstellen
        img.drawWidth = 6 * inch  # Breite einstellen
        img.keepAspectRatio = True  # Seitenverhältnis beibehalten
        story.append(img)
        story.append(Spacer(1, 12))

    # PDF-Dokument erstellen
    doc.build(story)

    # Fügen Sie das erstellte PDF zum leeren PDF-Dokument hinzu
    pdf_report = open(filename, 'rb')
    pdf_reader = PyPDF2.PdfReader(pdf_report)
    pdf.add_page(pdf_reader.pages[0])