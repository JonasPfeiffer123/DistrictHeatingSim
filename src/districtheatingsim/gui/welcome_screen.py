"""
Welcome Screen for DistrictHeatingSim Application

This module provides the initial welcome screen that users see when starting
the application. It offers project management functionality including recent
projects, quick actions, and access to documentation.
"""

import os
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
    """A modern toggle switch for theme switching."""
    
    def __init__(self, parent=None):
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
        """Handle mouse press events to toggle the checkbox."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self.isChecked())
        super().mousePressEvent(event)
        
    def paintEvent(self, event):
        """Custom paint event for the toggle switch."""
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
    """Widget for displaying a single recent project with thumbnail and metadata."""
    
    projectSelected = pyqtSignal(str)  # Signal emitted when project is selected
    
    def __init__(self, project_path: str, project_info: Dict):
        super().__init__()
        self.project_path = project_path
        self.project_info = project_info
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the UI for the recent project widget."""
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
            modified_label = QLabel(f"Modified: {self.project_info['last_modified']}")
            # Styling handled by central QSS themes
            layout.addWidget(modified_label)
        
        self.setLayout(layout)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(100)
        self.setMinimumWidth(200)
    
    def _get_display_path(self) -> str:
        """Get the full project path for display."""
        return str(Path(self.project_path))
    
    def mousePressEvent(self, event):
        """Handle mouse press to select project."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.projectSelected.emit(self.project_path)
        super().mousePressEvent(event)


class WelcomeScreen(QWidget):
    """
    Welcome screen widget providing project management and quick actions.
    
    Features:
    - Recent projects display from config manager
    - Quick action buttons (New Project, Open Project)
    - Getting started section with documentation links
    - Clean, modern interface design
    """
    
    projectSelected = pyqtSignal(str)  # Signal when user selects a project
    newProjectRequested = pyqtSignal()  # Signal when user wants to create new project
    themeChangeRequested = pyqtSignal(str)  # Signal when user changes theme (light/dark)
    
    def __init__(self, config_manager=None):
        super().__init__()
        self.config_manager = config_manager  # Use the real config manager for recent projects
        self.recent_projects = []
        self.setup_ui()
        self.load_recent_projects()
    
    def setup_ui(self):
        """Setup the main welcome screen UI with improved layout."""
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
        main_layout.addStretch(0)  # No extra stretch at bottom
        
        self.setLayout(main_layout)
    
    def create_header(self, parent_layout):
        """Create the welcome screen header with improved introduction."""
        header_layout = QVBoxLayout()
        header_layout.setSpacing(15)
        
        # Main title
        title_label = QLabel("Welcome to DistrictHeatingSim")
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Subtitle with better description
        subtitle_label = QLabel("Professional District Heating System Planning and Analysis")
        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        # Add introduction text
        intro_text = QLabel(
            "Plan, analyze and optimize district heating networks with comprehensive tools for "
            "energy system design, economic evaluation, and technical simulation."
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
        self.theme_toggle.setToolTip("Switch between Light and Dark theme")
        self.theme_toggle.toggled.connect(self.on_theme_toggle)
        theme_layout.addWidget(self.theme_toggle)
        
        dark_label = QLabel("🌙")
        dark_label.setFont(QFont("Arial", 14))
        theme_layout.addWidget(dark_label)
        
        header_layout.addLayout(theme_layout)
        
        parent_layout.addLayout(header_layout)
    
    def create_recent_projects_section(self, parent_layout):
        """Create the recent projects section with improved layout."""
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(20)
        
        # Section title with project count
        title_layout = QHBoxLayout()
        recent_title = QLabel("Recent Projects")
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
        """Create the quick actions and getting started section."""
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
        """Create the quick actions section with enhanced buttons."""
        actions_title = QLabel("Quick Actions")
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
            "🆕 Create New Project",
            "Start a new district heating analysis from scratch",
            "primaryButton",
            self.new_project_clicked
        )
        actions_layout.addWidget(new_project_container)
        
        # Open Project button with description  
        open_project_container = self.create_action_button(
            "📂 Open Existing Project",
            "Continue working on a saved project",
            "secondaryButton", 
            self.open_project_clicked
        )
        actions_layout.addWidget(open_project_container)
        
        parent_layout.addLayout(actions_layout)
    
    def create_action_button(self, title: str, description: str, style_class: str, callback):
        """Create an action button with title and description."""
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
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setObjectName("actionDescription")
        layout.addWidget(desc_label)
        
        container.setLayout(layout)
        return container
    
    def create_getting_started(self, parent_layout):
        """Create the getting started section with tutorials and resources."""
        started_title = QLabel("Getting Started")
        started_font = QFont()
        started_font.setPointSize(18)
        started_font.setBold(True)
        started_title.setFont(started_font)
        parent_layout.addWidget(started_title)
        
        # Getting started content
        started_layout = QVBoxLayout()
        started_layout.setSpacing(15)
        
        # Documentation link
        doc_btn = QPushButton("📖 View Documentation")
        doc_btn.setMinimumHeight(40)
        doc_btn.setObjectName("linkButton")
        doc_btn.clicked.connect(self.open_documentation)
        started_layout.addWidget(doc_btn)
        
        # Examples
        examples_btn = QPushButton("🔧 Examples")
        examples_btn.setMinimumHeight(40)
        examples_btn.setObjectName("linkButton")
        examples_btn.clicked.connect(self.open_examples)
        started_layout.addWidget(examples_btn)
        
        # Support
        support_btn = QPushButton("💬 Get Support")
        support_btn.setMinimumHeight(40)
        support_btn.setObjectName("linkButton")
        support_btn.clicked.connect(self.open_support)
        started_layout.addWidget(support_btn)
        
        # Feature overview
        features_frame = QFrame()
        features_frame.setFrameStyle(QFrame.Shape.Box)
        features_frame.setObjectName("featuresFrame")
        
        features_layout = QVBoxLayout()
        features_layout.setContentsMargins(15, 15, 15, 15)
        features_layout.setSpacing(8)
        
        features_title = QLabel("Key Features:")
        features_title_font = QFont()
        features_title_font.setBold(True)
        features_title.setFont(features_title_font)
        features_layout.addWidget(features_title)
        
        features = [
            "🏗️ Network topology generation",
            "🔥 Heat demand calculation", 
            "💰 Economic analysis",
            "⚡ Energy system optimization",
            "📊 Comprehensive reporting"
        ]
        
        for feature in features:
            feature_label = QLabel(feature)
            feature_label.setObjectName("featureItem")
            features_layout.addWidget(feature_label)
        
        features_frame.setLayout(features_layout)
        started_layout.addWidget(features_frame)
        
        parent_layout.addLayout(started_layout)
    
    def load_recent_projects(self):
        """Load and display recent projects from config manager."""
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
        
        # Fallback: scan for projects if no config manager or no recent projects
        if not self.recent_projects:
            self.recent_projects = self.scan_for_projects()
        
        if not self.recent_projects:
            # Show "no projects" message with helpful tips
            no_projects_container = QFrame()
            no_projects_container.setObjectName("noProjectsContainer")
            no_projects_layout = QVBoxLayout()
            no_projects_layout.setContentsMargins(20, 30, 20, 30)
            no_projects_layout.setSpacing(15)
            
            no_projects_label = QLabel("No recent projects found")
            no_projects_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_projects_label.setObjectName("noProjectsTitle")
            font = QFont()
            font.setBold(True)
            font.setPointSize(14)
            no_projects_label.setFont(font)
            no_projects_layout.addWidget(no_projects_label)
            
            tip_label = QLabel("Create a new project or open an existing one to get started!")
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
    
    def scan_for_projects(self) -> List[tuple]:
        """
        Scan for existing project folders.
        
        Returns:
            List of tuples (project_path, project_info)
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
        Check if a folder looks like a DistrictHeatingSim project.
        
        Args:
            folder_path: Path to check
            
        Returns:
            True if it appears to be a project folder
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
        Get information about a project folder.
        
        Args:
            project_path: Path to the project
            
        Returns:
            Dictionary with project information
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
            info['last_modified'] = "Unknown"
            info['last_modified_timestamp'] = 0
        
        return info
    
    def new_project_clicked(self):
        """Handle new project button click."""
        # Start in a sensible default location - check for existing projects first
        start_dir = self.get_default_project_directory()
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select folder for new project",
            start_dir
        )
        
        if folder:
            self.newProjectRequested.emit()
            self.projectSelected.emit(folder)
    
    def open_project_clicked(self):
        """Handle open project button click."""
        # Start in a sensible default location - check for existing projects first
        start_dir = self.get_default_project_directory()
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select project folder",
            start_dir
        )
        
        if folder:
            self.projectSelected.emit(folder)

    def get_default_project_directory(self):
        """Get a sensible default directory for project dialogs."""
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
        """Handle project selection."""
        self.projectSelected.emit(project_path)
    
    def open_documentation(self):
        """Open the documentation website."""
        webbrowser.open("https://districtheatingsim.readthedocs.io/en/latest/")
    
    def open_examples(self):
        """Open example projects folder or documentation."""
        examples_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "examples")
        if os.path.exists(examples_path):
            # Open the examples folder
            os.startfile(examples_path) if os.name == 'nt' else os.system(f'open "{examples_path}"')
        else:
            # Fallback to documentation
            webbrowser.open("https://github.com/JonasPfeiffer123/DistrictHeatingSim/tree/main/examples")
    
    def open_support(self):
        """Open support resources."""
        webbrowser.open("https://github.com/JonasPfeiffer123/DistrictHeatingSim/issues")

    def on_theme_toggle(self, checked):
        """Handle theme toggle switch change."""
        if checked:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()

    def apply_light_theme(self):
        """Request light theme application for entire application."""
        self.themeChangeRequested.emit('light_theme_style_path')

    def apply_dark_theme(self):
        """Request dark theme application for entire application."""
        self.themeChangeRequested.emit('dark_theme_style_path')
    
    def set_current_theme(self, is_dark_theme: bool):
        """Set the toggle switch state based on current theme."""
        # Temporarily disconnect the signal to avoid loops
        self.theme_toggle.toggled.disconnect(self.on_theme_toggle)
        self.theme_toggle.setChecked(is_dark_theme)
        # Reconnect the signal
        self.theme_toggle.toggled.connect(self.on_theme_toggle)
    
    def refresh_recent_projects(self):
        """Refresh the recent projects list."""
        self.load_recent_projects()


def main():
    """Test the welcome screen standalone."""
    app = QApplication([])
    
    welcome = WelcomeScreen()
    welcome.show()
    
    app.exec()


if __name__ == '__main__':
    main()
