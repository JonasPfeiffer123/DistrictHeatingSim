import traceback

def debug_print(msg):
    print(f"[ProjectExplorer DEBUG] {msg}")
"""
Comparison Tab Module
====================

Modern tab widget for comprehensive project variant comparison and analysis.

Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-14
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QSplitter, 
    QScrollArea, QGroupBox, QGridLayout, QFrame, QLabel, 
    QPushButton, QTreeWidget, QTreeWidgetItem, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class ProjectExplorer(QWidget):
    """
    Project explorer widget for automatic variant discovery and selection.
    """
    
    variants_changed = pyqtSignal(list)  # Signal emitted when variant selection changes
    
    def __init__(self, folder_manager, config_manager, parent=None):
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.config_manager = config_manager
        self.selected_variants = []
        self.base_path = None
        self.initUI()
        # Connect to folder_manager signal for project path changes
        if hasattr(self.folder_manager, 'project_folder_changed'):
            self.folder_manager.project_folder_changed.connect(self.set_base_path)
        # Initialize base_path if available
        if hasattr(self.folder_manager, 'project_data_path') and self.folder_manager.project_data_path:
            self.set_base_path(self.folder_manager.project_data_path)
        else:
            self.set_base_path(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "project_data"))
        
    def initUI(self):
        """Initialize project explorer UI."""
        self.layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Projekt-Explorer")
        header_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        header_label.setStyleSheet("color: #fff; background: #222; padding: 8px 12px; border-radius: 6px; margin-bottom: 4px;")
        self.layout.addWidget(header_label)

        # Refresh button
        self.refresh_btn = QPushButton("Projekte aktualisieren")
        self.refresh_btn.clicked.connect(self.discover_projects)
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: #fff;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
                margin-bottom: 8px;
            }
            QPushButton:hover {
                background-color: #217dbb;
            }
        """)
        self.layout.addWidget(self.refresh_btn)

        # Project tree
        self.project_tree = QTreeWidget()
        self.project_tree.setHeaderLabel("Verfügbare Projekte")
        self.project_tree.itemChanged.connect(self.on_selection_changed)
        self.project_tree.setStyleSheet("""
            QTreeWidget {
                background: #181818;
                color: #eee;
                border-radius: 6px;
                font-size: 12px;
            }
            QTreeWidget::item {
                padding: 4px 8px;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background: #2d3a4a;
                color: #fff;
                border: 1px solid #3498db;
            }
            QTreeWidget::item:hover {
                background: #232323;
            }
            QHeaderView::section {
                background: #222;
                color: #fff;
                font-weight: bold;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QCheckBox {
                spacing: 6px;
                font-size: 12px;
            }
        """)
        self.layout.addWidget(self.project_tree)

        # Selection info
        self.info_label = QLabel("Keine Varianten ausgewählt")
        self.info_label.setStyleSheet("color: #aaa; font-style: italic; margin-top: 6px;")
        self.layout.addWidget(self.info_label)
        
    def set_base_path(self, base_path):
        """Set the base path and refresh project list."""
        self.base_path = base_path
        debug_print(f"set_base_path called with: {base_path}")
        self.discover_projects()

    def discover_projects(self):
        """Discover and populate project variants."""
        self.project_tree.clear()
        try:
            debug_print(f"discover_projects: base_path={self.base_path}")
            if not self.base_path or not os.path.exists(self.base_path):
                debug_print("Projekt-Datenordner nicht gefunden!")
                self.info_label.setText("Projekt-Datenordner nicht gefunden")
                return
            # Use parent directory of base_path to find all variants
            parent_dir = os.path.dirname(self.base_path)
            debug_print(f"Using parent_dir for variants: {parent_dir}")
            variants = [d for d in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, d)) and d.startswith("Variante")]
            debug_print(f"Found variant folders: {variants}")
            # Add all valid variants as top-level items
            variant_count = 0
            for variant_name in variants:
                variant_path = os.path.join(parent_dir, variant_name)
                if self.validate_variant(variant_path):
                    debug_print(f"Valid variant: {variant_name} at {variant_path}")
                    variant_item = QTreeWidgetItem([variant_name])
                    variant_item.setCheckState(0, Qt.CheckState.Checked)
                    variant_item.setData(0, Qt.ItemDataRole.UserRole, variant_path)
                    self.project_tree.addTopLevelItem(variant_item)
                    variant_count += 1
                else:
                    debug_print(f"Skipped (invalid): {variant_name} at {variant_path}")
            if variant_count == 0:
                self.info_label.setText("Keine gültigen Varianten gefunden")
            else:
                self.info_label.setText(f"{variant_count} Varianten gefunden")
            self.update_selected_variants()
        except Exception as e:
            debug_print(f"Exception in discover_projects: {e}\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Fehler", f"Fehler beim Laden der Projekte: {str(e)}")

    # No longer needed, replaced by set_base_path
            
    def validate_variant(self, variant_path):
        """Validate if variant contains required data files."""
        required_files = [
            os.path.join("Ergebnisse", "Ergebnisse.json"),
            os.path.join("Lastgang", "Lastgang.csv"),
            os.path.join("Wärmenetz", "Konfiguration Netzinitialisierung.json")
        ]
        valid = all(os.path.exists(os.path.join(variant_path, file)) for file in required_files)
        debug_print(f"validate_variant: {variant_path} valid={valid}")
        return valid
        
    def on_selection_changed(self, item, column):
        """Handle variant selection changes."""
        if item.data(0, Qt.ItemDataRole.UserRole):  # Only for variant items
            self.update_selected_variants()
            
    def update_selected_variants(self):
        """Update list of selected variants and emit signal."""
        self.selected_variants = []
        for i in range(self.project_tree.topLevelItemCount()):
            variant_item = self.project_tree.topLevelItem(i)
            if variant_item.checkState(0) == Qt.CheckState.Checked:
                variant_path = variant_item.data(0, Qt.ItemDataRole.UserRole)
                variant_name = variant_item.text(0)
                self.selected_variants.append({
                    'name': variant_name,
                    'path': variant_path
                })
        # Update info label
        count = len(self.selected_variants)
        if count == 0:
            self.info_label.setText("Keine Varianten ausgewählt")
        elif count == 1:
            self.info_label.setText("1 Variante ausgewählt")
        else:
            self.info_label.setText(f"{count} Varianten ausgewählt")
        # Emit signal
        self.variants_changed.emit(self.selected_variants)

