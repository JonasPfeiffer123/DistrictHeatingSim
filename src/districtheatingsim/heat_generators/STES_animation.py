"""
DATE: 04.04.2025
AUTHOR: Dipl-Ing. (FH) Jonas Pfeiffer
FILENAME: STES_animation.py

DESCRIPTION: This script provides an interactive 3D visualization of the temperature stratification in a seasonal thermal energy storage (STES) system. The user can control the animation speed, start/stop the animation, and navigate through time steps using buttons and sliders.

"""

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.animation import FuncAnimation

class STESAnimation:
    def __init__(self, storage):
        self.storage = storage
        self.is_animating = False
        self.anim_speed = 100  # Default animation speed (in ms per frame)
        self.step_size = 1  # Default step size
        self.anim = None
        self.current_frame = 0

        # Initialize the figure and axes
        self.fig, self.ax = plt.subplots(subplot_kw={"projection": "3d"})
        plt.subplots_adjust(left=0.1, bottom=0.35)

        # Add UI elements
        self._add_slider()
        self._add_buttons()

        # Initial plot
        self.storage.labels_exist = False
        self.storage.colorbar_exists = False
        self.update_plot(0)

    def _add_slider(self):
        """Add sliders to control the time step and animation speed."""
        # Slider for time step
        self.ax_slider = plt.axes([0.1, 0.1, 0.65, 0.03], facecolor='lightgoldenrodyellow')
        self.slider = Slider(self.ax_slider, 'Time Step', 0, self.storage.hours - 1, valinit=self.current_frame, valstep=1)
        self.slider.on_changed(lambda val: self.update_plot(val))

        # Slider for animation speed
        self.ax_speed = plt.axes([0.75, 0.25, 0.15, 0.04])
        self.speed_slider = Slider(self.ax_speed, 'Speed (ms)', 50, 300, valinit=self.anim_speed)
        self.speed_slider.on_changed(lambda val: self.adjust_speed(val))

        # Slider for step size
        self.ax_step = plt.axes([0.75, 0.1, 0.15, 0.04])
        self.step_slider = Slider(self.ax_step, 'Step Size', 1, 100, valinit=1, valstep=1)
        self.step_slider.on_changed(lambda val: self.set_step_size(val))

    def _add_buttons(self):
        """Add start, stop, forward, backward, and speed control buttons."""
        self.ax_start = plt.axes([0.1, 0.25, 0.1, 0.04])
        self.start_button = Button(self.ax_start, 'Start', color='lightblue', hovercolor='green')
        self.start_button.on_clicked(lambda event: self.start_animation())

        self.ax_stop = plt.axes([0.25, 0.25, 0.1, 0.04])
        self.stop_button = Button(self.ax_stop, 'Stop', color='lightblue', hovercolor='red')
        self.stop_button.on_clicked(lambda event: self.stop_animation())

        self.ax_forward = plt.axes([0.4, 0.25, 0.1, 0.04])
        self.forward_button = Button(self.ax_forward, 'Forward', color='lightblue', hovercolor='yellow')
        self.forward_button.on_clicked(lambda event: self.forward())

        self.ax_backward = plt.axes([0.55, 0.25, 0.1, 0.04])
        self.backward_button = Button(self.ax_backward, 'Backward', color='lightblue', hovercolor='yellow')
        self.backward_button.on_clicked(lambda event: self.backward())

    def set_step_size(self, val):
        """Set the step size for the animation."""
        self.step_size = int(val)

    def update_plot(self, val):
        """Update the 3D plot based on the selected time step."""
        self.current_frame = int(val)
        self.ax.cla()  # Clear the axis
        self.storage.plot_3d_temperature_distribution(self.ax, self.current_frame)
        self.ax.set_title(f'Temperature Stratification (Time Step {self.current_frame})')
        plt.draw()

    def animate(self, i):
        """Animation function to update the plot at each time step."""
        self.current_frame = i
        self.update_plot(i)
        self.slider.set_val(i)  # Update slider position to reflect the current time step
        plt.draw()  # Aktualisiere die GUI

    def start_animation(self):
        """Start the animation."""
        if not self.is_animating:
            self.anim = FuncAnimation(
                self.fig,
                self.animate,
                frames=range(self.current_frame, self.storage.hours, self.step_size),  # Verwende die Schrittweite
                interval=self.anim_speed,
                blit=False,
                repeat=True
            )
            self.is_animating = True
            plt.draw()

    def stop_animation(self):
        """Stop the animation."""
        if self.anim is not None:
            self.anim.event_source.stop()
            self.is_animating = False
            plt.draw()

    def forward(self):
        """Move forward by 1 frame."""
        self.current_frame = min(self.current_frame + 1, self.storage.hours - 1)
        self.slider.set_val(self.current_frame)  # Aktualisiere den Slider
        plt.draw()  # Aktualisiere die GUI

    def backward(self):
        """Move backward by 1 frame."""
        self.current_frame = max(self.current_frame - 1, 0)
        self.slider.set_val(self.current_frame)
        plt.draw()

    def adjust_speed(self, val):
        """Adjust the animation speed."""
        self.anim_speed = int(val)
        if self.is_animating:
            self.stop_animation()
            self.start_animation()

    def show(self):
        """Display the interactive plot."""
        plt.show()