import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

# Funktion, um den 3D-Quader zu zeichnen
def plot_3d_cube(ax, x, y, z, dx, dy, dz):
    vertices = [
        [x, y, z],
        [x + dx, y, z],
        [x + dx, y + dy, z],
        [x, y + dy, z],
        [x, y, z + dz],
        [x + dx, y, z + dz],
        [x + dx, y + dy, z + dz],
        [x, y + dy, z + dz]
    ]
    faces = [
        [vertices[j] for j in [0, 1, 2, 3]],
        [vertices[j] for j in [4, 5, 6, 7]],
        [vertices[j] for j in [0, 3, 7, 4]],
        [vertices[j] for j in [1, 2, 6, 5]],
        [vertices[j] for j in [0, 1, 5, 4]],
        [vertices[j] for j in [2, 3, 7, 6]]
    ]
    ax.add_collection3d(Poly3DCollection(faces, 
                                         facecolors='cyan', linewidths=1, edgecolors='r', alpha=.25))

# Initiale Parameter des Quaders
x, y, z = 0, 0, 0
dx, dy, dz = 1, 1, 1

# Funktion, die auf Klick-Events reagiert
def on_click(event):
    global dx, dy
    if event.inaxes == ax2d:
        dx = event.xdata - x
        dy = event.ydata - y
        
        ax2d.clear()
        ax2d.plot([x, x + dx, x + dx, x, x], [y, y, y + dy, y + dy, y], 'b-')
        ax2d.set_xlim(0, 10)
        ax2d.set_ylim(0, 10)

        ax3d.clear()
        plot_3d_cube(ax3d, x, y, z, dx, dy, dz)
        ax3d.set_xlabel('X-Achse')
        ax3d.set_ylabel('Y-Achse')
        ax3d.set_zlabel('Z-Achse')
        ax3d.set_xlim(0, 10)
        ax3d.set_ylim(0, 10)
        ax3d.set_zlim(0, 10)

        plt.draw()

fig = plt.figure(figsize=(10, 5))

# Erstelle das 2D-Diagramm
ax2d = fig.add_subplot(121)
ax2d.plot([x, x + dx, x + dx, x, x], [y, y, y + dy, y + dy, y], 'b-')
ax2d.set_xlim(0, 10)
ax2d.set_ylim(0, 10)
ax2d.set_title('2D-Plot')

# Erstelle das 3D-Diagramm
ax3d = fig.add_subplot(122, projection='3d')
plot_3d_cube(ax3d, x, y, z, dx, dy, dz)
ax3d.set_xlabel('X-Achse')
ax3d.set_ylabel('Y-Achse')
ax3d.set_zlabel('Z-Achse')
ax3d.set_xlim(0, 10)
ax3d.set_ylim(0, 10)
ax3d.set_zlim(0, 10)
ax3d.set_title('3D-Plot')

fig.canvas.mpl_connect('button_press_event', on_click)

plt.show()