class ComparisonDashboard(QWidget):
    """
    Main dashboard widget showing comparison overview and KPIs.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.variant_data = []
        self.initUI()
        
    def initUI(self):
        """Initialize dashboard UI."""
        self.layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Variantenvergleich - Dashboard")
        header_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.layout.addWidget(header_label)
        
        # Create scroll area for dashboard content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        
        # KPI Overview section
        self.create_kpi_section()
        
        # Charts section
        self.create_charts_section()
        
        scroll_area.setWidget(scroll_widget)
        self.layout.addWidget(scroll_area)
        
    def create_kpi_section(self):
        """Create KPI overview section."""
        kpi_group = QGroupBox("Kennzahlen-Übersicht")
        kpi_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        kpi_layout = QGridLayout(kpi_group)
        
        # Placeholder for KPI widgets - will be populated when data loads
        self.kpi_widgets = {}
        kpi_metrics = [
            ("Wärmegestehungskosten", "€/MWh"),
            ("CO2-Emissionen", "t_CO2/MWh"),
            ("Primärenergiefaktor", "-"),
            ("Jahreswärmebedarf", "MWh"),
            ("Trassenlänge", "m"),
            ("Verteilverluste", "%")
        ]
        
        for i, (metric, unit) in enumerate(kpi_metrics):
            row, col = i // 3, i % 3
            widget = self.create_kpi_widget(metric, unit)
            self.kpi_widgets[metric] = widget
            kpi_layout.addWidget(widget, row, col)
            
        self.scroll_layout.addWidget(kpi_group)
        
    def create_kpi_widget(self, title, unit):
        """Create individual KPI widget."""
        widget = QFrame()
        widget.setFrameStyle(QFrame.Shape.StyledPanel)
        widget.setMinimumHeight(80)
        
        layout = QVBoxLayout(widget)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        value_label = QLabel("--")
        value_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet("color: #2E8B57;")
        layout.addWidget(value_label)
        
        unit_label = QLabel(unit)
        unit_label.setFont(QFont("Arial", 8))
        unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        unit_label.setStyleSheet("color: #666;")
        layout.addWidget(unit_label)
        
        widget.value_label = value_label  # Store reference for updates
        return widget
        
    def create_charts_section(self):
        """Create charts section with tabbed organization."""
        # Create matplotlib figures with seaborn styling
        sns.set_style("whitegrid")
        plt.rcParams.update({
            'font.size': 11,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10
        })
        
        # Create tabbed chart organization for better space utilization
        charts_tab_widget = QTabWidget()
        charts_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 5px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 12px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #3498db;
            }
        """)
        
        # Economic Analysis Tab
        economic_tab = QWidget()
        economic_layout = QGridLayout(economic_tab)
        economic_layout.setSpacing(15)
        
        # Cost comparison chart (larger size)
        self.cost_figure = Figure(figsize=(8, 5))
        self.cost_canvas = FigureCanvas(self.cost_figure)
        economic_layout.addWidget(self.cost_canvas, 0, 0)
        
        charts_tab_widget.addTab(economic_tab, "💰 Wirtschaftlich")
        
        # Energy Analysis Tab (new)
        energy_tab = QWidget()
        energy_layout = QGridLayout(energy_tab)
        energy_layout.setSpacing(15)
        
        # Energy mix chart (moved from economic)
        self.energy_figure = Figure(figsize=(8, 5))
        self.energy_canvas = FigureCanvas(self.energy_figure)
        energy_layout.addWidget(self.energy_canvas, 0, 0)
        
        charts_tab_widget.addTab(energy_tab, "⚡ Energie")
        
        # Environmental Analysis Tab
        environmental_tab = QWidget()
        environmental_layout = QGridLayout(environmental_tab)
        environmental_layout.setSpacing(15)
        
        # CO2 emissions chart (larger size)
        self.co2_figure = Figure(figsize=(8, 5))
        self.co2_canvas = FigureCanvas(self.co2_figure)
        environmental_layout.addWidget(self.co2_canvas, 0, 0)
        
        # Primärenergiefaktor chart (larger size)
        self.pe_figure = Figure(figsize=(8, 5))
        self.pe_canvas = FigureCanvas(self.pe_figure)
        environmental_layout.addWidget(self.pe_canvas, 0, 1)
        
        charts_tab_widget.addTab(environmental_tab, "🌱 Umwelt")
        
        # Technical Analysis Tab
        technical_tab = QWidget()
        technical_layout = QVBoxLayout(technical_tab)
        technical_layout.setSpacing(15)
        
        # Network statistics chart (full width, larger size)
        self.network_figure = Figure(figsize=(16, 6))
        self.network_canvas = FigureCanvas(self.network_figure)
        technical_layout.addWidget(self.network_canvas)
        
        charts_tab_widget.addTab(technical_tab, "⚙️ Technik")
        
        self.scroll_layout.addWidget(charts_tab_widget)
        
    def update_dashboard(self, variant_data):
        """Update dashboard with new variant data."""
        self.variant_data = variant_data
        
        if not variant_data:
            self.clear_dashboard()
            return
            
        self.update_kpis()
        self.update_charts()
        
    def update_kpis(self):
        """Update KPI widgets with current data."""
        if not self.variant_data:
            # Reset all KPIs to default
            for widget in self.kpi_widgets.values():
                widget.value_label.setText("--")
            return
            
        # Calculate averages or ranges for KPIs
        try:
            # Extract metrics from variant data
            wgk_values = [v.get('WGK_Gesamt', 0) for v in self.variant_data if v.get('WGK_Gesamt', 0) not in (None, 0)]
            co2_values = [v.get('specific_emissions_Gesamt', 0) for v in self.variant_data if v.get('specific_emissions_Gesamt', 0) not in (None, 0)]
            pe_values = [v.get('primärenergiefaktor_Gesamt', 0) for v in self.variant_data if v.get('primärenergiefaktor_Gesamt', 0) not in (None, 0)]
            heat_values = [v.get('Jahreswärmebedarf', 0) for v in self.variant_data if v.get('Jahreswärmebedarf', 0) not in (None, 0)]

            # New: Extract network metrics
            trassenlänge_values = [v.get('Trassenlänge', 0) for v in self.variant_data if v.get('Trassenlänge', 0) not in (None, 0)]
            verluste_values = [v.get('Verteilverluste', 0) for v in self.variant_data if v.get('Verteilverluste', 0) not in (None, 0)]
            
            # Update KPI widgets with proper formatting
            # Wärmegestehungskosten
            if wgk_values:
                if len(wgk_values) == 1:
                    self.kpi_widgets['Wärmegestehungskosten'].value_label.setText(f"{wgk_values[0]:.1f}")
                else:
                    min_val, max_val = min(wgk_values), max(wgk_values)
                    self.kpi_widgets['Wärmegestehungskosten'].value_label.setText(f"{min_val:.1f} - {max_val:.1f}")
            else:
                self.kpi_widgets['Wärmegestehungskosten'].value_label.setText("--")
                
            # CO2-Emissionen
            if co2_values:
                if len(co2_values) == 1:
                    self.kpi_widgets['CO2-Emissionen'].value_label.setText(f"{co2_values[0]:.3f}")
                else:
                    min_val, max_val = min(co2_values), max(co2_values)
                    self.kpi_widgets['CO2-Emissionen'].value_label.setText(f"{min_val:.3f} - {max_val:.3f}")
            else:
                self.kpi_widgets['CO2-Emissionen'].value_label.setText("--")
                
            # Primärenergiefaktor
            if pe_values:
                if len(pe_values) == 1:
                    self.kpi_widgets['Primärenergiefaktor'].value_label.setText(f"{pe_values[0]:.2f}")
                else:
                    min_val, max_val = min(pe_values), max(pe_values)
                    self.kpi_widgets['Primärenergiefaktor'].value_label.setText(f"{min_val:.2f} - {max_val:.2f}")
            else:
                self.kpi_widgets['Primärenergiefaktor'].value_label.setText("--")
                
            # Jahreswärmebedarf
            if heat_values:
                if len(heat_values) == 1:
                    self.kpi_widgets['Jahreswärmebedarf'].value_label.setText(f"{heat_values[0]:.0f}")
                else:
                    min_val, max_val = min(heat_values), max(heat_values)
                    self.kpi_widgets['Jahreswärmebedarf'].value_label.setText(f"{min_val:.0f} - {max_val:.0f}")
            else:
                self.kpi_widgets['Jahreswärmebedarf'].value_label.setText("--")
                
            # Trassenlänge (new)
            if trassenlänge_values:
                if len(trassenlänge_values) == 1:
                    self.kpi_widgets['Trassenlänge'].value_label.setText(f"{trassenlänge_values[0]:.0f}")
                else:
                    min_val, max_val = min(trassenlänge_values), max(trassenlänge_values)
                    self.kpi_widgets['Trassenlänge'].value_label.setText(f"{min_val:.0f} - {max_val:.0f}")
            else:
                self.kpi_widgets['Trassenlänge'].value_label.setText("n.v.")  # "nicht verfügbar"
                
            # Verteilverluste (new)
            if verluste_values:
                if len(verluste_values) == 1:
                    self.kpi_widgets['Verteilverluste'].value_label.setText(f"{verluste_values[0]:.1f}")
                else:
                    min_val, max_val = min(verluste_values), max(verluste_values)
                    self.kpi_widgets['Verteilverluste'].value_label.setText(f"{min_val:.1f} - {max_val:.1f}")
            else:
                self.kpi_widgets['Verteilverluste'].value_label.setText("n.v.")
                
        except Exception as e:
            print(f"Error updating KPIs: {e}")
            # Reset to default on error
            for widget in self.kpi_widgets.values():
                widget.value_label.setText("--")
            
    def update_charts(self):
        """Update all comparison charts."""
        try:
            self.update_cost_chart()
            self.update_energy_chart()
            self.update_co2_chart()
            self.update_pe_chart()
            self.update_network_chart()
        except Exception as e:
            print(f"Error updating charts: {e}")
            
    def update_cost_chart(self):
        """Update cost comparison chart."""
        self.cost_figure.clear()
        
        if not self.variant_data:
            return
            
        ax = self.cost_figure.add_subplot(111)
        
        # Use shorter, cleaner names for charts
        names = [self.get_clean_variant_name(v.get('name', f'Variante {i+1}')) for i, v in enumerate(self.variant_data)]
        costs = [v.get('WGK_Gesamt', 0) for v in self.variant_data]
        
        bars = ax.bar(names, costs, color='#3498db', alpha=0.8, edgecolor='#2980b9', linewidth=1)
        
        ax.set_title('Wärmegestehungskosten Vergleich', fontweight='bold', fontsize=12)
        ax.set_ylabel('Kosten (€/MWh)', fontweight='bold')
        
        # Improve x-axis labels
        if len(names) > 3:
            ax.tick_params(axis='x', rotation=45, labelsize=9)
        else:
            ax.tick_params(axis='x', rotation=0, labelsize=10)
        
        # Add value labels on bars with better positioning
        for bar, cost in zip(bars, costs):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                   f'{cost:.1f}', ha='center', va='bottom', fontweight='bold', fontsize=10)

        # Improve layout
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_axisbelow(True)
        
        self.cost_figure.tight_layout()
        self.cost_canvas.draw()
        
    def get_clean_variant_name(self, full_name):
        """Extract clean variant name from full project path name."""
        if ' - ' in full_name:
            return full_name.split(' - ')[-1]  # Take the last part after ' - '
        return full_name
        
    def update_energy_chart(self):
        """Update energy mix comparison chart."""
        self.energy_figure.clear()
        if not self.variant_data:
            return

        n_variants = len(self.variant_data)
        if n_variants == 0:
            return
            
        fig = self.energy_figure
        
        # Adjust subplot layout based on number of variants
        if n_variants == 1:
            cols = 1
        elif n_variants == 2:
            cols = 2
        else:
            cols = min(3, n_variants)  # Max 3 columns
            
        rows = (n_variants + cols - 1) // cols  # Calculate required rows
        
        for i, variant in enumerate(self.variant_data):
            ax = fig.add_subplot(rows, cols, i + 1)
            techs = variant.get('techs', [])
            anteile = variant.get('Anteile', [])
            colors = variant.get('colors', plt.cm.Set3.colors[:len(techs)])

            if techs and anteile:
                filtered_data = [(tech, anteil, color) for tech, anteil, color in zip(techs, anteile, colors) if anteil > 1.0]
                if filtered_data:
                    techs_filtered, anteile_filtered, colors_filtered = zip(*filtered_data)
                else:
                    techs_filtered, anteile_filtered, colors_filtered = techs, anteile, colors
                wedges, texts = ax.pie(
                    anteile_filtered,
                    labels=None,
                    colors=colors_filtered,
                    autopct=None,
                    startangle=90
                )
                legend_labels = [f"{tech}: {anteil:.1f}%" for tech, anteil in zip(techs_filtered, anteile_filtered)]
                # Always show legend, right for 1-2, below for more
                if cols == 1 or (cols == 2 and n_variants <= 2):
                    ax.legend(wedges, legend_labels, loc='center left', bbox_to_anchor=(1.1, 0.5),
                              fontsize=9, frameon=True, fancybox=True, shadow=True)
                else:
                    ax.legend(wedges, legend_labels, loc='upper center', bbox_to_anchor=(0.5, -0.1),
                              ncol=2, fontsize=8, frameon=True, fancybox=True, shadow=True)
            clean_name = self.get_clean_variant_name(variant.get('name', f'Variante {i+1}'))
            ax.set_title(clean_name, fontsize=10, fontweight='bold', pad=10)

        fig.suptitle('Energiemix Vergleich', fontsize=12, fontweight='bold', y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.97])
        self.energy_canvas.draw()
        
    def update_co2_chart(self):
        """Update CO2 emissions comparison chart."""
        self.co2_figure.clear()
        
        if not self.variant_data:
            return
            
        ax = self.co2_figure.add_subplot(111)
        
        names = [self.get_clean_variant_name(v.get('name', f'Variante {i+1}')) for i, v in enumerate(self.variant_data)]
        emissions = [v.get('specific_emissions_Gesamt', 0) for v in self.variant_data]
        
        # Create CO2 bar chart
        bars = ax.bar(names, emissions, color='#e74c3c', alpha=0.8, edgecolor='#c0392b', linewidth=1)
        
        ax.set_title('CO2-Emissionen Vergleich', fontweight='bold', fontsize=12)
        ax.set_ylabel('CO2-Emissionen (t/MWh)', fontweight='bold')
        ax.set_xlabel('Varianten', fontweight='bold')
        
        # Rotate labels if needed
        if len(names) > 3:
            ax.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, emission in zip(bars, emissions):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                   f'{emission:.3f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        # Improve grid and styling
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_axisbelow(True)
        
        self.co2_figure.tight_layout()
        self.co2_canvas.draw()
        
    def update_pe_chart(self):
        """Update Primärenergiefaktor comparison chart."""
        self.pe_figure.clear()
        
        if not self.variant_data:
            return
            
        ax = self.pe_figure.add_subplot(111)
        
        names = [self.get_clean_variant_name(v.get('name', f'Variante {i+1}')) for i, v in enumerate(self.variant_data)]
        pe_factors = [v.get('primärenergiefaktor_Gesamt', 0) for v in self.variant_data]
        
        # Create PE factor bar chart
        bars = ax.bar(names, pe_factors, color='#f39c12', alpha=0.8, edgecolor='#e67e22', linewidth=1)
        
        ax.set_title('Primärenergiefaktor Vergleich', fontweight='bold', fontsize=12)
        ax.set_ylabel('Primärenergiefaktor (-)', fontweight='bold')
        ax.set_xlabel('Varianten', fontweight='bold')
        
        # Rotate labels if needed
        if len(names) > 3:
            ax.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, pe_factor in zip(bars, pe_factors):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                   f'{pe_factor:.2f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        # Improve grid and styling
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_axisbelow(True)
        
        self.pe_figure.tight_layout()
        self.pe_canvas.draw()
        
    def update_network_chart(self):
        """Update network statistics chart with enhanced layout for larger space."""
        self.network_figure.clear()
        
        if not self.variant_data:
            return
            
        # Extract network metrics
        names = [self.get_clean_variant_name(v.get('name', f'Variante {i+1}')) for i, v in enumerate(self.variant_data)]
        verteilverluste = [v.get('Verteilverluste', 0) for v in self.variant_data]
        anzahl_gebaeude = [v.get('Anzahl_Gebäude', 0) for v in self.variant_data]
        trassenlaenge = [v.get('Trassenlänge', 0) for v in self.variant_data]
        
        # Check if we have meaningful data
        if all(v == 0 for v in verteilverluste + anzahl_gebaeude + trassenlaenge):
            # Show placeholder if no real data available
            ax = self.network_figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Netzstatistiken\n(Daten werden aus Projekten geladen...)', 
                   ha='center', va='center', transform=ax.transAxes,
                   fontsize=14, style='italic', color='#666',
                   bbox=dict(boxstyle="round,pad=0.5", facecolor='lightgray', alpha=0.5))
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
        else:
            # Create subplots for different network metrics (side by side for better space utilization)
            fig = self.network_figure
            
            # Create three subplots horizontally
            ax1 = fig.add_subplot(131)  # Verteilverluste
            ax2 = fig.add_subplot(132)  # Anzahl Gebäude  
            ax3 = fig.add_subplot(133)  # Trassenlänge
            
            # Verteilverluste chart
            if any(v > 0 for v in verteilverluste):
                bars1 = ax1.bar(names, verteilverluste, color='#e74c3c', alpha=0.8, edgecolor='#c0392b')
                ax1.set_title('Verteilverluste', fontweight='bold', fontsize=12)
                ax1.set_ylabel('Verluste (%)', fontweight='bold')
                
                # Add value labels
                for bar, value in zip(bars1, verteilverluste):
                    if value > 0:
                        height = bar.get_height()
                        ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                               f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
            else:
                ax1.text(0.5, 0.5, 'Keine\nDaten', ha='center', va='center', 
                        transform=ax1.transAxes, fontsize=10, style='italic', color='#999')
                ax1.set_title('Verteilverluste', fontweight='bold', fontsize=12)
                
            # Anzahl Gebäude chart  
            if any(v > 0 for v in anzahl_gebaeude):
                bars2 = ax2.bar(names, anzahl_gebaeude, color='#3498db', alpha=0.8, edgecolor='#2980b9')
                ax2.set_title('Anzahl Gebäude', fontweight='bold', fontsize=12)
                ax2.set_ylabel('Anzahl', fontweight='bold')
                
                # Add value labels
                for bar, value in zip(bars2, anzahl_gebaeude):
                    if value > 0:
                        height = bar.get_height()
                        ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                               f'{int(value)}', ha='center', va='bottom', fontweight='bold')
            else:
                ax2.text(0.5, 0.5, 'Keine\nDaten', ha='center', va='center',
                        transform=ax2.transAxes, fontsize=10, style='italic', color='#999')
                ax2.set_title('Anzahl Gebäude', fontweight='bold', fontsize=12)
                
            # Trassenlänge chart
            if any(v > 0 for v in trassenlaenge):
                bars3 = ax3.bar(names, trassenlaenge, color='#f39c12', alpha=0.8, edgecolor='#e67e22')
                ax3.set_title('Trassenlänge', fontweight='bold', fontsize=12) 
                ax3.set_ylabel('Länge (m)', fontweight='bold')
                
                # Add value labels
                for bar, value in zip(bars3, trassenlaenge):
                    if value > 0:
                        height = bar.get_height()
                        ax3.text(bar.get_x() + bar.get_width()/2., height + height*0.02,
                               f'{int(value)}', ha='center', va='bottom', fontweight='bold')
            else:
                ax3.text(0.5, 0.5, 'Keine\nDaten', ha='center', va='center',
                        transform=ax3.transAxes, fontsize=10, style='italic', color='#999')
                ax3.set_title('Trassenlänge', fontweight='bold', fontsize=12)
            
            # Improve layout for all subplots
            for ax in [ax1, ax2, ax3]:
                ax.grid(True, alpha=0.3, axis='y')
                ax.set_axisbelow(True)
                if len(names) > 2:
                    ax.tick_params(axis='x', rotation=45)
        
        self.network_figure.tight_layout(pad=2.0)
        self.network_canvas.draw()
        self.network_canvas.draw()
        
    def clear_dashboard(self):
        """Clear all dashboard content."""
        # Reset KPI widgets
        for widget in self.kpi_widgets.values():
            widget.value_label.setText("--")
            
        # Clear charts
        for figure in [self.cost_figure, self.energy_figure, 
                      self.co2_figure, self.pe_figure, self.network_figure]:
            figure.clear()
            
        for canvas in [self.cost_canvas, self.energy_canvas, 
                      self.co2_canvas, self.pe_canvas, self.network_canvas]:
            canvas.draw()

