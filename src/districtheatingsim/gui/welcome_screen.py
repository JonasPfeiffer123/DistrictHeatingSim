"""Welcome Screen Module
=====================

Initial welcome screen with project management, recent projects, and quick actions.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import os
import sys
import json
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                             QPushButton, QLabel, QFrame, QScrollArea, 
                             QFileDialog, QMessageBox, QApplication, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QRect, QEasingCurve
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPainter, QColor, QPen


class ThemeToggleSwitch(QCheckBox):
    """
    Modern toggle switch for theme switching with animated handle.

    .. note::
       Renders custom painted toggle with sun/moon icons for light/dark theme indication.
    """
    
    def __init__(self, parent=None):
        """
        Initialize toggle switch with custom styling and animation.

        :param parent: Parent widget, defaults to None
        :type parent: QWidget, optional
        """
        super().__init__(parent)
        self.setFixedSize(60, 20)
        self.setStyleSheet("""
            QCheckBox {
                background: transparent;
                spacing: 0px;
            }
            QCheckBox::indicator {
                width: 0px;
                height: 0px;
            }
        """)
        
        # Animation for smooth toggle
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
    def mousePressEvent(self, event):
        """
        Handle mouse press events to toggle the checkbox state.

        :param event: Mouse event
        :type event: QMouseEvent
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self.isChecked())
        super().mousePressEvent(event)
        
    def paintEvent(self, event):
        """
        Custom paint event for rendering the toggle switch with animated handle.

        :param event: Paint event
        :type event: QPaintEvent

        .. note::
           Draws track background, circular handle, and sun/moon icons based on theme state.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Track (background)
        track_color = QColor("#4a90e2" if self.isChecked() else "#ccc")
        painter.setBrush(track_color)
        painter.setPen(Qt.PenStyle.NoPen)
        track_rect = QRect(0, 0, self.width(), self.height())
        painter.drawRoundedRect(track_rect, self.height()//2, self.height()//2)
        
        # Handle (circle)
        handle_radius = self.height() - 4
        handle_x = self.width() - handle_radius - 2 if self.isChecked() else 2
        handle_y = 2
        
        painter.setBrush(QColor("white"))
        painter.drawEllipse(handle_x, handle_y, handle_radius, handle_radius)
        
        # Icons
        icon_size = 12
        icon_y = (self.height() - icon_size) // 2
        
        # Sun icon (left side) - visible when light mode (unchecked)
        if not self.isChecked():
            painter.setPen(QPen(QColor("#666"), 2))
            sun_x = 8
            sun_center_x = sun_x + icon_size // 2
            sun_center_y = icon_y + icon_size // 2
            painter.drawEllipse(sun_center_x - 3, sun_center_y - 3, 6, 6)
            # Sun rays
            painter.drawLine(sun_center_x, sun_center_y - 8, sun_center_x, sun_center_y - 6)
            painter.drawLine(sun_center_x, sun_center_y + 6, sun_center_x, sun_center_y + 8)
            painter.drawLine(sun_center_x - 8, sun_center_y, sun_center_x - 6, sun_center_y)
            painter.drawLine(sun_center_x + 6, sun_center_y, sun_center_x + 8, sun_center_y)
        
        # Moon icon (right side) - visible when dark mode (checked)
        else:
            painter.setPen(QPen(QColor("white"), 2))
            painter.setBrush(QColor("white"))
            moon_x = self.width() - 20
            moon_center_x = moon_x + icon_size // 2
            moon_center_y = icon_y + icon_size // 2
            painter.drawEllipse(moon_center_x - 4, moon_center_y - 4, 8, 8)
            painter.setBrush(track_color)
            painter.drawEllipse(moon_center_x - 1, moon_center_y - 4, 6, 6)


class RecentProjectWidget(QFrame):
    """
    Widget for displaying a single recent project with thumbnail and metadata.

    :signal projectSelected: Emitted when project is selected (str: project_path)

    .. note::
       Displays project name, path, and last modification date in clickable frame.
    """
    
    projectSelected = pyqtSignal(str)  # Signal emitted when project is selected
    
    def __init__(self, project_path: str, project_info: Dict):
        """
        Initialize recent project widget.

        :param project_path: Path to the project folder
        :type project_path: str
        :param project_info: Dictionary with project metadata
        :type project_info: Dict
        """
        super().__init__()
        self.project_path = project_path
        self.project_info = project_info
        self.setup_ui()
    
    def setup_ui(self):
        """
        Setup the UI for the recent project widget with name, path, and modification date.

        .. note::
           Creates clickable frame with project metadata display and hover cursor.
        """
        self.setFrameStyle(QFrame.Shape.Box)
        # Styling is handled by central QSS themes
        
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Project name
        name_label = QLabel(self.project_info.get('name', os.path.basename(self.project_path)))
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(11)
        name_label.setFont(name_font)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        # Project path (shortened)
        path_label = QLabel(self._get_display_path())
        # Styling handled by central QSS themes
        path_label.setWordWrap(True)
        layout.addWidget(path_label)
        
        # Last modified
        if 'last_modified' in self.project_info:
            modified_label = QLabel(f"Geändert: {self.project_info['last_modified']}")
            # Styling handled by central QSS themes
            layout.addWidget(modified_label)
        
        self.setLayout(layout)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)
        self.setMinimumWidth(200)
    
    def _get_display_path(self) -> str:
        """
        Get the full project path for display in widget.

        :return: Formatted project path string
        :rtype: str
        """
        return str(Path(self.project_path))
    
    def mousePressEvent(self, event):
        """
        Handle mouse press to emit project selection signal.

        :param event: Mouse event
        :type event: QMouseEvent
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.projectSelected.emit(self.project_path)
        super().mousePressEvent(event)


