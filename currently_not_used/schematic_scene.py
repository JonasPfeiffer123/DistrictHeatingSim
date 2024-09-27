from PyQt5.QtWidgets import (QGraphicsScene, QGraphicsPathItem, QGraphicsLineItem, QGraphicsItem, QGraphicsView)
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
    GENERATOR_SPACING = 75
    GENERATOR_SPACING_STORAGE = 75
    LINE_Y_OFFSET_GENERATOR = 100
    GENERATOR_X_START = 20
    LINE_THICKNESS = 3
    FLOW_LINE_COLOR = Qt.red
    RETURN_LINE_COLOR = Qt.blue
    TEXT_FONT = QFont("Arial", 11)

    # Define the objects that can be added to the scene
    # Color codes: yellow for Solar, blue for CHP, purple for Storage, green for Consumer
    # Sizes: Solar (circle), CHP (rectangle), Storage (cylinder), Consumer (rectangle)
    OBJECTS = {
        'Solar': {
            'color': QColor('yellow'),
            'geometry': QRectF(-20, -20, 40, 40),  # Circle dimensions for Solar
            'counter': 0  # Counter for Solar
        },
        'CHP': {
            'color': QColor('blue'),
            'geometry': QRectF(-30, -15, 60, 30),  # Rectangle dimensions for CHP
            'counter': 0  # Counter for CHP
        },
        'Storage': {
            'color': QColor('purple'),
            'geometry': QRectF(-20, -40, 40, 80),  # Cylindrical shape for storage
            'counter': 0  # Counter for Storage
        },
        'Consumer': {
            'color': QColor('green'),
            'geometry': QRectF(-30, -15, 60, 30),  # Rectangle dimensions for Consumer
            'counter': 0  # Counter for Consumer
        }
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

        self.create_parallel_lines()

    def update_mouse_label(self, x, y):
        """Update the mouse label when the mouse moves in the scene"""
        self.mouse_label.setText(f"Mouse Coordinates: x = {x:.1f}, y = {y:.1f}")

    def snap_to_grid(self, position):
        """Snap the given position to the nearest grid point"""
        x = round(position.x() / self.GRID_SIZE) * self.GRID_SIZE
        y = round(position.y() / self.GRID_SIZE) * self.GRID_SIZE
        return QPointF(x, y)
    
    def create_parallel_lines(self):
        """Create the parallel Vorlauf (red) and Rücklauf (blue) lines and add labels"""
        scene_width = self.width()

        # Vorlauf (red line)
        self.vorlauf_line = QGraphicsLineItem(self.GENERATOR_X_START, self.generator_y - self.LINE_Y_OFFSET_GENERATOR, scene_width, self.generator_y - self.LINE_Y_OFFSET_GENERATOR)
        self.vorlauf_line.setPen(QPen(self.FLOW_LINE_COLOR, self.LINE_THICKNESS))
        self.addItem(self.vorlauf_line)

        # Rücklauf (blue line)
        self.ruecklauf_line = QGraphicsLineItem(self.GENERATOR_X_START, self.generator_y + self.LINE_Y_OFFSET_GENERATOR, scene_width, self.generator_y + self.LINE_Y_OFFSET_GENERATOR)
        self.ruecklauf_line.setPen(QPen(self.RETURN_LINE_COLOR, self.LINE_THICKNESS))
        self.addItem(self.ruecklauf_line)

        # Add label for Vorlauf (above the red line)
        vorlauf_label = self.addText("Vorlauf", self.TEXT_FONT)
        vorlauf_label.setDefaultTextColor(self.FLOW_LINE_COLOR)
        vorlauf_label.setPos(scene_width / 2 - vorlauf_label.boundingRect().width() / 2, self.generator_y - self.LINE_Y_OFFSET_GENERATOR - 30)

        # Add label for Rücklauf (below the blue line)
        ruecklauf_label = self.addText("Rücklauf", self.TEXT_FONT)
        ruecklauf_label.setDefaultTextColor(self.RETURN_LINE_COLOR)
        ruecklauf_label.setPos(scene_width / 2 - ruecklauf_label.boundingRect().width() / 2, self.generator_y + self.LINE_Y_OFFSET_GENERATOR + 10)


    def add_generator(self, item_name, connect_to_lines=True):
        """Add a generator at a fixed position and optionally connect it to the parallel lines"""
        # Define the generator position based on the current x-position
        position = QPointF(self.GENERATOR_X_START, self.generator_y)
        position = self.snap_to_grid(position)

        item_name = item_name  # Name of the generator (Solar, CHP)
        item_color = self.OBJECTS[item_name]['color']  # Color of the generator
        item_geometry = self.OBJECTS[item_name]['geometry']  # Geometry of the generator
        
        self.OBJECTS[item_name]['counter'] += 1  # Increment the counter for the generator type
        item_counter = self.OBJECTS[item_name]['counter']  # Get the current count for the generator

        # Create and add the generator
        generator = ComponentItem(position, item_name, item_color, item_geometry)
        generator.create_connection_points()  # Create connection points
        self.addItem(generator)

        label_text = f'{item_name} {item_counter}'
        self.add_label(generator, label_text)

        if connect_to_lines:
            self.connect_items_to_lines(generator)

        self.GENERATOR_X_START += self.GENERATOR_SPACING  # Shift position for the next generator
        return generator

    def add_storage(self, position, item_name='Storage'):
        """Helper function to create and add a storage unit with custom geometry"""
        position = self.snap_to_grid(position)

        item_color = self.OBJECTS[item_name]['color']  # Color of the generator
        item_geometry = self.OBJECTS[item_name]['geometry']  # Geometry of the generator

        self.OBJECTS[item_name]['counter'] += 1  # Increment the counter for the storage
        item_counter = self.OBJECTS[item_name]['counter']  # Get the current count for the storage

        storage = ComponentItem(position, item_name, item_color, item_geometry)
        storage.create_connection_points()
        self.addItem(storage)

        label_text = f'{item_name} {item_counter}'
        self.add_label(storage, label_text)

        self.GENERATOR_X_START += self.GENERATOR_SPACING
        return storage

    def add_generator_with_storage(self, generator_type):
        """Add a generator and a storage unit, connecting them and the storage to the consumer"""
        # Add the generator but don't connect it to the lines
        generator = self.add_generator(generator_type, connect_to_lines=False)

        # Add the storage to the right of the generator
        storage_position = QPointF(generator.pos().x() + self.GENERATOR_SPACING_STORAGE, generator.pos().y())  # Fixed distance of 100 units to the right
        storage = self.add_storage(storage_position)

        # Connect generator to storage and storage to consumer
        self.connect_generator_to_storage(generator, storage)

        # Connect the storage to the parallel lines
        self.connect_items_to_lines(storage, is_storage=True)

    def add_consumer_net(self, item_name):
        """Add the consumer (network)"""
        if self.consumer is None:
            position = QPointF(self.GENERATOR_X_START, self.generator_y)  # Vertically center the generator
            position = self.snap_to_grid(position)  # Snap the position to the grid

            item_color = self.OBJECTS[item_name]['color']  # Color of the consumer
            item_geometry = self.OBJECTS[item_name]['geometry']  # Geometry of the consumer

            self.consumer = ComponentItem(position, item_name, item_color, item_geometry)
            self.consumer.create_connection_points()  # Create connection points
            self.addItem(self.consumer)
            self.add_label(self.consumer, item_name)

            # Connect the component to the Vorlauf and Rücklauf lines
            self.connect_items_to_lines(self.consumer)

            # Update the position for the next generator (place it to the right)
            self.GENERATOR_X_START += self.GENERATOR_SPACING  # Shift by a fixed distance

    def add_label(self, item, text):
        """Add a label under the item with a specific text"""
        label = self.addText(text, self.TEXT_FONT)
        label.setPos(item.pos().x(), item.pos().y() + 40)  # Place label under the item
        item.label = label  # Store the label reference in the item

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

    def add_solar(self):
        """Add a Solar generator"""
        self.add_generator('Solar')

    def add_chp(self):
        """Add a CHP generator"""
        self.add_generator('CHP')

    def add_solar_storage(self):
        """Add Solar + Storage"""
        self.add_generator_with_storage('Solar')

    def add_chp_storage(self):
        """Add CHP + Storage"""
        self.add_generator_with_storage('CHP')

    def add_consumer(self):
        self.add_consumer_net('Consumer')

class ComponentItem(QGraphicsItem):
    def __init__(self, position, item_type, color, geometry):
        """Create a general visual representation of a component"""
        super().__init__()

        self.color = color
        self.item_type = item_type
        self.geometry = geometry  # The geometry is now passed in from the scene
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
        painter.setPen(Qt.black)

        if self.item_type == 'Solar':
            # Drawing circular shape for Solar
            painter.drawEllipse(self.boundingRect())
        elif self.item_type == 'CHP':
            # Drawing rectangular shape for CHP
            painter.drawRect(self.boundingRect())
        elif self.item_type == 'Storage':
            # Drawing a cylindrical shape (represented as a tall rectangle for simplicity)
            painter.drawRect(self.boundingRect())
        else:
            # Default drawing for unknown types
            painter.drawRect(self.boundingRect())

    def create_connection_points(self):
        """Create connection points (ports) for the item based on the shape."""
        # Add connection points based on the item type (generator, storage, consumer)
        if self.item_type == 'Storage':
            # Storage has 4 connection points: top-left, top-right, bottom-left, bottom-right
            self.connection_points.append(self.create_connection_point(0, 0.1, 'left', Qt.red))  # Top-left
            self.connection_points.append(self.create_connection_point(1, 0.1, 'right', Qt.red))  # Top-right
            self.connection_points.append(self.create_connection_point(0, 0.9, 'left', Qt.blue))  # Bottom-left
            self.connection_points.append(self.create_connection_point(1, 0.9, 'right', Qt.blue))  # Bottom-right
        else:
            # Generators and consumers have 2 connection points: top (supply) and bottom (return)
            self.connection_points.append(self.create_connection_point(0.5, 0, 'up', Qt.red))  # Top (middle)
            self.connection_points.append(self.create_connection_point(0.5, 1, 'down', Qt.blue))  # Bottom (middle)

    def create_connection_point(self, x_offset, y_offset, direction, color):
        """Helper method to create a connection point at a relative position based on the bounding rectangle."""
        point = ConnectionPoint(self, x_offset, y_offset, direction, color)
        if self.scene():  # Only add if scene exists
            self.scene().addItem(point)
        return point

    def itemChange(self, change, value):
        """Update connected pipes and label when the component moves."""
        if change == QGraphicsItem.ItemPositionChange:
            # Call snap_to_grid on the scene to adjust the movement to the grid
            scene = self.scene()
            if isinstance(scene, SchematicScene):
                value = scene.snap_to_grid(value)  # Snap to grid when moved

            if self.scene():  # Check if the item is in a scene
                for pipe in self.scene().items():
                    if isinstance(pipe, Pipe):
                        pipe.update_path()  # Update the path of all pipes

                if self.label:
                    self.label.setPos(value.x() - 20, value.y() + 40)

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