class ComparisonTab(QWidget):
    """
    Modern comparison tab widget with comprehensive variant analysis.
    """
    
    def __init__(self, folder_manager, data_manager, config_manager, parent=None):
        """
        Initialize modern comparison tab.

        Parameters
        ----------
        folder_manager : FolderManager
            Project folder manager.
        data_manager : DataManager
            Application data manager.
        config_manager : ConfigManager
            Configuration manager.
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self.folder_manager = folder_manager
        self.data_manager = data_manager
        self.config_manager = config_manager
        
        self.variant_data = []
        
        self.initUI()

    def initUI(self):
        """Initialize modern user interface."""
        self.mainLayout = QHBoxLayout(self)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Project Explorer (25% width)
        self.project_explorer = ProjectExplorer(self.folder_manager, self.config_manager)
        self.project_explorer.variants_changed.connect(self.on_variants_changed)
        self.project_explorer.setMaximumWidth(350)
        self.project_explorer.setMinimumWidth(250)
        main_splitter.addWidget(self.project_explorer)
        
        # Right panel: Comparison content (75% width)
        self.comparison_content = self.create_comparison_content()
        main_splitter.addWidget(self.comparison_content)
        
        # Set splitter proportions
        main_splitter.setSizes([250, 750])
        main_splitter.setStretchFactor(0, 0)  # Explorer doesn't stretch
        main_splitter.setStretchFactor(1, 1)  # Content stretches
        
        self.mainLayout.addWidget(main_splitter)

        self.project_explorer.update_selected_variants()  # Initial update to load any pre-selected variants
        
    def create_comparison_content(self):
        """Create the main comparison content area."""
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Create tab widget for different comparison views
        self.tab_widget = QTabWidget()
        
        # Dashboard tab
        self.dashboard = ComparisonDashboard()
        self.tab_widget.addTab(self.dashboard, "📊 Dashboard")
        
        content_layout.addWidget(self.tab_widget)
        
        return content_widget
        
    def on_variants_changed(self, selected_variants):
        """Handle variant selection changes."""
        if not selected_variants:
            self.variant_data = []
            self.dashboard.update_dashboard([])
            return
            
        # Load data for selected variants
        self.load_variant_data(selected_variants)
        
    def load_variant_data(self, selected_variants):
        """Load data for selected variants."""
        self.variant_data = []
        
        for variant_info in selected_variants:
            try:
                variant_path = variant_info['path']
                variant_name = variant_info['name']
                
                # Load results.json
                results_path = os.path.join(variant_path, "Ergebnisse", "Ergebnisse.json")
                with open(results_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Extract results section
                results = data.get('results', {})
                
                # Process data for comparison
                processed_data = self.process_variant_results(results)
                processed_data['name'] = variant_name
                processed_data['path'] = variant_path
                
                # Load additional network data
                network_data = self.load_network_data(variant_path)
                processed_data.update(network_data)
                
                self.variant_data.append(processed_data)
                
            except Exception as e:
                QMessageBox.warning(self, "Ladenfehler", 
                                   f"Fehler beim Laden von {variant_name}:\n{str(e)}")
                
        # Update dashboard
        self.dashboard.update_dashboard(self.variant_data)
        
    def load_network_data(self, variant_path):
        """Instantiate NetworkGenerationData for the variant, load its data, and calculate KPIs."""
        network_data = {
            'Trassenlänge': 0,
            'Verteilverluste': 0,
            'Pumpenenergie': 0,
            'Anzahl_Gebäude': 0
        }
        try:
            config_path = os.path.join(variant_path, "Wärmenetz", "Konfiguration Netzinitialisierung.json")
            if not os.path.exists(config_path):
                print(f"Config not found for {variant_path}")
                return network_data
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            kpi_results = config.get('kpi_results', {})
            network_data['Trassenlänge'] = kpi_results.get('Trassenlänge Wärmenetz [m]', 0)
            network_data['Verteilverluste'] = kpi_results.get('rel. Verteilverluste [%]', 0)
            network_data['Pumpenenergie'] = kpi_results.get('Pumpenstrom [MWh]', 0)
            network_data['Anzahl_Gebäude'] = kpi_results.get('Anzahl angeschlossene Gebäude', 0)
        except Exception as e:
            print(f"Error loading KPIs for {variant_path}: {e}")
        return network_data
        
    def process_variant_results(self, results):
        """Process raw variant results for comparison."""
        try:
            # Handle primärenergiefaktor_Gesamt which can be float or list
            pe_gesamt = results.get('primärenergiefaktor_Gesamt', 0)
            waermemengen = results.get('Wärmemengen', [])
            
            if isinstance(pe_gesamt, (float, int)):
                pe_gesamt = [pe_gesamt] * len(waermemengen) if waermemengen else [pe_gesamt]
            elif isinstance(pe_gesamt, list):
                if len(pe_gesamt) != len(waermemengen) and waermemengen:
                    pe_gesamt = pe_gesamt * len(waermemengen) if pe_gesamt else [0] * len(waermemengen)
                    
            processed_results = {
                "techs": results.get('techs', []),
                "Wärmemengen": [round(w, 2) for w in waermemengen],
                "WGK": [round(w, 2) for w in results.get('WGK', [])],
                "Anteile": [round(a * 100, 2) for a in results.get('Anteile', [])],
                "colors": results.get('colors', []),
                "specific_emissions_L": [round(e, 4) for e in results.get('specific_emissions_L', [])],
                "primärenergie_L": [round(pe / w, 4) if w else 0 for pe, w in zip(pe_gesamt, waermemengen)],
                "Jahreswärmebedarf": round(results.get('Jahreswärmebedarf', 0), 1),
                "Strommenge": round(results.get('Strommenge', 0), 2),
                "Strombedarf": round(results.get('Strombedarf', 0), 2),
                "WGK_Gesamt": round(results.get('WGK_Gesamt', 0), 2),
                "specific_emissions_Gesamt": round(results.get("specific_emissions_Gesamt", 0), 4),
                "primärenergiefaktor_Gesamt": round(results.get("primärenergiefaktor_Gesamt", 0), 4),
            }
            
            return processed_results
            
        except Exception as e:
            raise ValueError(f"Error processing results: {e}")