class WelcomeScreen(QWidget):
    """
    Welcome screen widget providing project management and quick actions.

    :signal projectSelected: Emitted when user selects a project (str: path)
    :signal newProjectRequested: Emitted when user wants to create new project
    :signal themeChangeRequested: Emitted when user changes theme (str: theme_key)

    .. note::
       Features recent projects display, quick action buttons, documentation links, and clean modern interface.
    """
    
    projectSelected = pyqtSignal(str)  # Signal when user selects a project
    newProjectRequested = pyqtSignal()  # Signal when user wants to create new project
    themeChangeRequested = pyqtSignal(str)  # Signal when user changes theme (light/dark)
    
    def __init__(self, config_manager=None):
        """
        Initialize welcome screen with config manager for recent projects.

        :param config_manager: Configuration manager instance, defaults to None
        :type config_manager: ConfigManager, optional
        """
        super().__init__()
        self.config_manager = config_manager  # Use the real config manager for recent projects
        self.recent_projects = []
        self.setup_ui()
        self.load_recent_projects()
    
    def setup_ui(self):
        """
        Setup the main welcome screen UI with header, content sections, and footer.

        .. note::
           Creates three-section layout: header with title/theme toggle, content with recent projects and quick actions, funding footer.
        """
        self.setWindowTitle("DistrictHeatingSim - Welcome")
        self.setMinimumSize(1000, 700)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(50, 40, 50, 40)
        main_layout.setSpacing(40)
        
        # Header
        self.create_header(main_layout)
        
        # Content area with better proportions
        content_layout = QHBoxLayout()
        content_layout.setSpacing(50)
        
        # Left side - Recent Projects (60% width)
        self.create_recent_projects_section(content_layout)
        
        # Right side - Quick Actions and Getting Started (40% width)
        self.create_actions_section(content_layout)
        
        main_layout.addLayout(content_layout, 1)  # Stretch factor 1
        
        # Funding/Project Information Footer
        self.create_funding_footer(main_layout)
        
        main_layout.addStretch(0)  # No extra stretch at bottom
        
        self.setLayout(main_layout)
    
    def create_header(self, parent_layout):
        """
        Create the welcome screen header with title, subtitle, and theme switcher.

        :param parent_layout: Parent layout to add header to
        :type parent_layout: QVBoxLayout

        .. note::
           Includes main title, subtitle, introductory text, and theme toggle switch positioned top-right.
        """
        header_layout = QVBoxLayout()
        header_layout.setSpacing(15)
        
        # Main title
        title_label = QLabel("Willkommen bei DistrictHeatingSim")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Subtitle with better description
        subtitle_label = QLabel("Professionelle Fernwärmesystem-Planung und -Analyse")
        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        # Add introduction text
        intro_text = QLabel(
            "Planen, analysieren und optimieren Sie Fernwärmenetze mit umfassenden Werkzeugen für "
            "Energiesystem-Design, wirtschaftliche Bewertung und technische Simulation."
        )
        intro_text.setWordWrap(True)
        intro_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro_text.setMaximumWidth(600)
        intro_text.setContentsMargins(50, 10, 50, 10)
        intro_font = QFont()
        intro_font.setPointSize(11)
        intro_text.setFont(intro_font)
        
        # Center the intro text
        intro_container = QHBoxLayout()
        intro_container.addStretch()
        intro_container.addWidget(intro_text)
        intro_container.addStretch()
        header_layout.addLayout(intro_container)
        
        # Theme switcher (moved to top-right corner)
        theme_layout = QHBoxLayout()
        theme_layout.addStretch()  # Push theme switcher to the right
        
        theme_label = QLabel("☀️")
        theme_label.setFont(QFont("Arial", 14))
        theme_layout.addWidget(theme_label)
        
        # Modern toggle switch
        self.theme_toggle = ThemeToggleSwitch()
        self.theme_toggle.setToolTip("Zwischen hellem und dunklem Design wechseln")
        self.theme_toggle.toggled.connect(self.on_theme_toggle)
        theme_layout.addWidget(self.theme_toggle)
        
        dark_label = QLabel("🌙")
        dark_label.setFont(QFont("Arial", 14))
        theme_layout.addWidget(dark_label)
        
        header_layout.addLayout(theme_layout)
        
        parent_layout.addLayout(header_layout)
    
    def create_recent_projects_section(self, parent_layout):
        """
        Create the recent projects section with scrollable project list.

        :param parent_layout: Parent layout to add section to
        :type parent_layout: QHBoxLayout

        .. note::
           Creates scrollable area with project widgets and project count badge.
        """
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)
        
        # Section title with project count
        title_layout = QHBoxLayout()
        recent_title = QLabel("Aktuelle Projekte")
        recent_font = QFont()
        recent_font.setPointSize(18)
        recent_font.setBold(True)
        recent_title.setFont(recent_font)
        title_layout.addWidget(recent_title)
        title_layout.addStretch()
        
        # Project count badge
        self.project_count_label = QLabel("0")
        self.project_count_label.setObjectName("projectCountBadge")
        self.project_count_label.setFixedSize(25, 25)
        self.project_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(self.project_count_label)
        
        left_layout.addLayout(title_layout)
        
        # Scroll area for projects
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setMinimumHeight(400)
        scroll_area.setObjectName("projectScrollArea")
        
        # Container for project widgets
        self.projects_container = QWidget()
        self.projects_layout = QVBoxLayout()
        self.projects_layout.setContentsMargins(5, 5, 5, 5)
        self.projects_layout.setSpacing(12)
        self.projects_container.setLayout(self.projects_layout)
        
        scroll_area.setWidget(self.projects_container)
        left_layout.addWidget(scroll_area)
        
        left_widget.setLayout(left_layout)
        left_widget.setMinimumWidth(500)  # Increased width
        parent_layout.addWidget(left_widget, 3)  # 60% of space
    
    def create_actions_section(self, parent_layout):
        """
        Create the quick actions and getting started section in right panel.

        :param parent_layout: Parent layout to add section to
        :type parent_layout: QHBoxLayout

        .. note::
           Combines quick action buttons and getting started resources.
        """
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(35)
        
        # Quick Actions
        self.create_quick_actions(right_layout)
        
        # Getting Started
        self.create_getting_started(right_layout)
        
        right_layout.addStretch()
        right_widget.setLayout(right_layout)
        right_widget.setMinimumWidth(350)  # Increased width
        parent_layout.addWidget(right_widget, 2)  # 40% of space
    
    def create_quick_actions(self, parent_layout):
        """
        Create the quick actions section with New Project and Open Project buttons.

        :param parent_layout: Parent layout to add quick actions to
        :type parent_layout: QVBoxLayout

        .. note::
           Creates styled action button containers with callbacks.
        """
        actions_title = QLabel("Schnellaktionen")
        actions_font = QFont()
        actions_font.setPointSize(18)
        actions_font.setBold(True)
        actions_title.setFont(actions_font)
        parent_layout.addWidget(actions_title)
        
        # Action buttons with descriptions
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(20)
        
        # New Project button with description
        new_project_container = self.create_action_button(
            "🆕 Neues Projekt erstellen",
            "primaryButton",
            self.new_project_clicked
        )
        actions_layout.addWidget(new_project_container)
        
        # Open Project button with description  
        open_project_container = self.create_action_button(
            "📂 Bestehendes Projekt öffnen",
            "secondaryButton", 
            self.open_project_clicked
        )
        actions_layout.addWidget(open_project_container)
        
        parent_layout.addLayout(actions_layout)
    
    def create_action_button(self, title: str, style_class: str, callback):
        """
        Create an action button with title and callback inside styled container.

        :param title: Button text
        :type title: str
        :param style_class: CSS class for button styling
        :type style_class: str
        :param callback: Function to call on button click
        :return: Framed button container
        :rtype: QFrame
        """
        container = QFrame()
        container.setFrameStyle(QFrame.Shape.Box)
        container.setObjectName("actionButtonContainer")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # Main button
        button = QPushButton(title)
        button.setMinimumHeight(45)
        button.setObjectName(style_class)
        button.clicked.connect(callback)
        layout.addWidget(button)
        
        container.setLayout(layout)
        return container
    
    def create_getting_started(self, parent_layout):
        """
        Create the getting started section with documentation, examples, and support links.

        :param parent_layout: Parent layout to add section to
        :type parent_layout: QVBoxLayout

        .. note::
           Provides quick access to documentation, example projects, and GitHub support.
        """
        started_title = QLabel("Schnellstart")
        started_font = QFont()
        started_font.setPointSize(18)
        started_font.setBold(True)
        started_title.setFont(started_font)
        parent_layout.addWidget(started_title)
        
        # Getting started content
        started_layout = QVBoxLayout()
        started_layout.setSpacing(15)
        
        # Documentation link
        doc_btn = QPushButton("📖 Dokumentation öffnen")
        doc_btn.setMinimumHeight(40)
        doc_btn.setObjectName("linkButton")
        doc_btn.clicked.connect(self.open_documentation)
        started_layout.addWidget(doc_btn)
        
        # Examples
        examples_btn = QPushButton("🔧 Beispiele")
        examples_btn.setMinimumHeight(40)
        examples_btn.setObjectName("linkButton")
        examples_btn.clicked.connect(self.open_examples)
        started_layout.addWidget(examples_btn)
        
        # Support
        support_btn = QPushButton("💬 Unterstützung")
        support_btn.setMinimumHeight(40)
        support_btn.setObjectName("linkButton")
        support_btn.clicked.connect(self.open_support)
        started_layout.addWidget(support_btn)
        
        parent_layout.addLayout(started_layout)
    
    def create_funding_footer(self, parent_layout):
        """
        Create the funding notice footer with logo and project information.

        :param parent_layout: Parent layout to add footer to
        :type parent_layout: QVBoxLayout

        .. note::
           Displays Saxony funding logo, project title, and developer information.
        """
        footer_container = QFrame()
        footer_container.setFrameStyle(QFrame.Shape.Box)
        footer_container.setObjectName("fundingFooter")
        
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(20, 15, 20, 15)
        footer_layout.setSpacing(20)
        
        # Funding logo
        try:
            from districtheatingsim.utilities.utilities import get_resource_path
            
            # Logo is in src/districtheatingsim/images/
            logo_path = get_resource_path(self.config_manager.get_relative_path('funding_logo_path'))
            
            if os.path.exists(logo_path):
                logo_label = QLabel()
                pixmap = QPixmap(logo_path)
                # Scale the logo to a reasonable size (max height 80px)
                scaled_pixmap = pixmap.scaledToHeight(80, Qt.TransformationMode.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
                logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                footer_layout.addWidget(logo_label)
            else:
                print(f"Funding logo not found at: {logo_path}")
        except Exception as e:
            print(f"Could not load funding logo: {e}")
        
        # Project information text
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        # Title
        project_title = QLabel("Gefördert durch das Sächsische Staatsministerium für Wissenschaft, Kultur und Tourismus")
        project_title.setWordWrap(True)
        project_title.setObjectName("fundingTitle")
        project_font = QFont()
        project_font.setBold(True)
        project_font.setPointSize(10)
        project_title.setFont(project_font)
        info_layout.addWidget(project_title)
        
        # Project name and details
        project_details = QLabel(
            "Projekt: SMWK-NEUES TG70 – Entwicklung und Erprobung von Methoden und Werkzeugen zur Konzeptionierung nachhaltiger Wärmenetze"
        )
        project_details.setWordWrap(True)
        project_details.setObjectName("fundingDetails")
        details_font = QFont()
        details_font.setPointSize(9)
        project_details.setFont(details_font)
        info_layout.addWidget(project_details)
        
        # Developer info
        developer_info = QLabel("Entwickelt von Dipl.-Ing. (FH) Jonas Pfeiffer, Hochschule Zittau/Görlitz")
        developer_info.setObjectName("fundingDetails")
        developer_info.setFont(details_font)
        info_layout.addWidget(developer_info)
        
        footer_layout.addLayout(info_layout, 1)  # Let text take remaining space
        
        footer_container.setLayout(footer_layout)
        parent_layout.addWidget(footer_container)
    
    def load_recent_projects(self):
        """
        Load and display recent projects from config manager with fallback to example project.

        .. note::
           Clears existing widgets, loads from config manager, adds Görlitz example if no projects found.
        """
        # Clear existing projects
        while self.projects_layout.count():
            child = self.projects_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Get recent projects from config manager if available
        self.recent_projects = []
        if self.config_manager:
            try:
                recent_project_paths = self.config_manager.get_recent_projects()
                for project_path in recent_project_paths:
                    if os.path.exists(project_path):
                        project_info = self.get_project_info(project_path)
                        self.recent_projects.append((project_path, project_info))
            except Exception as e:
                print(f"Could not load recent projects: {e}")
        
        # Always add the bundled example project (Görlitz) if no recent projects exist
        if not self.recent_projects:
            example_project = self.get_bundled_example_project()
            if example_project:
                self.recent_projects.append(example_project)
        
        if not self.recent_projects:
            # Show "no projects" message with helpful tips
            no_projects_container = QFrame()
            no_projects_container.setObjectName("noProjectsContainer")
            no_projects_layout = QVBoxLayout()
            no_projects_layout.setContentsMargins(20, 30, 20, 30)
            no_projects_layout.setSpacing(15)
            
            no_projects_label = QLabel("Keine aktuellen Projekte gefunden")
            no_projects_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_projects_label.setObjectName("noProjectsTitle")
            font = QFont()
            font.setBold(True)
            font.setPointSize(14)
            no_projects_label.setFont(font)
            no_projects_layout.addWidget(no_projects_label)
            
            tip_label = QLabel("Erstellen Sie ein neues Projekt oder öffnen Sie ein bestehendes, um zu beginnen!")
            tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tip_label.setWordWrap(True)
            tip_label.setObjectName("noProjectsTip")
            no_projects_layout.addWidget(tip_label)
            
            no_projects_container.setLayout(no_projects_layout)
            self.projects_layout.addWidget(no_projects_container)
            
            # Update project count
            if hasattr(self, 'project_count_label'):
                self.project_count_label.setText("0")
        else:
            # Add recent project widgets
            for project_path, project_info in self.recent_projects[:10]:  # Show max 10 recent
                project_widget = RecentProjectWidget(project_path, project_info)
                project_widget.projectSelected.connect(self.project_selected)
                self.projects_layout.addWidget(project_widget)
            
            # Update project count
            if hasattr(self, 'project_count_label'):
                self.project_count_label.setText(str(min(len(self.recent_projects), 10)))
        
        self.projects_layout.addStretch()
    
    def get_bundled_example_project(self) -> Optional[tuple]:
        """
        Get the bundled Görlitz example project path.
        
        This method locates the Görlitz example project that is bundled with
        the application in the project_data directory. Works both in development
        and in frozen (PyInstaller) deployments.
        
        Returns:
            Optional[tuple]: (project_path, project_info) if found, None otherwise
        """
        try:
            # Import utilities to get resource path
            from districtheatingsim.utilities.utilities import get_resource_path
            
            # Try to get the standard folder path from config
            standard_project_path = None
            
            if self.config_manager:
                try:
                    # Get from file_paths.json configuration
                    standard_relative = self.config_manager.get_relative_path('standard_folder_path')
                    # Convert to absolute path using resource path resolution
                    standard_project_path = get_resource_path(standard_relative)
                except Exception as e:
                    print(f"Could not get standard project path from config: {e}")
            
            # Fallback: try common locations
            if not standard_project_path or not os.path.exists(standard_project_path):
                # Get application base directory
                if getattr(sys, 'frozen', False):
                    # Running as compiled executable
                    base_path = sys._MEIPASS
                    # Also check directory where exe is located (for user-accessible folders)
                    exe_dir = os.path.dirname(sys.executable)
                else:
                    # Running in development
                    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    exe_dir = base_path
                
                # Try different possible locations
                possible_paths = [
                    # First check next to exe (user-accessible location)
                    os.path.join(exe_dir, 'project_data', 'Görlitz'),
                    # Then check in _MEIPASS (internal location)
                    os.path.join(base_path, 'project_data', 'Görlitz'),
                    os.path.join(base_path, 'districtheatingsim', 'project_data', 'Görlitz'),
                    os.path.join(os.path.dirname(base_path), 'project_data', 'Görlitz'),
                ]
                
                for path in possible_paths:
                    if os.path.exists(path) and os.path.isdir(path):
                        standard_project_path = path
                        break
            
            # Check if we found a valid example project
            if standard_project_path and os.path.exists(standard_project_path):
                project_info = self.get_project_info(standard_project_path)
                project_info['name'] = '📚 Görlitz Beispielprojekt'  # Add icon to indicate it's the example
                return (standard_project_path, project_info)
            
        except Exception as e:
            print(f"Error locating bundled example project: {e}")
        
        return None
    
    def scan_for_projects(self) -> List[tuple]:
        """
        Scan common directories for existing project folders.

        :return: List of tuples (project_path, project_info) sorted by modification time
        :rtype: List[tuple]

        .. note::
           Scans Documents, current directory, and application directory for valid project structures.
        """
        projects = []
        
        # Default locations to scan
        scan_paths = [
            os.path.expanduser("~/Documents"),
            os.getcwd(),
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ]
        
        for scan_path in scan_paths:
            if os.path.exists(scan_path):
                try:
                    for item in os.listdir(scan_path):
                        item_path = os.path.join(scan_path, item)
                        if os.path.isdir(item_path):
                            # Check if it looks like a project folder
                            if self.is_project_folder(item_path):
                                project_info = self.get_project_info(item_path)
                                projects.append((item_path, project_info))
                except (OSError, PermissionError):
                    continue
        
        # Sort by last modified time (newest first)
        projects.sort(key=lambda x: x[1].get('last_modified_timestamp', 0), reverse=True)
        
        return projects
    
    def is_project_folder(self, folder_path: str) -> bool:
        """
        Check if a folder contains typical DistrictHeatingSim project structure.

        :param folder_path: Path to check
        :type folder_path: str
        :return: True if appears to be a project folder
        :rtype: bool

        .. note::
           Looks for indicator folders like 'Eingangsdaten allgemein', 'Definition Quartier IST', 'Variante 1'.
        """
        # Look for typical project structure indicators
        indicators = [
            "Eingangsdaten allgemein",
            "Definition Quartier IST", 
            "Variante 1",
            "Gebäudedaten",
            "Wärmenetz"
        ]
        
        try:
            contents = os.listdir(folder_path)
            return any(indicator in contents for indicator in indicators)
        except (OSError, PermissionError):
            return False
    
    def get_project_info(self, project_path: str) -> Dict:
        """
        Get metadata information about a project folder.

        :param project_path: Path to the project
        :type project_path: str
        :return: Dictionary with name, path, last_modified, last_modified_timestamp
        :rtype: Dict

        .. note::
           Extracts folder name and modification timestamp for display and sorting.
        """
        info = {
            'name': os.path.basename(project_path),
            'path': project_path
        }
        
        try:
            # Get folder modification time
            stat = os.stat(project_path)
            info['last_modified_timestamp'] = stat.st_mtime
            info['last_modified'] = datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
        except (OSError, PermissionError):
            info['last_modified'] = "Unbekannt"
            info['last_modified_timestamp'] = 0
        
        return info
    
    def new_project_clicked(self):
        """
        Handle new project button click by emitting newProjectRequested signal.

        .. note::
           Main window handles complete workflow including folder selection and project creation.
        """
        # Simply emit the signal - the main window will handle the complete workflow
        # including folder selection, project name input, and project creation
        self.newProjectRequested.emit()
    
    def open_project_clicked(self):
        """
        Handle open project button click with file dialog for folder selection.

        .. note::
           Opens file dialog starting in default project directory, emits projectSelected signal.
        """
        # Start in a sensible default location - check for existing projects first
        start_dir = self.get_default_project_directory()
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Projektordner auswählen",
            start_dir
        )
        
        if folder:
            self.projectSelected.emit(folder)

    def get_default_project_directory(self):
        """
        Get a sensible default directory for project dialogs.

        :return: Path to default directory (most recent project parent or Documents folder)
        :rtype: str

        .. note::
           Prefers parent directory of most recent project, falls back to ~/Documents.
        """
        # Try to use the most recent project's parent directory
        if self.config_manager:
            try:
                recent_projects = self.config_manager.get_recent_projects()
                if recent_projects:
                    # Use the parent directory of the most recent project
                    most_recent = recent_projects[0]
                    return os.path.dirname(most_recent)
            except:
                pass
        
        # Fallback to Documents folder
        return os.path.expanduser("~/Documents")
    
    def project_selected(self, project_path: str):
        """
        Handle project selection by emitting projectSelected signal.

        :param project_path: Path to selected project
        :type project_path: str
        """
        self.projectSelected.emit(project_path)
    
    def open_documentation(self):
        """
        Open the ReadTheDocs documentation website in default browser.

        .. note::
           Opens https://districtheatingsim.readthedocs.io/en/latest/
        """
        webbrowser.open("https://districtheatingsim.readthedocs.io/en/latest/")
    
    def open_examples(self):
        """
        Open example projects folder or GitHub examples page.

        .. note::
           Opens local examples folder if exists, otherwise opens GitHub examples page.
        """
        examples_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "examples")
        if os.path.exists(examples_path):
            # Open the examples folder
            os.startfile(examples_path) if os.name == 'nt' else os.system(f'open "{examples_path}"')
        else:
            # Fallback to documentation
            webbrowser.open("https://github.com/JonasPfeiffer123/DistrictHeatingSim/tree/main/examples")
    
    def open_support(self):
        """
        Open GitHub issues page for support and bug reporting.

        .. note::
           Opens https://github.com/JonasPfeiffer123/DistrictHeatingSim/issues
        """
        webbrowser.open("https://github.com/JonasPfeiffer123/DistrictHeatingSim/issues")

    def on_theme_toggle(self, checked):
        """
        Handle theme toggle switch change to apply light or dark theme.

        :param checked: True if dark theme, False if light theme
        :type checked: bool
        """
        if checked:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()

    def apply_light_theme(self):
        """
        Request light theme application for entire application.

        .. note::
           Emits themeChangeRequested signal with 'light_theme_style_path'.
        """
        self.themeChangeRequested.emit('light_theme_style_path')

    def apply_dark_theme(self):
        """
        Request dark theme application for entire application.

        .. note::
           Emits themeChangeRequested signal with 'dark_theme_style_path'.
        """
        self.themeChangeRequested.emit('dark_theme_style_path')
    
    def set_current_theme(self, is_dark_theme: bool):
        """
        Set the toggle switch state based on current theme without triggering signals.

        :param is_dark_theme: True for dark theme, False for light theme
        :type is_dark_theme: bool

        .. note::
           Temporarily disconnects signal to avoid loops when updating toggle state.
        """
        # Temporarily disconnect the signal to avoid loops
        self.theme_toggle.toggled.disconnect(self.on_theme_toggle)
        self.theme_toggle.setChecked(is_dark_theme)
        # Reconnect the signal
        self.theme_toggle.toggled.connect(self.on_theme_toggle)
    
    def refresh_recent_projects(self):
        """
        Refresh the recent projects list by reloading from config manager.

        .. note::
           Calls load_recent_projects() to update the displayed project widgets.
        """
        self.load_recent_projects()


def main():
    """
    Test the welcome screen standalone for development and debugging.

    .. note::
       Creates QApplication and displays WelcomeScreen widget.
    """
    app = QApplication([])
    
    welcome = WelcomeScreen()
    welcome.show()
    
    app.exec()


if __name__ == '__main__':
    main()
