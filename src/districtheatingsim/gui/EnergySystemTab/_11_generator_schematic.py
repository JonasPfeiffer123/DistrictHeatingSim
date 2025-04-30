"""
Filename: _11_generator_schematic.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2024-09-28
Description: Custom QGraphicsScene and QGraphicsView classes for a generator schematic. Also includes generator schematic items (ComponentItem, Pipe). Complex example for a schematic editor with custom items and connections.
"""

from PyQt5.QtWidgets import (QGraphicsScene, QGraphicsPathItem, QGraphicsLineItem, QGraphicsItem, QGraphicsView, QGraphicsRectItem, QGraphicsTextItem)
from PyQt5.QtCore import Qt, QPointF, QRectF, QLineF, pyqtSignal
from PyQt5.QtGui import QPen, QColor, QPainterPath, QFont, QPainter

class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)  # Use QPainter.Antialiasing instead of QPainterPath
        self.setDragMode(QGraphicsView.ScrollHandDrag)  # Activate scroll drag mode
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)  # Anchor zoom to mouse position

        # Automatically fit the scene when initializing
        self.fit_to_scene()

    def fit_to_scene(self):
        """Fit the entire scene into the view, considering the current window size."""
        # Use fitInView to scale the scene so that it fits entirely within the view
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        """Ensure the scene fits into the view whenever the window is resized."""
        super().resizeEvent(event)
        self.fit_to_scene()  # Fit scene after resizing

    def wheelEvent(self, event):
        """Handle zooming with mouse wheel"""
        zoom_factor = 1.1  # Zoom factor for each wheel step
        if event.angleDelta().y() > 0:  # Zoom in
            self.scale(zoom_factor, zoom_factor)
        else:  # Zoom out
            self.scale(1 / zoom_factor, 1 / zoom_factor)

    def mousePressEvent(self, event):
        """Activate panning on middle mouse button press"""
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)  # Allow panning with middle mouse button
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Deactivate panning when middle mouse button is released"""
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.NoDrag)  # Stop panning
        super().mouseReleaseEvent(event)

class CustomGraphicsScene(QGraphicsScene):
    # Signal to emit mouse position updates
    mouse_position_changed = pyqtSignal(float, float)

    def __init__(self, x, y, width, height, parent=None):
        super().__init__(x, y, width, height, parent)
        self.setSceneRect(x, y, width, height)

    def mouseMoveEvent(self, event):
        """Handle mouse move events in the scene"""
        mouse_position = event.scenePos()  # Get mouse position relative to the scene
        x = mouse_position.x()
        y = mouse_position.y()
        self.mouse_position_changed.emit(x, y)  # Emit signal with the new coordinates
        super().mouseMoveEvent(event)

class SchematicScene(CustomGraphicsScene):
    GRID_SIZE = 1  # Define grid size for snapping
    GENERATOR_SPACING = 100
    GENERATOR_SPACING_STORAGE = 100 # Spacing between generator and storage
    LINE_Y_OFFSET_GENERATOR = 100
    GENERATOR_X_START = 20
    LINE_THICKNESS = 3
    FLOW_LINE_COLOR = Qt.red
    RETURN_LINE_COLOR = Qt.blue
    TEXT_FONT = QFont("Arial", 12, QFont.Bold)

    # Define the objects that can be added to the scene
    # Color codes: yellow for Solar, blue for CHP, purple for Storage, green for Consumer
    # Sizes: Solar (circle), CHP (rectangle), Storage (cylinder), Consumer (rectangle)
    OBJECTS = {
        'Solar': {
            'color': QColor('yellow'),
            'geometry': QRectF(-20, -20, 40, 40),  # Circle dimensions for Solar
            'shape': 'circle',  # Define the shape type
            'counter': 0  # Counter for Solar
        },
        'CHP': {
            'color': QColor('blue'),
            'geometry': QRectF(-30, -15, 60, 30),  # Rectangle dimensions for CHP
            'shape': 'rect',  # Shape as rectangle
            'counter': 0  # Counter for CHP
        },
        'Wood-CHP': {
            'color': QColor('brown'),
            'geometry': QRectF(-30, -20, 60, 40),  # Larger square to differentiate from other CHP
            'shape': 'rect',  # Shape as rectangle
            'counter': 0  # Counter for Wood-CHP
        },
        'Biomass Boiler': {
            'color': QColor('darkgreen'),
            'geometry': QRectF(-25, -20, 50, 40),  # Taller rectangle for biomass boiler
            'shape': 'rect',  # Shape as rectangle
            'counter': 0  # Counter for Biomass Boiler
        },
        'Gas Boiler': {
            'color': QColor('gray'),
            'geometry': QRectF(-25, -25, 50, 50),  # Narrower and shorter rectangle for gas boiler
            'shape': 'rect',  # Shape as rectangle
            'counter': 0  # Counter for Gas Boiler
        },
        'Power-to-Heat': {
            'color': QColor('orange'),
            'geometry': QRectF(-25, -25, 50, 50),  # Square to represent power-to-heat
            'shape': 'rect',  # Shape as rectangle
            'counter': 0  # Counter for Power-to-Heat
        },
        'Geothermal Heat Pump': {
            'color': QColor('blueviolet'),
            'geometry': QRectF(-25, -25, 50, 50),  # Square to represent geothermal heat pump
            'shape': 'rect',  # Shape as rectangle
            'counter': 0  # Counter for Geothermal Heat Pump
        },
        'River Heat Pump': {
            'color': QColor('deepskyblue'),
            'geometry': QRectF(-25, -25, 50, 50),  # Larger square for river heat pump
            'shape': 'rect',  # Shape as rectangle
            'counter': 0  # Counter for River Heat Pump
        },
        'Waste Heat Pump': {
            'color': QColor('orange'),
            'geometry': QRectF(-25, -25, 50, 50),  # Rectangle for waste heat pump
            'shape': 'rect',  # Shape as rectangle
            'counter': 0  # Counter for Waste Heat Pump
        },
        'Aqva Heat Pump': {
            'color': QColor('cyan'),
            'geometry': QRectF(-25, -25, 50, 50),  # Square for Aqva heat pump
            'shape': 'rect',  # Shape as rectangle
            'counter': 0  # Counter for Aqva Heat Pump
        },
        'Storage': {
            'color': QColor('purple'),
            'geometry': QRectF(-20, -40, 40, 80),  # Cylindrical shape for storage
            'shape': 'rect',  # Use rectangle to represent a cylinder
            'counter': 0  # Counter for Storage
        },
        'Consumer': {
            'color': QColor('green'),
            'geometry': QRectF(-30, -15, 60, 30),  # Rectangle dimensions for Consumer
            'shape': 'rect',  # Shape as rectangle
            'counter': 0  # Counter for Consumer
        },
        'Seasonal Thermal Storage': {
            'color': QColor('darkorange'),
            'geometry': QRectF(-30, -20, 60, 40),  # Rectangle dimensions for seasonal storage
            'shape': 'trapezoid',  # Shape as trapezoid to symbolize an earth basin
            'counter': 0  # Counter for seasonal storage
        },
    }

    def __init__(self, width, height, parent=None):
        super().__init__(0, 0, width, height, parent)
        self.setSceneRect(0, 0, width, height)
        self.setBackgroundBrush(QColor(240, 240, 240))  # Light gray background

        self.generators = []
        self.storage_units = []
        self.pipes = []
        self.consumer = None

        # Separate counters for each generator type
        self.solar_counter = 0
        self.chp_counter = 0
        self.storage_counter = 0

        self.generator_y = height / 2

        self.selected_item = None  # Track selected item

        # Add the consumer first but don't draw the parallel lines yet
        self.add_consumer_net('Consumer', connect_to_lines=False)

        # Parallel lines are initialized without extending them (no generators yet)
        self.vorlauf_line = None
        self.ruecklauf_line = None

        #self.consumer.create_parallel_lines()

        # Verbinde das selectionChanged-Signal mit einer Methode zum Aktualisieren
        self.selectionChanged.connect(self.update_selected_item)

    def update_scene_size(self):
        """
        Updates the scene size dynamically based on the positions of all items.
        """
        if not self.items():
            return
        
        # Berechne die Bounding Box für alle Objekte in der Szene
        bounding_rect = self.itemsBoundingRect()

        # Erweiterung der Bounding Box, falls nötig (z.B. Puffer für die Ränder)
        margin = 25  # Margin in Pixeln, um etwas Platz um die Objekte zu lassen
        bounding_rect.adjust(-margin, -margin, margin, margin)

        # Setze die neue Szenegröße basierend auf der Bounding Box
        self.setSceneRect(bounding_rect)

    def update_selected_item(self):
        """Aktualisiert das ausgewählte Objekt, wenn sich die Auswahl in der Szene ändert."""
        # Hole alle ausgewählten Objekte (es könnte theoretisch mehr als eines sein)
        selected_items = self.selectedItems()

        if selected_items:
            # Falls es ein ausgewähltes Objekt gibt, speichere das erste davon
            self.selected_item = selected_items[0]  # Speichere das ausgewählte Objekt
        else:
            # Falls kein Objekt ausgewählt ist, setze selected_item auf None
            self.selected_item = None

    def snap_to_grid(self, position):
        """Snap the given position to the nearest grid point"""
        x = round(position.x() / self.GRID_SIZE) * self.GRID_SIZE
        y = round(position.y() / self.GRID_SIZE) * self.GRID_SIZE
        return QPointF(x, y)
    
    def create_parallel_lines(self):
        """Create or update the parallel Vorlauf (red) and Rücklauf (blue) lines and add labels"""
        # Entferne bestehende Leitungen und Labels
        if hasattr(self, 'vorlauf_line') and self.vorlauf_line:
            self.removeItem(self.vorlauf_line)
        if hasattr(self, 'ruecklauf_line') and self.ruecklauf_line:
            self.removeItem(self.ruecklauf_line)

        # Entferne bestehende Labels
        for item in self.items():
            if isinstance(item, QGraphicsTextItem) and item.toPlainText() in ["Vorlauf", "Rücklauf"]:
                self.removeItem(item)

        # Überprüfe, ob Erzeuger oder Speicher vorhanden sind
        generators_and_storage = [item for item in self.items() if isinstance(item, ComponentItem) and item != self.consumer]
        
        if not generators_and_storage:
            # Keine Erzeuger oder Speicher vorhanden, also keine Leitungen zeichnen
            return

        # Finde die Position des letzten Erzeugers oder Speichers
        last_item_x = max(item.pos().x() for item in generators_and_storage)

        # Zeichne die Leitungen vom Consumer bis zum letzten Erzeuger oder Speicher
        start_x = self.consumer.pos().x()
        end_x = last_item_x

        # Zeichne Vorlauf (rote Linie)
        self.vorlauf_line = QGraphicsLineItem(start_x, self.generator_y - self.LINE_Y_OFFSET_GENERATOR, end_x, self.generator_y - self.LINE_Y_OFFSET_GENERATOR)
        self.vorlauf_line.setPen(QPen(self.FLOW_LINE_COLOR, self.LINE_THICKNESS))
        self.addItem(self.vorlauf_line)

        # Zeichne Rücklauf (blaue Linie)
        self.ruecklauf_line = QGraphicsLineItem(start_x, self.generator_y + self.LINE_Y_OFFSET_GENERATOR, end_x, self.generator_y + self.LINE_Y_OFFSET_GENERATOR)
        self.ruecklauf_line.setPen(QPen(self.RETURN_LINE_COLOR, self.LINE_THICKNESS))
        self.addItem(self.ruecklauf_line)

        # Füge Labels hinzu, die zwischen Consumer und letztem Erzeuger/Speicher zentriert sind
        self.update_parallel_labels(start_x, end_x)

        # Nach dem Erstellen der Leitungen aktualisiere die Pipes, die mit den Leitungen verbunden sind
        self.update_pipes_connected_to_lines()

        # Consumer mit den Leitungen verbinden, falls das noch nicht geschehen ist
        self.connect_items_to_lines(self.consumer)

    def update_parallel_labels(self, start_x, end_x):
        """Update the labels for the Vorlauf and Rücklauf lines dynamically."""
        # Berechne die Mitte zwischen Start und Ende
        scene_width = end_x - start_x
        center_x = start_x + scene_width / 2

        # Füge Label für Vorlauf (oberhalb der roten Linie) hinzu
        vorlauf_label = self.addText("Vorlauf", self.TEXT_FONT)
        vorlauf_label.setDefaultTextColor(self.FLOW_LINE_COLOR)
        vorlauf_label.setPos(center_x - vorlauf_label.boundingRect().width() / 2, self.generator_y - self.LINE_Y_OFFSET_GENERATOR - 30)

        # Füge Label für Rücklauf (unterhalb der blauen Linie) hinzu
        ruecklauf_label = self.addText("Rücklauf", self.TEXT_FONT)
        ruecklauf_label.setDefaultTextColor(self.RETURN_LINE_COLOR)
        ruecklauf_label.setPos(center_x - ruecklauf_label.boundingRect().width() / 2, self.generator_y + self.LINE_Y_OFFSET_GENERATOR + 10)

    def update_pipes_connected_to_lines(self):
        """Update pipes that are connected to the parallel lines."""
        for pipe in self.pipes:
            if not isinstance(pipe.point1, ConnectionPoint) or not isinstance(pipe.point2, ConnectionPoint):
                # Pipe ist mit einer Linie verbunden
                pipe.update_path()

    def add_generator(self, item_type, item_name, connect_to_lines=True):
        """Add a generator at a fixed position and optionally connect it to the parallel lines"""
        """
        item_name: Type of the generator (e.g., 'CHP', 'Solar')
        name: Unique name for the generator (e.g., 'BHKW_1')
        """
        # Define the generator position based on the current x-position
        position = QPointF(self.GENERATOR_X_START, self.generator_y)
        position = self.snap_to_grid(position)

        item_color = self.OBJECTS[item_type]['color']  # Color of the generator
        item_geometry = self.OBJECTS[item_type]['geometry']  # Geometry of the generator
        
        self.OBJECTS[item_type]['counter'] += 1  # Increment the counter for the generator type
        item_counter = self.OBJECTS[item_type]['counter']  # Get the current count for the generator

        # Create and add the generator
        generator = ComponentItem(position, item_type, item_name, item_color, item_geometry, self.FLOW_LINE_COLOR, self.RETURN_LINE_COLOR)
        generator.create_connection_points()  # Create connection points
        self.addItem(generator)

        self.update_label(generator, item_name)

        # Aktualisiere die parallelen Leitungen
        self.create_parallel_lines()

        if connect_to_lines:
            self.connect_items_to_lines(generator)

        self.GENERATOR_X_START += self.GENERATOR_SPACING  # Shift position for the next generator

        # Update the scene size after adding the generator
        self.update_scene_size()

        return generator

    def add_storage(self, position, item_type='Storage', item_name='Speicher'):
        """Helper function to create and add a storage unit with custom geometry"""
        position = self.snap_to_grid(position)

        item_color = self.OBJECTS[item_type]['color']  # Color of the storage
        item_geometry = self.OBJECTS[item_type]['geometry']  # Geometry of the storage

        self.OBJECTS[item_type]['counter'] += 1  # Increment the counter for the storage
        item_counter = self.OBJECTS[item_type]['counter']  # Get the current count for the storage

        storage = ComponentItem(position, item_type, item_name, item_color, item_geometry, self.FLOW_LINE_COLOR, self.RETURN_LINE_COLOR)
        storage.create_connection_points()
        self.addItem(storage)

        label_text = f'{item_name} {item_counter}'  # Add the counter to the label
        self.update_label(storage, label_text)

        self.GENERATOR_X_START += self.GENERATOR_SPACING

        # Update the scene size after adding the generator
        self.update_scene_size()

        return storage

    def add_generator_with_storage(self, item_name, name):
        """Add a generator and a storage unit, connecting them and the storage to the consumer"""
        # Add the generator but don't connect it to the lines
        generator = self.add_generator(item_name, name, connect_to_lines=False)

        # Add the storage to the right of the generator
        storage_position = QPointF(generator.pos().x() + self.GENERATOR_SPACING_STORAGE, generator.pos().y())  # Fixed distance of 100 units to the right
        storage = self.add_storage(storage_position)

        # Connect generator to storage and storage to consumer
        self.connect_generator_to_storage(generator, storage)

        # Aktualisiere die parallelen Leitungen
        self.create_parallel_lines()

        # Connect the storage to the parallel lines
        self.connect_items_to_lines(storage, is_storage=True)

        # Update the scene size after adding the generator
        self.update_scene_size()

        return generator

    def add_consumer_net(self, item_type, item_name="Wärmenetz", connect_to_lines=False):
        """Add the consumer (network)"""
        if self.consumer is None:
            position = QPointF(self.GENERATOR_X_START, self.generator_y)  # Place consumer at Start_x
            position = self.snap_to_grid(position)  # Snap the position to the grid

            item_color = self.OBJECTS[item_type]['color']  # Color of the consumer
            item_geometry = self.OBJECTS[item_type]['geometry']  # Geometry of the consumer

            self.consumer = ComponentItem(position, item_type, item_name, item_color, item_geometry, self.FLOW_LINE_COLOR, self.RETURN_LINE_COLOR)
            self.consumer.create_connection_points()  # Create connection points
            self.addItem(self.consumer)
            self.update_label(self.consumer, item_name)  # Update the label for the consumer

            # Deaktiviere Bewegung und Auswahl für den Consumer
            self.consumer.setFlag(QGraphicsItem.ItemIsMovable, False)
            self.consumer.setFlag(QGraphicsItem.ItemIsSelectable, False)

            # Aktualisiere die Position für den nächsten Generator (platziere ihn rechts)
            self.GENERATOR_X_START += self.GENERATOR_SPACING  # Verschiebe um eine feste Distanz

            # Update the scene size after adding the generator
            self.update_scene_size()

    def add_seasonal_storage(self, item_type='Saisonaler Wärmespeicher', item_name='Speicher', connect_to_lines=True):
        """Add a seasonal storage unit at a fixed position and optionally connect it to the parallel lines."""
        # Define the storage position based on the current x-position
        position = QPointF(self.GENERATOR_X_START, self.generator_y)
        position = self.snap_to_grid(position)

        item_color = self.OBJECTS[item_type]['color']  # Color of the storage
        item_geometry = self.OBJECTS[item_type]['geometry']  # Geometry of the storage
        
        self.OBJECTS[item_type]['counter'] += 1  # Increment the counter for the storage type
        item_counter = self.OBJECTS[item_type]['counter']  # Get the current count for the storage

        # Create and add the storage
        storage = ComponentItem(position, item_type, item_name, item_color, item_geometry, self.FLOW_LINE_COLOR, self.RETURN_LINE_COLOR)
        storage.create_connection_points()  # Create connection points
        self.addItem(storage)

        self.update_label(storage, f"{item_name} {item_counter}")

        # Update the parallel lines
        self.create_parallel_lines()

        if connect_to_lines:
            self.connect_items_to_lines(storage)

        self.GENERATOR_X_START += self.GENERATOR_SPACING  # Shift position for the next component

        # Update the scene size after adding the storage
        self.update_scene_size()

        return storage
    
    def update_label(self, item, new_text):
        """Update the label of a given item with new text."""
        if item.label:
            # Update the text of the label
            item.label.setPlainText(new_text)
        else:
            # If no label exists, create a new one
            label = self.addText(new_text, self.TEXT_FONT)
            item.label = label  # Link the label to the item

        # Ensure the label is always on top
        item.label.setZValue(10)  # Make sure label is displayed above everything else

        # Add padding for better visibility
        padding = 10  

        # Update the position of the label based on the item type
        if item.item_type == 'Storage':
            # Position the label above the storage item
            label_x = item.pos().x() - item.boundingRect().width() / 2 + padding
            label_y = item.pos().y() - item.boundingRect().height() - padding
        else:
            # Position the label below the item for other types
            label_x = item.pos().x() - item.boundingRect().width() / 2 + padding
            label_y = item.pos().y() + item.boundingRect().height() + padding

        item.label.setPos(label_x, label_y)  # Set the label position manually

        # Get the updated bounding rect of the label
        label_rect = item.label.boundingRect()

        # Calculate the absolute scene position for the background rect
        scene_label_pos = item.label.scenePos()
        background_rect_x = scene_label_pos.x() - padding / 2
        background_rect_y = scene_label_pos.y() - padding / 2
        background_rect_width = label_rect.width() + padding
        background_rect_height = label_rect.height() + padding

        # Optionally: Set background color for the label (pseudo background using rect)
        if hasattr(item, 'background_rect') and item.background_rect:  # Check if background_rect exists
            item.background_rect.setRect(background_rect_x, background_rect_y, background_rect_width, background_rect_height)
        else:
            # Erstelle ein halbtransparentes Rechteck um das Label
            background_rect = QGraphicsRectItem(background_rect_x, background_rect_y, background_rect_width, background_rect_height)
            background_color = QColor(255, 255, 255, 150)  # Weiß mit Alpha-Wert von 150 für halbe Transparenz
            background_rect.setBrush(background_color)  # Setze die halbtransparente Farbe
            background_rect.setPen(QPen(Qt.NoPen))  # Keine Umrandung für den Hintergrund
            background_rect.setZValue(9)  # Leicht unterhalb des Labels
            self.addItem(background_rect)  # Add the background to the scene
            item.background_rect = background_rect  # Link it to the item
            item.label.setParentItem(background_rect)  # Ensure the label is on top of the background

    def connect_generator_to_storage(self, generator, storage):
        """Connect two items (generator, storage, or consumer) using their connection points"""
        if generator.connection_points and storage.connection_points:
            # Erzeuger oder Verbraucher: Verwende rechte Verbindung für Vorlauf und linke für Rücklauf
            point1_supply = generator.connection_points[0]  # 0: Obere Verbindung für Vorlauf
            point1_return = generator.connection_points[1]  # 1: Untere Verbindung für Rücklauf

            # Speicher: Obere Verbindung für Vorlauf und untere für Rücklauf
            point2_supply = storage.connection_points[0]  # Obere linke Verbindung für Vorlauf zum Speicher
            point2_return = storage.connection_points[2]  # Untere linke Verbindung für Rücklauf zum Speicher

            # Red supply pipe (Vorlauf)
            supply_pipe = Pipe(point1_supply, point2_supply, self.FLOW_LINE_COLOR, self.LINE_THICKNESS)
            self.addItem(supply_pipe)
            self.pipes.append(supply_pipe)

            # Blue return pipe (Rücklauf)
            return_pipe = Pipe(point1_return, point2_return, self.RETURN_LINE_COLOR, self.LINE_THICKNESS)
            self.addItem(return_pipe)
            self.pipes.append(return_pipe)
        else:
            print("Error: One or both items have no connection points.")
            
    def connect_items_to_lines(self, component, is_storage=False):
        """Connect a component to the parallel Vorlauf (red) and Rücklauf (blue) lines"""

        if not hasattr(self, 'vorlauf_line') or not self.vorlauf_line:
            return  # Leitungen existieren nicht, können keine Verbindung herstellen

        # Vorlauf connection (red line) to top of component
        if not is_storage:
            # Connect the top (supply) of the generator to the Vorlauf (red line)
            point_supply = component.connection_points[0]  # Top connection point
            line_point_vorlauf = QPointF(point_supply.scenePos().x(), self.vorlauf_line.line().y1())  # Connect vertically to Vorlauf line
            supply_pipe = Pipe(point_supply, line_point_vorlauf, self.FLOW_LINE_COLOR, self.LINE_THICKNESS)
            self.addItem(supply_pipe)
            self.pipes.append(supply_pipe)

            # Rücklauf connection (blue line) to bottom of component
            # Storage items should always connect to Rücklauf line even if is_storage is True
            point_return = component.connection_points[1]  # Bottom connection point
            line_point_ruecklauf = QPointF(point_return.scenePos().x(), self.ruecklauf_line.line().y1())  # Connect vertically to Rücklauf line
            return_pipe = Pipe(point_return, line_point_ruecklauf, self.RETURN_LINE_COLOR, self.LINE_THICKNESS)
            self.addItem(return_pipe)
            self.pipes.append(return_pipe)

        if is_storage:
            # For storage, connect both the top (Vorlauf) and bottom (Rücklauf) to the parallel lines
            point_storage_supply = component.connection_points[1]  # Additional top supply point for storage
            line_point_vorlauf_storage = QPointF(point_storage_supply.scenePos().x(), self.vorlauf_line.line().y1())  # Connect vertically to Vorlauf line
            storage_supply_pipe = Pipe(point_storage_supply, line_point_vorlauf_storage, self.FLOW_LINE_COLOR, self.LINE_THICKNESS)
            self.addItem(storage_supply_pipe)
            self.pipes.append(storage_supply_pipe) 

            # For storage, connect both the top (Vorlauf) and bottom (Rücklauf) to the parallel lines
            point_storage_supply = component.connection_points[3]  # Additional top supply point for storage
            line_point_vorlauf_storage = QPointF(point_storage_supply.scenePos().x(), self.ruecklauf_line.line().y1())  # Connect vertically to Vorlauf line
            storage_supply_pipe = Pipe(point_storage_supply, line_point_vorlauf_storage, self.RETURN_LINE_COLOR, self.LINE_THICKNESS)
            self.addItem(storage_supply_pipe)
            self.pipes.append(storage_supply_pipe)

    def add_component(self, item_name, name, storage=False):
        """
        Add a component (generator, storage, or consumer) to the scene.
        item_name: Type of the component (e.g., 'CHP', 'Solar')
        name: Unique name for the component (e.g., 'BHKW_1')
        storage: If True, add a storage with the component
        """
        if storage:
            return self.add_generator_with_storage(item_name, name)
        else:
            if item_name == 'Consumer':
                return self.add_consumer_net(name)
            if item_name == 'Saisonaler Wärmespeicher':
                return self.add_seasonal_storage(item_name, name)
            else:
                return self.add_generator(item_name, name)

    def delete_selected(self):
        """Delete the selected component, ensuring that connected generators and storage are deleted together."""
        if self.selected_item and isinstance(self.selected_item, ComponentItem) and self.selected_item != self.consumer:
            # Erstelle eine Liste mit Generatoren und zugehörigen Speichern
            generators_with_storage = []
            generators_without_storage = []

            # Durchlaufe alle Items in der Szene und sortiere sie in die entsprechenden Listen
            for item in self.items():
                if isinstance(item, ComponentItem) and item.item_type != 'Storage' and item != self.consumer:
                    linked_storage = self.find_linked_storage(item)
                    if linked_storage:
                        generators_with_storage.append((item, linked_storage))
                    else:
                        generators_without_storage.append(item)

            # Prüfe, ob der ausgewählte Item ein Speicher ist und lösche auch den zugehörigen Generator
            if self.selected_item.item_type == 'Storage':
                # Finde den Generator, der mit dem Speicher verbunden ist
                linked_generator = self.find_linked_generator(self.selected_item)
                if linked_generator:
                    generators_with_storage = [(gen, storage) for gen, storage in generators_with_storage if gen != linked_generator and storage != self.selected_item]
                else:
                    generators_with_storage = [(gen, storage) for gen, storage in generators_with_storage if storage != self.selected_item]
            else:
                # Der ausgewählte Item ist ein Generator, lösche auch den zugehörigen Speicher
                linked_storage = self.find_linked_storage(self.selected_item)
                if linked_storage:
                    generators_with_storage = [(gen, storage) for gen, storage in generators_with_storage if gen != self.selected_item and storage != linked_storage]
                else:
                    generators_without_storage = [item for item in generators_without_storage if item != self.selected_item]

            # Lösche alles außer dem Consumer
            self.delete_all()

            # Füge die Generatoren und Speicher in der ursprünglichen Reihenfolge wieder hinzu
            for generator, storage in sorted(generators_with_storage, key=lambda i: i[0].pos().x()):
                print(generator)
                self.add_generator_with_storage(generator.item_type, generator.item_name)

            for generator in sorted(generators_without_storage, key=lambda i: i.pos().x()):
                self.add_generator(generator.item_type, generator.item_name)

            # Setze das ausgewählte Item zurück
            self.selected_item = None

            self.update_scene_size()

    def delete_all(self):
        """Delete all components, pipes, and reset all counters except for the consumer and its connections."""
        # Collect all items except for the consumer and the pipes connected to the consumer
        items_to_delete = [
            item for item in self.items() 
            if isinstance(item, (ComponentItem, Pipe)) 
            and (item != self.consumer and not self.is_connected_to_consumer(item))
        ]
        
        # Delete all selected items
        for item in items_to_delete:
            if isinstance(item, ComponentItem):
                if item.label:
                    self.removeItem(item.label)  # Delete the label
                if hasattr(item, 'background_rect') and item.background_rect:
                    self.removeItem(item.background_rect)  # Delete the background rect
            self.removeItem(item)

        # Reset the counters for all object types
        for key in self.OBJECTS.keys():
            self.OBJECTS[key]['counter'] = 0  # Reset counters

        # Keep the consumer and its connections intact, and reset the x position for generators
        if self.consumer:
            self.GENERATOR_X_START = self.consumer.pos().x() + self.GENERATOR_SPACING  # Start next to the consumer

        # Da keine Erzeuger mehr vorhanden sind, entferne die parallelen Leitungen
        self.create_parallel_lines()
        
        self.selected_item = None  # Reset the selected item

        self.update_scene_size()

    def is_connected_to_consumer(self, item):
        """Helper method to check if a pipe is connected to the consumer."""
        if isinstance(item, Pipe):
            point1_connected = isinstance(item.point1, ConnectionPoint) and item.point1.parent == self.consumer
            point2_connected = isinstance(item.point2, ConnectionPoint) and item.point2.parent == self.consumer
            return point1_connected or point2_connected
        return False
    
    def find_linked_generator(self, storage):
        """Find the generator linked to the given storage unit."""
        for pipe in self.items():
            if isinstance(pipe, Pipe):
                # Prüfen, ob pipe.point1 ein ConnectionPoint ist und mit dem Speicher verbunden ist
                if isinstance(pipe.point1, ConnectionPoint) and pipe.point1.parent == storage:
                    if isinstance(pipe.point2, ConnectionPoint) and isinstance(pipe.point2.parent, ComponentItem):
                        return pipe.point2.parent  # Rückgabe des Generators
                # Prüfen, ob pipe.point2 ein ConnectionPoint ist und mit dem Speicher verbunden ist
                if isinstance(pipe.point2, ConnectionPoint) and pipe.point2.parent == storage:
                    if isinstance(pipe.point1, ConnectionPoint) and isinstance(pipe.point1.parent, ComponentItem):
                        return pipe.point1.parent  # Rückgabe des Generators
        return None
    
    def find_linked_storage(self, generator):
        """Find the storage unit linked to the given generator."""
        for pipe in self.items():
            if isinstance(pipe, Pipe):
                # Prüfen, ob pipe.point1 ein ConnectionPoint ist und mit dem Generator verbunden ist
                if isinstance(pipe.point1, ConnectionPoint) and pipe.point1.parent == generator:
                    if isinstance(pipe.point2, ConnectionPoint) and pipe.point2.parent.item_type == 'Storage':
                        return pipe.point2.parent  # Rückgabe des Speichers
                # Prüfen, ob pipe.point2 ein ConnectionPoint ist und mit dem Generator verbunden ist
                if isinstance(pipe.point2, ConnectionPoint) and pipe.point2.parent == generator:
                    if isinstance(pipe.point1, ConnectionPoint) and pipe.point1.parent.item_type == 'Storage':
                        return pipe.point1.parent  # Rückgabe des Speichers
        return None

class ComponentItem(QGraphicsItem):
    def __init__(self, position, item_type, item_name, color, geometry, flow_line_color=Qt.red, return_line_color=Qt.blue):
        """Create a general visual representation of a component"""
        super().__init__()

        self.item_name = item_name
        self.color = color
        self.item_type = item_type
        self.geometry = geometry  # The geometry is now passed in from the scene
        self.flow_line_color = flow_line_color
        self.return_line_color = return_line_color
        self.shape = SchematicScene.OBJECTS[item_type]['shape']  # Get the shape type from OBJECTS
        self.setPos(position)

        # Set the flags for interaction
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.ItemIsSelectable)

        # Placeholder for connection points (ports)
        self.connection_points = []
        self.label = None  # Placeholder for label reference

    def boundingRect(self):
        """Return the predefined geometry passed in during creation"""
        return self.geometry

    def paint(self, painter, option, widget=None):
        """Draw the item with the specified shape and color."""
        painter.setBrush(self.color)

        # Überprüfe, ob das Objekt ausgewählt ist
        if self.isSelected():
            # Wenn das Objekt ausgewählt ist, zeichne den Rahmen dicker und in einer auffälligen Farbe
            painter.setPen(QPen(Qt.red, 3))  # Roter, dicker Rahmen für ausgewähltes Objekt
        else:
            # Normaler schwarzer Rahmen für nicht ausgewählte Objekte
            painter.setPen(QPen(Qt.black, 1))  # Dünner schwarzer Rahmen

        # Drawing based on the shape type
        if self.shape == 'circle':
            painter.drawEllipse(self.boundingRect())
        elif self.shape == 'rect':
            painter.drawRect(self.boundingRect())
        elif self.shape == 'ellipse':
            painter.drawEllipse(self.boundingRect())  # You can add more custom shapes here
        else:
            painter.drawRect(self.boundingRect())  # Fallback: draw rectangle by default

    def create_connection_points(self):
        """Create connection points (ports) for the item based on the shape."""
        # Add connection points based on the item type (generator, storage, consumer)
        if self.item_type == 'Storage':
            # Storage has 4 connection points: top-left, top-right, bottom-left, bottom-right
            self.connection_points.append(self.create_connection_point(0, 0.1, 'left', self.flow_line_color))  # Top-left
            self.connection_points.append(self.create_connection_point(1, 0.1, 'right', self.flow_line_color))  # Top-right
            self.connection_points.append(self.create_connection_point(0, 0.9, 'left', self.return_line_color))  # Bottom-left
            self.connection_points.append(self.create_connection_point(1, 0.9, 'right', self.return_line_color))  # Bottom-right
        else:
            # Generators and consumers have 2 connection points: top (supply) and bottom (return)
            self.connection_points.append(self.create_connection_point(0.5, 0, 'up', self.flow_line_color))  # Top (middle)
            self.connection_points.append(self.create_connection_point(0.5, 1, 'down', self.return_line_color))  # Bottom (middle)

    def create_connection_point(self, x_offset, y_offset, direction, color):
        """Helper method to create a connection point at a relative position based on the bounding rectangle."""
        point = ConnectionPoint(self, x_offset, y_offset, direction, color)
        if self.scene():  # Only add if scene exists
            self.scene().addItem(point)
        return point

    def itemChange(self, change, value):
        """Update connected pipes, label, and background when the component moves."""
        if change == QGraphicsItem.ItemPositionChange:
            # Call snap_to_grid on the scene to adjust the movement to the grid
            scene = self.scene()
            if isinstance(scene, SchematicScene):
                value = scene.snap_to_grid(value)  # Snap to grid when moved

            if self.scene():  # Check if the item is in a scene
                # Aktualisiere alle Pipes, die mit dem Item verbunden sind
                for pipe in self.scene().items():
                    if isinstance(pipe, Pipe):
                        pipe.update_path()  # Update the path of all pipes

                # Aktualisiere die Position des Labels
                if self.label:
                    padding = 10  # Padding für die Positionierung

                    if self.item_type == 'Storage':
                        # Label über dem Speicher platzieren
                        label_x = value.x() - self.boundingRect().width() / 2 + padding
                        label_y = value.y() - self.boundingRect().height() - padding
                    else:
                        # Label unter anderen Komponenten platzieren
                        label_x = value.x() - self.boundingRect().width() / 2 + padding
                        label_y = value.y() + self.boundingRect().height() + padding

                    # Setze die Position des Labels
                    self.label.setPos(label_x, label_y)

                    # Aktualisiere die Position und Größe der Hintergrundbox (background_rect)
                    if hasattr(self, 'background_rect') and self.background_rect:
                        label_rect = self.label.boundingRect()

                        # Berechne die Szene-Position des Labels
                        scene_label_pos = self.label.scenePos()
                        background_rect_x = scene_label_pos.x() - padding / 2
                        background_rect_y = scene_label_pos.y() - padding / 2
                        background_rect_width = label_rect.width() + padding
                        background_rect_height = label_rect.height() + padding

                        # Setze die neue Position und Größe des Hintergrundrechtecks
                        self.background_rect.setRect(background_rect_x, background_rect_y, background_rect_width, background_rect_height)

                # Aktualisiere die Position der Verbindungs-Punkte
                for point in self.connection_points:
                    point.update_position()

        return super().itemChange(change, value)

class ConnectionPoint(QGraphicsLineItem):
    def __init__(self, parent, x_offset, y_offset, direction, color):
        """Create a connection point as a short line extending from the parent item."""
        self.parent = parent
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.direction = direction  # Direction of the line extension (up, down, left, right)
        self.color = color

        # Create the line as a QGraphicsLineItem
        super().__init__()
        self.setParentItem(parent)  # Attach to the parent item (Generator, Storage, etc.)

        # Set the pen for the line (its color and thickness)
        self.setPen(QPen(self.color, 3))

        # Position the connection point and create its extension line
        self.update_position()

    def update_position(self):
        """Update the position of the connection point relative to the parent item and its extension line"""
        bounding_rect = self.parentItem().boundingRect()

        # Calculate the new position relative to the parent's local coordinate system
        local_x = bounding_rect.x() + bounding_rect.width() * self.x_offset
        local_y = bounding_rect.y() + bounding_rect.height() * self.y_offset

        # Set the start of the line to the position of this connection point
        line_start = QPointF(local_x, local_y)

        # Determine the direction of the line and set the end point
        if self.direction == 'up':
            line_end = QPointF(line_start.x(), line_start.y() - 10)
        elif self.direction == 'down':
            line_end = QPointF(line_start.x(), line_start.y() + 10)
        elif self.direction == 'left':
            line_end = QPointF(line_start.x() - 10, line_start.y())
        elif self.direction == 'right':
            line_end = QPointF(line_start.x() + 10, line_start.y())

        # Set the line's geometry based on the calculated start and end points
        self.setLine(QLineF(line_start, line_end))

    def get_end_point(self):
        """Return the end point of the connection line (for pipe connections)."""
        return self.parentItem().mapToScene(self.line().p2())

class Pipe(QGraphicsPathItem):
    def __init__(self, point1, point2, color, line_thickness):
        """Create a flexible pipe (supply/return) between component and parallel lines"""
        super().__init__()
        self.point1 = point1
        self.point2 = point2
        self.color = color  # Color for the pipe (red for supply, blue for return)
        self.line_thickness = line_thickness  # Thickness of the pipe

        # Set the pen for the pipe, making it thicker and colored
        self.setPen(QPen(self.color, self.line_thickness))  # Set line color and thickness

        # Now it's safe to call update_path since the pipe is in the scene
        self.update_path()

    def update_path(self):
        """Update the pipe path to connect components to parallel lines with vertical and horizontal segments only."""
        if isinstance(self.point1, ConnectionPoint):
            start_pos = self.point1.get_end_point()  # Start position is the connection point of the component
        else:
            start_pos = self.point1

        if isinstance(self.point2, ConnectionPoint):
            end_pos = self.point2.get_end_point()  # End position is the connection point of the component
        else:
            end_pos = self.point2  # End position is the point on the parallel line (Vorlauf or Rücklauf)

        # Create a path from start to end with right-angled turns (horizontal and vertical segments only)
        self.path = QPainterPath(start_pos)

        # Check for collisions in the vertical and horizontal segments
        intermediate_point = QPointF(start_pos.x(), end_pos.y())

        # Adjust path to avoid collisions
        if self.check_collision(intermediate_point):
            # If a collision is detected in the vertical segment, adjust the path
            adjusted_point = QPointF(start_pos.x() + 20, start_pos.y())  # Move right or left to avoid collision
            self.path.lineTo(adjusted_point)
            intermediate_point = QPointF(adjusted_point.x(), end_pos.y())  # Recalculate intermediate point

        # Add vertical movement to the level of the parallel line
        self.path.lineTo(intermediate_point)

        # Add horizontal movement along the parallel line
        self.path.lineTo(end_pos)

        # Apply the updated path to the Pipe
        self.setPath(self.path)

    def check_collision(self, point):
        """Check if the given point collides with any item (generator, consumer, storage)"""
        # Only check for collisions if the pipe is part of a scene
        if self.scene() is None:
            return False

        # Loop through the items in the scene and check for collisions
        for item in self.scene().items():
            if isinstance(item, ComponentItem):
                if item.contains(item.mapFromScene(point)):
                    return True
        return False